# Design

This chapter presents a design to address the requirements in chapter [-@sec:requirements].
It builds upon the design presented in the previous study project ([@sec:related-study-project]) [@studyproject] because it already fulfills parts of the requirements.
This thesis evolves the design to address the extended list of requirements.

## Sharding Events {#sec:sharding-events}

To enhance the existing design, it is critical to understand which sharding-related events must be handled by the sharder.
Based on this, the following sections develop changes to the design regarding how the individual events are detected.

The following is a complete list of sharding events that must be considered by the sharder and what actions it needs to perform for each event.

\subsubsection*{\evt{new-shard}A new shard becomes available}

When a new shard becomes available for assignments, no existing objects are assigned to the instance.
Accordingly, the sharder needs to rebalance assignments of existing objects to achieve a good distribution of reconciliation work.

For this, the sharder needs to determine which objects should be assigned to the new shard according to the partitioning algorithm.
It needs to consider all objects and perform one of the following actions accordingly:

- If the object still needs to be assigned, assign it directly to the desired available shard.
- If the object is assigned to an unavailable shard, assign it directly to the desired available shard.
- If the object is assigned to an available shard but should be moved to another shard, start the handover protocol by draining the object.

\subsubsection*{\evt{shard-down}An existing shard becomes unavailable}

If an existing shard becomes unavailable, the sharder must move all objects assigned to it to another available shard.
Here, the sharder must consider all objects with the `shard` label set to the unavailable shard.
It must determine the desired available shard using the partitioning algorithm for every object and add the `shard` label accordingly.
If the object is in the process of being drained – i.e., it still carries the `drain` label – the sharder must remove the `drain` label together with adding the `shard` label.
If there is no remaining available shard, the sharder does not need to take any action.
In this case, objects effectively stay unassigned until a new shard becomes available (\refevt{new-shard}).

\subsubsection*{\evt{new-object}A new object is created, or an object is drained}

When a client creates a new API object, it is unassigned, and neither carries the `shard` nor the `drain` label.
This is also the case when an existing object should be moved to another shard and drained successfully by the currently responsible shard.

In these cases, the sharder must directly assign the object to one of the available shards.
If there is no available shard, the assignment is deferred until a new shard becomes available (\refevt{new-shard}).

## Architecture

![Evolved controller sharding architecture](../draw/architecture.pdf)

The evolved design keeps the sharding mechanisms inspired by distributed databases for membership, failure detection, and partitioning, as presented in the study project.
I.e., individual controller instances announce themselves to the sharder by maintaining a shard lease that also serves the purpose of detecting shard failures.
Also, the design keeps consistent hashing as a deterministic partitioning algorithm based on the discovered membership information, facilitating minimal movements during instance additions and removals.

Furthermore, the design keeps label-based assignments, coordination, and shard-specific label selectors for a good CPU and memory load distribution related to the controller's watch caches.
Lastly, concurrent reconciliations are prevented by following the same protocol for handovers between active instances involving the `drain` label.

In contrast to the previous design, the sharder is not part of the controller deployment itself but runs externally as a dedicated deployment.
It is configured by `ClusterRing` objects that identify rings of controller instances responsible for a set of sharded API objects.
Most notably, the sharder consists of two active components: the sharder webhook and the sharder controller.
Both components realize object assignments in response to different sharding events ([@sec:sharding-events]).

The evolved design addresses the extended requirements by two different architectural changes.
First, moving partitioning, assignment, and coordination logic to an external sharder deployment configurable via custom resources makes the sharding mechanism independent of the used controller framework and programming language.
With this, the sharding implementation becomes reusable for any arbitrary Kubernetes controller, fulfilling \refreq{reusable} ([@sec:design-external]).

Second, the design limits the overhead of the sharding mechanism to be independent of the controller's load (\refreq{constant}) by performing assignments during object admission when required by event \refevt{new-object}.
A mutating webhook is triggered whenever a client creates a new unassigned object or the currently responsible shard removes the `drain` label from an existing object ([@sec:design-admission]).
With this, watching the sharded objects is obsolete and allows removing the watch cache that causes a resource usage proportional to the number of objects.
Additionally, this change reduces the API request volume caused by assignments and coordination.

## External Sharder {#sec:design-external}

The first architectural change generalizes the sharding design and makes the implementation reusable to address \refreq{reusable}.
Note that this change does not reduce the resource overhead or API request volume to address \refreq{constant}, but only move it to an external deployment.

Instead of running the sharder as another controller in the sharded controller deployment itself, it is extracted to a dedicated external deployment without changing its core logic.
This allows for reusing the sharder for multiple sharded controller deployments in the same cluster.
However, as the sharder is not part of the same binary as the sharded controller, it must also be configured explicitly.
For this, the design introduces a new custom resource modeling a ring of controller instances: the `ClusterRing`.

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

: Example ClusterRing {#lst:clusterring}

The sharded controller deployment only runs the actual controllers themselves, i.e., the actual shards.
Nevertheless, the controller deployment is configured with the corresponding `ClusterRing` to use matching names.
The individual instances announce their ring membership by adding a `clusterring` label with the ring's name as the label value to their shard leases.

Like the internal sharder design, object assignments persist in the `shard` label on sharded objects.
The enhanced external sharder design uses ring-specific `shard` and `drain` labels including the name of the corresponding `ClusterRing`.
Individual controllers use a ring-specific label selector for filtering their watch caches accordingly.
This allows sharded objects to be part of multiple rings.
For example, a resource owned by a sharded controller might, in turn, be reconciled by another sharded controller.
Both controllers would use a dedicated `ClusterRing` in this scenario that includes the given resource.

Apart from the name, the `ClusterRing` object contains a list of resources that should be sharded, i.e., reconciled by a sharded ring of controllers.
Listed resources can either be the main resource of a controller or controlled resources ([@sec:apimachinery]).
The sharder determines the partitioning key for objects of the controller's main resource based on their metadata.
In contrast to this, the partitioning key of controlled objects is determined based on the metadata contained in the objects' controller reference.
With this, main and controlled resources are assigned to the same shard as many controllers require ([@sec:controller-machinery]).
However, multiple main resources listed in `ClusterRing` specifications are not guaranteed to be assigned to the same shard.

This architectural change extracts the core logic of the sharding mechanism to an external, generic sharder.
It allows generically reusing the implementation and applying the sharding mechanism to any controller.
While the core logic is implemented externally, the implementation of controllers still needs to be adapted to comply with the sharding mechanism.
However, the required changes are limited in scope and simple to implement:

- controllers must announce themselves to the sharder via individual shard leases
- controllers must use ring-specific label selectors to filter their watch caches
- controllers must follow the handover protocol and acknowledge drain operations initiated by the sharder

These changes need to be implemented in the programming language of the controller itself and work with the leveraged controller framework.
However, implementing these changes generically in the respective controller frameworks would allow controller developers to adopt the sharding mechanisms quickly.

\newpage

## Assignments in Admission {#sec:design-admission}

The second architectural change ensures that the overhead of the sharding mechanism stays the same independent of the controller's load.
It ensures a constant overhead for true horizontal scalability of sharded controller setups, addressing \refreq{scale-out} and \refreq*{constant}.
This change builds upon the previous one to limit the sharder's resource usage and to reduce the API request volume caused by assignments and coordination.

The evolved design achieves these goals by performing assignments in the API admission phase, which replaces the sharder's costly watch cache for sharded objects.
Considering the sharding-related events that need to be handled by the sharding mechanism ([@sec:sharding-events]), the watch cache for sharded objects is only needed to detect and handle \refevt{new-object}, i.e., when new unassigned objects are created, or existing objects are drained.
This event always involves a mutating API request for the sharded object itself.
Hence, the admission control logic can be leveraged to perform actions in response to the request instead of triggering sharder reconciliations in response to a watch event.

In the presented design, a mutating admission webhook served by the sharder is used, which can be configured in all clusters without changing control plane components.
Alternatively, an in-tree admission plugin in the Kubernetes API server could achieve the same, requiring changing the API server.
Hence, the admission webhook is more flexible but adds latency to API requests.
The sharder is responsible for setting up the `MutatingWebhookConfigurations` as needed.
For this, the `ClusterRing` controller creates one webhook configuration for each ring with a matching list of sharded API resources.

The sharder still watches shard leases for detecting ring state changes (\refevt{new-shard}, \refevt*{shard-down}).
It runs a controller that accordingly handles both events as described in [@sec:sharding-events].
For this, the sharder does not need to watch the sharded objects themselves.
Instead, it can use lightweight metadata-only list requests whenever object assignments of a `ClusterRing` need to be reconciled.
With this, both ring-related sharding events can be detected and handled by a sharder controller solely watching shard leases.

The webhook server shares the watch cache for shard leases with the sharder controller for constructing the consistent hash ring.
When it receives a webhook request, the handler decodes the contained object from the original API request and determines the desired shard based on its metadata.
It then responds with corresponding patch operations to mutate the `shard` label as desired.

In a distributed system like this, failures in inter-component communication can occur at any time and must be handled accordingly.
The design must cater to situations where the webhook server does not perform object assignments as needed due to network failures or similar issues.
Hence, the sharder controller is triggered periodically to perform reconciliations (resyncs) of all object assignments if the webhook did not correctly assign some objects.
This fallback mechanism is never needed during regular operation but is essential for guaranteeing eventual consistency in the distributed system.

To summarize, this design enhancement trades the resource overhead caused by watching sharded objects for periodic resyncs with non-cached list requests and increased request latency.
However, as chapter [-@sec:implementation] shows, the negative impact on API request latency can be reduced by using object selectors to be practically irrelevant.
If the API latency added by webhook requests still becomes problematic, using an in-tree admission plugin in the API server reduces the request latency.

Most importantly, this architectural change eliminates all elements in the sharding design that grow in resource usage with the controller's load.
This is crucial in achieving horizontal scalability for Kubernetes controllers.
Also, it significantly reduces the API request volume added by the sharding assignments and coordination and, with this, the load on the control plane and etcd in particular.
More concretely, object creation and initial assignment are combined into a single mutating API request.
In other words, the sharding mechanism does not incur additional API requests when creating objects.
The design also reduces additional API requests needed by the handover protocol by one-third compared to the existing design.
Instead of performing three object changes for initiating the drain operation, acknowledging it, and performing a new assignment, the new sharding design involves only two mutations by combining the latter two requests.
