# Design

This chapter presents a design to address the requirements presented in chapter [-@sec:requirements].
It is based on the design presented in the previous study project ([@sec:related-study-project]) [@studyproject] because it already fulfills parts of the requirements (req. 1–5).
This thesis evolves the design to address the extended set of requirements (req. 6–8).

## Sharding Events {#sec:sharding-events}

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

The first architectural change generalizes the sharding design and makes the implementation reusable to address req. \ref{req:reusable}.
Note that this change does not reduce the resource overhead or API request volume to address req. \ref{req:constant}, but only move it to an external deployment.

Instead of running the sharder as another controller in the sharded controller deployment itself, it is extracted to a dedicated external deployment without changing its core logic.
This allows reusing the sharder for multiple sharded controller deployments in the same cluster.
However, as the sharder is not part of the same binary as the sharded controller, it needs to be configured explicitly too.
For this, a new custom resource modeling a ring of controller instances is introduced: the `ClusterRing`.

```yaml
apiVersion: sharding.timebertt.dev/v1alpha1
kind: ClusterRing
metadata:
  name: myoperator
spec:
  resources:
  - group: myoperator.timebertt.dev
    resource: application
    controlledResources:
    - group: apps
      resource: deployments
    - group: ""
      resource: configmaps
```

: Example ClusterRing resource {#lst:clusterring}

The sharded controller deployment only runs the actual controllers themselves, i.e., the actual shards.
Nevertheless, the controller deployment is configured together with the corresponding `ClusterRing` to use matching names.
The individual instances announce their ring membership by adding a `clusterring` label with the name of the ring as the label value to their shard leases.

Similar to the internal sharder design, object assignments are persisted in the `shard` label on sharded objects.
In the enhanced external sharder design, ring-specific `shard` and `drain` labels are used that include the name of the corresponding `ClusterRing`.
Individual controllers use a ring-specific label selector for filtering their watch caches accordingly.
This allows sharded objects to be part of multiple rings.
For example, a resource owned by a sharded controller might in turn be reconciled by another sharded controller.
In this scenario, both controllers would use a dedicated `ClusterRing` that both include the given resource.

Apart from the name, the `ClusterRing` object contains a list of resources that should be sharded, i.e., reconciled by a sharded ring of controllers.
Listed resources can either be the main resource of a controller or controlled resources ([@sec:apimachinery]).
For the controller's main resource, the object's own metadata is used for determining the partitioning key.
In contrast to this, the partitioning key of controlled objects is determined based on the metadata contained in the objects' controller reference.
With this, main and controlled resources are assigned to the same shard as required by many controllers ([@sec:controller-machinery]).
However, multiple main resources listed in `ClusterRing` specifications are not guaranteed to be assigned to the same shard.

This architectural change extracts the core logic of the sharding mechanism to an external, generic sharder.
It allows to reuse the implementation and apply the sharding mechanism generically to any controller.
While the core logic is implemented externally, the implementation of controllers still needs to be adapted to comply with the sharding mechanism.
However, the required changes are limited in scope and simple to implement:

- controllers must announce themselves to the sharder via individual shard leases
- controllers must use ring-specific label selectors to filter their watch caches
- controllers must follow the handover protocol and acknowledge drain operations initiated by the sharder

These changes need to be implemented in the programming language of the controller itself and work with the leveraged controller framework.
However, implementing these changes generically in the respective controller frameworks would allow controller developers to adopt the sharding mechanisms easily.

\newpage

## Assignments in Admission {#sec:design-admission}

The second architectural change ensures that overhead of the sharding mechanism doesn't grow with the number of sharded objects.
It ensures a constant overhead for true horizontal scalability of sharded controller setups, addressing req. \ref{req:scale-out} and \ref{req:constant}.
This change builds upon the previous one to limit the sharder's resource usage and to reduce the API request volume caused by assignments and coordination.

These goals are achieved by performing assignments in the API admission phase, which replaces the sharder's costly watch cache for sharded objects.
Considering the sharding-related events that need to be handled by the sharding mechanism ([@sec:sharding-events]), the watch cache for sharded objects is only needed to detect and handle evt. \ref{evt:new-object}, i.e., when new unassigned objects are created or existing objects are drained successfully.
This event always involves a mutating API request for the sharded object itself.
Hence, admission control logic can be leveraged for performing actions in response to the request instead of triggering sharder reconciliations in response to a watch event.

In the presented design, a mutating admission webhook served by the sharder is used which can be configured in all clusters without changing control plane components.
Alternatively, an in-tree admission plugin in the Kubernetes API server could also be used to achieve the same thing, but it requires changing the API server itself.
Hence, the admission webhook is more flexible but adds latency to API requests though.
The sharder is responsible for setting up the `MutatingWebhookConfigurations` as needed.
For this, the `ClusterRing` controller creates one webhook configuration for each ring with a matching list of sharded API resources.

The sharder still watches shard leases for detecting ring state changes (evt. \ref{evt:new-shard} and \ref{evt:shard-down}).
It runs a controller that handles both events as described in [@sec:sharding-events] accordingly.
For this, the sharder doesn't need to watch the sharded objects themselves.
Instead it can use lightweight metadata-only list requests whenever object assignments of a `ClusterRing` need to be reconciled.
With this, both ring-related sharding events can be detected and handled by a sharder controller solely watching shard leases.

The webhook server shares the watch cache for shard leases with the sharder controller for constructing the consistent hash ring.
When it receives a webhook request, the handler decodes the contained object from the original API request and determines the desired shard based on its metadata.
It then responds with corresponding patch operations to mutate the `shard` label as desired.

In a distributed system like this, failures in inter-component communication can occur any time and need to be handled accordingly.
Concretely, the design must cater for situations in which the webhook server doesn't perform object assignments as needed due to network failures or similar issues.
Hence, the sharder controller is triggered periodically to perform reconciliations (resyncs) of all object assignments for the case that some objects were not correctly assigned by the webhook.
This is a fallback mechanism that is never needed during normal operation, but is essential for guaranteeing eventual consistency in the distributed system.

To summarize, this design enhancement trades the resource overhead caused by watching sharded objects for periodic resyncs with non-cached list requests and an increase in request latency.
However, as chapter [-@sec:implementation] shows, the negative impact on API request latency can be reduced by the use of object selectors to be practically irrelevant.
If the API latency added by webhook requests becomes problematic nevertheless, an in-tree admission plugin in the API server can be considered as a solution.

Most importantly, this architectural change eliminates all elements in the sharding design that grow in resource usage with the number of sharded objects.
This is crucial in achieving horizontal scalability for Kubernetes controllers.
Also, it significantly reduces the API request volume added by the sharding assignments and coordination and with this the load on the control plane and etcd in particular.
More concretely, object creation and initial assignment are combined into a single mutating API request.
In other words, the sharding mechanism doesn't incur any additional mutating API requests during object creations.
The additional API requests needed by the handover protocol are also reduced by one third in comparison to the existing design.
Instead of performing three object changes for initiating the drain operation, acknowledging it, and performing a new assignment, the new sharding design involves only two mutations by combining the later two requests into one.

<!--
- controller and admission view on ring state could be slightly out of date
  - objects might end up on "wrong" shards
    - event \ref{evt:new-shard}: new shard just got ready, not observed by admission, new object incorrectly assigned to another shard
    - event \ref{evt:shard-down}: sharder drains object, controller removes drain/shard label, admission assigns to the same shard again -> cannot happen, right?
  - might be acceptable
    - objects are only assigned to available shards
    - single responsible shard is guaranteed
    - doesn't violate original requirements
  - moving into a single component (running controller and serving webhook) doesn't solve the problem: will need to run multiple instances which watch individually again
-->
