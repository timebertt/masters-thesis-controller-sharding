# Design

This chapter presents a design to address the requirements presented in chapter [-@sec:requirements].
It is based on the design presented in the previous study project ([@sec:related-study-project]) [@studyproject] because it already fulfills parts of the requirements (req. 1–5).
This thesis evolves the design to address the extended set of requirements (req. 6–8).

## Sharding Events

To enhance the existing design, it is important to analyze which sharding-related events must be handled by the sharding mechanism.
Based on this, the following sections develop changes to the design with regards to how the individual events are detected.

The following is a complete list of sharding events that must be considered by the design and what actions need to be taken for each individual event.

\subsubsection*{\event\label{evt:new-shard}A new shard becomes available}

When a shard becomes available for assignments, none of the existing objects are assigned to it.
To achieve a good distribution of reconciliation work, a rebalancing needs to be performed.

For this, the sharder needs to determine which objects should be assigned to the new shard according to the partitioning algorithm.
It needs to consider all objects and perform one of the following actions accordingly:

- If the object is not assigned yet, assign it directly to the desired available shard.
- If the object is assigned to an unavailable shard, assign it directly to the desired available shard.
- If the object is assigned to an available shard but should be moved to another shard, start the handover protocol by draining the object.

\subsubsection*{\event\label{evt:shard-down}An existing shard becomes unavailable}

If an existing shard becomes unavailable, all objects that are assigned to it must be moved to another available shard.
Here, the sharder needs to consider all objects that currently have the `shard` label set to the unavailable shard.
For every object, the desired available shard is determined using the partitioning algorithm and the `shard` label is added accordingly.
If the object was in the process of being drained – i.e., it still carries the `drain` label – the sharder must remove the `drain` label together with adding the `shard` label.
If there is no remaining available shard, the sharder doesn't need to take any action.
In this case, objects effectively stay unassigned until a new shard becomes available (evt. \ref{evt:new-shard}).

\subsubsection*{\event\label{evt:new-object}A new object is created, or an object is drained}

When a new API object is created by the user or a controller, it is unassigned and neither carries the `shard` nor the `drain` label.
This is also the case when an existing object is should be moved to another shard and drained successfully by the currently responsible shard.

In these cases, the sharder should directly assign the object to one of the available shards.
If there is no available shard, the assignment is deferred until a new shard becomes available (evt. \ref{evt:new-shard}).

## Architecture

![Sharding architecture](../draw/architecture.pdf)

The presented design keeps the sharding mechanisms inspired by distributed databases for membership, failure detection, and partitioning as seen in the study project.
I.e., individual controller instances announce themselves to the sharder by maintaining a shard lease that also serves the purpose of detecting shard failures.
Also, consistent hashing is kept for deterministically identifying the responsible instance for API objects based on the discovered membership information, while facilitating minimal movements during instance additions and removals.

Furthermore, label-based assignments and coordination as well as shard-specific label selectors are kept for a good distribution of CPU and memory load related to the controller's watch caches.
Lastly, concurrent reconciliations are prevented by following the same protocol for handovers between active instance involving the `drain` label.

In contrast to the previous design, the sharder is not part of the controller deployment itself but runs externally as a dedicated deployment.
It is configured by `ClusterRing` objects that identify rings of controller instances responsible for a set of sharded API objects.
Most notably, the sharder consists of two active components: the sharder webhook and the sharder controller.
Both components realize object assignments in response to different sharding events ([@sec:sharding-events]).

In the evolved design, the extended requirements are addressed by two different architectural changes.
Firstly, moving partitioning, assignment, and coordination logic to an external sharder deployment configurable via custom resources makes the sharding mechanism independent of the used controller framework and programming language.
With this, the sharding implementation becomes reusable for any arbitrary Kubernetes controller, fulfilling req. \ref{req:reusable} ([@sec:design-external]).

Limiting the overhead of the sharding mechanism to be independent of the number of sharded API objects (req. \ref{req:constant}) is realized by performing assignments during object admission when required by event \ref{evt:new-object}.
A mutating webhook is triggered whenever a new unassigned object is created or an existing object is successfully drained by the currently responsible shard ([@sec:design-admission]).
With this, watching the sharded objects is obsolete and allows removing the watch cache that causes a resource usage proportional to the number of objects.
Additionally, this change reduces the API request volume caused by assignments and coordination.

## External Sharder {#sec:design-external}

Goals:

- address req. \ref{req:reusable}: generalization
- will not reduce CPU/mem overhead, only move it to an external component
- will not reduce API request volume

Ideas:

- simply move sharder to controller manager without changing its core logic
- keep assigning objects via labels
- design how shard leases are recognized
- design how to configure which objects should be sharded
- define label patterns for object selector
- design how object relationships are handled, e.g. owner references to the controller's "main object"

Problems:

- controller-side still has to comply with drain label
  - must only be implemented once in the controller framework, is acceptable

## Assignments in Admission {#sec:design-admission}

Goals:

- address req. \ref{req:constant}: constant overhead
- reduce CPU/mem overhead
- reduce API request volume

Ideas:

- shard labels are added to objects during admission: either in admission plugin or webhook
- when ring state changes, controller triggers reassignment or drain on all relevant objects
- admission handles event 1 (new object or object drained)
  - handles object-related events, that can be detected solely by mutating API requests to objects
  - currently, watch events (~cache) for the sharded objects are used for this
  - with assignments in admission, watches and caches can be dropped
  - webhook adds significant latency to mutating API requests
    - only needs to act on unassigned objects -> add object selector
- controller handles event 2 and 3 (ring state changes)
  - handles ring-related events, that can be detected solely by watch events for leases
  - sharder controller doesn't need to watch objects, only needs watch for leases
  - event 2 (new shard)
    - list all objects and determine desired shard
    - add drain label to all objects that are not assigned to desired shard
  - event 3 (dead shard)
    - list all objects assigned to dead shard
    - reassign all objects immediately
  - controller might interfere with itself (might act on a single object concurrently) -> use optimistic locking for all object mutations
- controller and admission view on ring state could be slightly out of date
  - objects might end up on "wrong" shards
    - event 1: new shard just got ready, not observed by admission, new object incorrectly assigned to another shard
    - event 2: sharder drains object, controller removes drain/shard label, admission assigns to the same shard again
  - might be acceptable
    - objects are only assigned to available shards
    - single responsible shard is guaranteed
    - doesn't violate original requirements
  - if eventual consistency should still be guaranteed:
    - periodically resyncs all leases
    - determine objects that should not be assigned to that lease and reassign
  - moving into a single component (running controller and serving webhook) doesn't solve the problem: will need to run multiple instances which watch individually again
- webhooks need to be created for all objects that should be sharded

Summary:

- trades resource overhead (object cache) for a few API requests (lists) and latency (webhook)
- latency can be reduced with object selector and/or by moving to admission plugin
- reduces API request volume a bit because drain and new assignment are now combined into a single API request
