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

## Overview

![Sharding architecture](../draw/architecture.pdf)

How to address extended requirements:

- generalization (req. \ref{req:reusable}): independent from controller framework and programming language
  - addressed in step 1 ([@sec:design-external])
  - move partitioning, assignment, coordination logic to external sharder
  - design how to configure which objects should be sharded
- constant overhead (req. \ref{req:constant}): required design/implementation enhancements:
  - addressed in step 2 ([@sec:design-admission])
  - reduce memory overhead by sharder
    - eliminate cache for sharded objects (grows with the number of sharded objects)
    - consider required actions again
    - object cache was only needed to detect evt. 1
    - find different mechanism to trigger assignments
  - reduce API request volume caused by assignments and coordination
    - during creation: two requests are used for creation and initial assignment
    - during drain: three requests are used for starting drain, acknowledging drain, and reassignment
  - non-goal: reduce API request volume of membership and failure detection
    - keep lease-based membership

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
