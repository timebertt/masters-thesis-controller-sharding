# Related Work

This chapter describes work related to sharding Kubernetes controllers and scaling them horizontally.
It presents approaches in previous scientific work and mechanisms implemented in open-source projects.
It analyzes the advantages and drawbacks of the described mechanisms.

## Configuration-Based Sharding

Many projects allow limiting the controllers to single or multiple namespaces instead of watching API resources in all namespaces.
Examples of this are Flux [@flux], ExternalDNS [@externaldns], cert-manager [@certmanagerdocs], Ingress-Nginx [@ingressnginxdocs], and Prometheus operator [@prometheusoperatordocs].
Based on these configuration options, sharding can be performed to scale controllers horizontally.
For example, one controller can be deployed for every namespace where one instance is only responsible for API objects in the corresponding namespace.
This allows distributing work across multiple controller instances to increase the load capacity of the overall system.

Such a setup prevents concurrent reconciliations by defining responsibilities for objects based on the namespace criterion.
For this, controllers typically add a field selector to their list and watch requests to retrieve only objects and watch events for their namespace.
If such controllers work with cluster-scoped resources in addition to the controlled resources, they watch all cluster-scoped resources in all namespaced instances.
Controllers for cluster-scoped resources cannot be sharded with this approach, as such objects do not belong to any namespace.

Another approach for sharding Kubernetes controllers is to deploy multiple instances that each enable a distinct subset of controllers.
For example, cert-manager [@certmanagerdocs] offers such configuration options.
Such a setup prevents concurrent reconciliations by enabling a given controller only in one instance.
In other words, this performs sharding based on the kind criterion.
Similar to namespace-based sharding, this allows for the distribution of reconciliations across controller instances to enable the system to sustain a higher load.

While these approaches are simple to comprehend and implement, both require manual configuration and separate orchestration of the controller instances.
Also, scaling out controllers cannot be performed dynamically according to the current load.
For example, if the load in existing namespaces increases, no new instances can be added to increase the system's capacity.
With this, the system's scalability is limited by the number of namespaces and controllers.

Additionally, the scalability of both approaches is limited when there is an uneven distribution of objects across namespaces or kinds.
There is an overhead for controllers only responsible for a few objects, but there is also a limit to how many objects can exist in a single namespace.
Furthermore, configuration-based sharding has negative side effects regarding duplicated watches and caches.
For, controllers restricted to a namespace watch cluster-scoped resources relevant to namespace-scoped many times.
Also, with controller-based sharding, individual instances might need to watch other dependent API resources reconciled by another instance.
If there are fewer shared watches compared to a single instance responsible for all API objects, the sharded setup increases the load on the API server but also requires significantly more compute resources.
All of these drawbacks limit the horizontal scalability of such sharded setups.
Hence, these approaches are not suited for generally making Kubernetes controllers horizontally scalable.

## Study Project {#sec:related-study-project}

![Study project sharding architecture [@studyproject]](../assets/study-project-design.pdf)

A previous study project [@studyproject] presents a design and implementation for sharding Kubernetes controllers by leveraging established sharding approaches from distributed databases.
The design introduces a sharder that runs in one of the controller instances as determined by a lease-based leader election mechanism.
It is responsible for sharding-related tasks like failure detection, partitioning, assignments, and coordination.

A lease-based mechanism inspired by Bigtable [@bigtable] is employed to realize membership and failure detection.
Each controller instance maintains a shard lease with its individual instance ID, serving as a heartbeat resource for announcing membership to the sharder.
The sharder watches these leases for reacting to state changes and performs shard termination and object reassignment upon lease expiration or voluntary termination.

For partitioning, a variant of consistent hashing inspired by Apache Cassandra [@cassandradocs] and Amazon Dynamo [@dynamo] is used to determine shard ownership based on the API object's metadata.
This minimizes object movement during instance additions or removals and provides a simple, deterministic algorithm for shard assignment.

In addition to watching shard leases, the sharder also watches the metadata of sharded API objects to react to object creations and assignment changes.
Objects are assigned to specific controller instances by the sharder, and this assignment is persisted in a `shard` label on the objects themselves.
The sharder's role is critical during initial assignments but is not in the critical path for ongoing reconciliations.
All shards use filtered watches with label selectors specific to their instance ID to watch and reconcile only API objects assigned to the respective instances.

Concurrent reconciliations of a single object in multiple controller instances during object movements are prevented by following a dedicated handover protocol.
If the current shard is still available, it must acknowledge the movement and confirm that it stops reconciling the object.
For this, the sharder first adds a `drain` label to the object and waits until the current shard has removed both the `drain` and `shard` labels.
Only then does the sharder set the `shard` label to the instance ID of the new, desired shard.
If the current shard is unavailable, objects are assigned immediately to the new shard without first setting the `drain` label.

This design is a step towards horizontally scalable Kubernetes controllers.
It achieves a good distribution of reconciliation work across available controller instances.
Also, the design enables dynamic scaling of the controller replicas during runtime by facilitating automatic rebalancing.
The CPU and memory usage related to processing watch events and caching objects is distributed well using shard-specific label selectors for watch requests.

The design is implemented generically in the controller-runtime library [@controllerruntime].
With this, it is reusable for other controllers written in Go and based on controller-runtime.
Controllers not written in Go or not using controller-runtime can leverage the exact sharding mechanisms but cannot reuse the presented implementation.
Another design drawback is the extra CPU and memory usage of the sharder's watches and caches for sharded API objects.
The design requires watching all sharded API objects in one of the controller instances and thus causes CPU and memory usage proportional to the number of sharded objects.
With this, the scalability limitation of controllers is not resolved but only shifted to the active sharder instance (see [@fig:study-project-memory]).
The assignments per object also require many sharder reconciliations and API requests, especially during rolling updates, increasing the control plane's load.

![Study project memory usage by pod [@studyproject]](../assets/study-project-memory.pdf){#fig:study-project-memory}

## knative

In knative [@knative], controllers also use leader election but not for global locking[^knative-issue].
Instead, the controllers perform leader election per reconciler[^reconciler] and bucket.
When running multiple instances of the controllers, each instance might acquire a subset of all leases and run only the corresponding reconcilers.
Some of knative's reconcilers are leader-aware and run in all instances but behave differently according to the leadership status.
For example, the webhook components also use reconcilers for building up indices.
The reconcilers also run in non-leader instances but only perform writing actions in the leader instance.
Additionally, the keys of all objects are split into a configurable number of buckets.
Each reconciler leases a subset of buckets, i.e., a shard of objects.
Before reconciling an object, the reconciler checks if its instance is responsible for the object.
Only if it is responsible can it continue with the usual reconciliation.
[@mooresharding]

![Failover with leader election per controller and bucket [@mooresharding]](../assets/reconciler-buckets.pdf)

To realize these mechanisms, all controller instances run all informers.
I.e., they watch all objects regardless of whether they need to reconcile them.
With this, the controllers' watches are not restricted to the relevant subset of objects.
While the CPU usage related to reconciliations is distributed across controller instances, the memory usage related to the watch cache is not distributed but instead duplicated.
Furthermore, the mechanisms do not guarantee an even distribution of objects across instances.
Users need to configure a higher number of buckets to achieve an even distribution.
This, in turn, increases the additional API request volume for `Lease` objects even further.

The described sharding mechanisms in knative achieve fast failovers as informers are warmed in all controller instances.
However, the system's scalability is still limited as the watch caches' resource impact is duplicated and not distributed.
Applying the described concepts to other controllers is complex and requires notable changes to the controller implementation.
To summarize, the system benefits from these mechanisms in terms of availability but not in terms of scalability.

[^reconciler]: Here, the term reconciler describes a single controller type for a specific object kind.
[^knative-issue]: The implementation efforts were tracked in <https://github.com/knative/pkg/issues/1181>.

## Flux

The Flux controllers offer a command line option `--watch-label-selector` that filters the controllers' watch caches using a label selector.
This can be used to scale out Flux controllers horizontally using a sharding strategy.
For this, users deploy multiple instances of the same controller with unique label selectors used as the sharding key[^flux-sharding].
Then, users assign objects to shards by adding the shard key label to the respective manifests ([@lst:flux-sharding]).
As a fallback for unassigned objects, a set of controller instances is deployed that selects all objects that do not have the shard key label.
[@flux]

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: source-controller-shard1
spec:
  template:
    spec:
      containers:
      - name: source-controller
        args:
        # ...
        - --watch-label-selector=sharding.fluxcd.io/key=shard1
# ...
---
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: podinfo
  namespace: default
  labels:
    sharding.fluxcd.io/key: shard1
spec:
  url: https://github.com/stefanprodan/podinfo
# ...
```

: Example Flux manifests using label-based sharding {#lst:flux-sharding}

With this strategy, reconciliation work and the cache's resource footprint are distributed across multiple controller instances, enabling the Flux controllers' horizontal scalability.
However, the strategy involves many manual steps: Users must set up individual controller instances with distinct label selectors and manually assign objects to shards.
Accordingly, the system does not detect failures in individual instances or perform automatic failovers or rebalancing.
The sharding strategy is limited to a static number of instances and does not allow for dynamic instance changes, e.g., due to instance failures or automatic scaling.

[^flux-sharding]: <https://fluxcd.io/flux/installation/configuration/sharding/>

## Argo CD

In Argo CD [@argocddocs], the application controller is the central component that deploys manifests pulled from Git repositories to Kubernetes.
It works with one or more clusters configured via `Secrets` that contain credentials for the cluster.
The application reconciliation process can become memory-intensive depending on the number and size of the deployed manifests.

To support using Argo CD to deploy thousands of applications to many clusters simultaneously, users can configure the application controller to run multiple instances and distribute work across them.
For this, individual clusters can either be assigned to a shard manually in the cluster `Secret` or automatically assigned by the application controller based on a selected partitioning algorithm.
Depending on whether the application controller is deployed as a `StatefulSet` (static sharding) or `Deployment` (dynamic sharding[^argodynamic]), the assignments from controller instances to shards are stored in a central `ConfigMap`.
If the user chooses the dynamic sharding mechanism, the `ConfigMap` also stores heartbeat data for all shards.
Based on this and the status of instance readiness probes, all controller instances can determine the health of a given instance and decide whether a shard needs to be reassigned to a different instance.
The application controller can facilitate dynamic scaling and automatic rebalancing with this mechanism.
[@argoaws; @argocnoe; @argoinfracloud]

While the described mechanisms help scale Argo CD horizontally for use cases with many clusters, they cannot be used to scale the application controller for use cases with many applications on only a few clusters.
Also, if the sharding approach based on a `StatefulSet` is used, all instances need to be rolled to configure a new number of instances.
Furthermore, depending on the chosen partitioning algorithm, removing a cluster from the system can cause a reshuffling of all other assignments and, with this, a significant performance impact.
Additionally, the sharding mechanism does not distribute the load of the watch cache but only the reconciliation work.
In the case of the application controller, the watch cache's memory footprint is negligible compared to the memory footprint of processing all deployed manifests.
However, this is specific to Argo CD's application controller, and the mechanism is unsuitable for reuse in arbitrary Kubernetes controllers.

[^argodynamic]: <https://github.com/argoproj/argo-cd/blob/master/docs/proposals/rebalancing-clusters-across-shards-dynamically.md>

## KubeVela

KubeVela also allows running multiple instances of its core controller responsible for deploying applications to support large-scale use cases.
For this, users deploy multiple instances of the vela-core – one in master mode (primary) and the others in slave mode (shards).
The primary instance runs all controllers and webhooks and schedules applications to one of the available shard instances.
On the other hand, the shard instances are labeled with a unique `shard-id` label and only run the application controller.
[@kubevela]

When a user or any other client creates a new application, the primary instance intercepts the request using a mutating webhook.
It then discovers available shards by selecting ready pods in its namespace with the `shard-id` label.
The mutating webhook assigns the application object to the designated instance by adding the `scheduled-shard-id` label.
All shard instances use a watch label selector with the `scheduled-shard-id` label to select the subset of applications scheduled to the respective instance.
With this, the reconciliation work and watch cache's resource consumption are distributed across the shard instances.
[@kubevela]

![Sharding architecture in KubeVela [@kubevela]](../assets/kubevela-sharding.jpg)

While the application webhook dynamically discovers the set of available shard instances, there are no automatic reassignments when a new instance is added, or an existing one is removed.
Most importantly, when a shard instance fails, the assigned applications are not reassigned and no longer reconciled.
Additionally, applications stay unassigned if no shard is available at the time of creation.
Manual interaction is required to restore the system's functionality in both cases.
Furthermore, the creation of application objects is blocked if the primary instance serving the mutating webhook is unavailable.
Lastly, if a new shard is added to the system, there is no automatic rebalancing.
I.e., the user must manually reassign existing objects to restore a balanced assignment distribution.
