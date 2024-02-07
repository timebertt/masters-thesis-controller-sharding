# Related Work

This chapter describes work related to sharding Kubernetes controllers and scaling them horizontally.
It presents approaches in previous scientific work as well as mechanisms implemented in open-source projects.
Advantages and drawbacks of the described mechanisms are analyzed.

## Configuration-Based Sharding

Many projects allow limiting the controllers to a single or multiple namespaces instead of watching API resources in all namespaces.
Examples for this are Flux [@flux], ExternalDNS [@externaldns], cert-manager [@certmanagerdocs], Ingress-Nginx [@ingressnginxdocs], and prometheus-operator [@prometheusoperatordocs].
Based on these configuration options, sharding can be performed to scale controllers horizontally.
For example, one controller can be deployed for every namespace where a single instance is only responsible for API objects in the corresponding namespace.
This allows distributing work across multiple controller instances to increase the load capacity of the overall system.

In such a setup, concurrent reconciliations are prevented by defining responsibilities for objects based on the namespace criterion.
For this, controllers typically add a field selector to their list and watch requests to only retrieve objects and watch events for the namespace they are responsible for.
If such controllers work with cluster-scoped resources in addition to the controlled resources, they watch all cluster-scoped resources in all namespaced instances.
Controllers for cluster-scoped resources cannot be sharded with this approach, as such objects are not located in any namespace.

Another approach for sharding Kubernetes controllers is to deploy multiple instances that each enable a distinct subset of controllers.
For example, cert-manager [@certmanagerdocs] offers such configuration options.
In such a setup, concurrent reconciliations can be prevented by enabling a given controller only in a single instance.
In other words, this performs sharding based on the kind criterion.
Similar to namespace-based sharding, this allows distributing reconciliations across controller instances for enabling the system to sustain a higher load.

While these approaches are simple to comprehend and implement, both require manual configuration and separate orchestration of the set of controller instances.
Also, scaling out controllers cannot be performed dynamically according to the current load.
For example, if the load in existing namespaces increases, no new instances can be added for increasing the system's capacity.
With this, the scalability of the system is limited by the number of namespaces and controllers.

Additionally, the scalability of both approaches is limited in scenarios with an uneven distribution of objects across namespaces or kinds.
E.g., there is an overhead for controllers that are only responsible for a few objects but there is also a limit for how many objects can be created in a single namespace.
Furthermore, configuration-based sharding has negative side-effects regarding duplicated watches and caches.
E.g., with namespace-based sharding, cluster-scoped resources relevant for namespace-scoped resources are watched many times.
Also, with controller-based sharding, individual instances might need to watch other dependent API resources that are reconciled by another instance.
If there are less shared watches compared to a single instance responsible for all API objects, the sharded setup increases the load on the API server, but also requires significantly more compute resources.
All of these drawbacks limit the horizontal scalability of such sharded setups.
Hence, these approaches are not suited for generally making Kubernetes controllers horizontally scalable.

## Study Project {#sec:related-study-project}

![Study project sharding architecture [@studyproject]](../assets/study-project-design.pdf)

A previous study project [@studyproject] presents a design and implementation for sharding Kubernetes controllers by leveraging established sharding approaches from distributed databases.
The design introduces a sharder that runs in one of the controller instances as determined by a lease-based leader election mechanism.
It is responsible for sharding-related tasks like failure detection, partitioning, assignments, and coordination.

To realize membership and failure detection, a lease-based mechanism inspired by Bigtable [@bigtable] is employed.
Each controller instance maintains a shard lease with its individual instance ID, serving as a heartbeat resource for announcing membership to the sharder.
The sharder watches these leases for reacting to state changes, and performs shard termination and object reassignment upon lease expiration or voluntary termination.

For partitioning, a variant of consistent hashing inspired by Apache Cassandra [@cassandradocs] and Amazon Dynamo [@dynamo] is used to determine shard ownership based on the API object's metadata.
This minimizes object movement during instance additions or removals and provides a simple, deterministic algorithm for shard assignment.

In addition to watching shard leases, the sharder also watches the metadata of sharded API objects to react to object creations and assignment changes.
Objects are assigned to specific controller instances by the sharder, and this assignment is persisted in a `shard` label on the objects themselves.
The sharder's role is critical during initial assignments but is not in the critical path for ongoing reconciliations.
All shards use filtered watches with label selectors specific to their instance ID to only watch and reconcile API objects that are assigned to the shard.

Concurrent reconciliations of a single object in multiple controller instances during object movements are prevented by following a dedicated handover protocol.
If the current shard is still available, it needs to acknowledge the movement and confirm that it stops reconciling the object.
For this, the sharder first adds a `drain` label to the object and waits until the current shard has removed both the `drain` and `shard` label.
Only then, the sharder sets the `shard` label to the instance ID of the new, desired shard.
If the current shard is not available, objects are immediately assigned to the new shard without setting the `drain` label first.

This design is a step towards horizontally scalable Kubernetes controllers.
It achieves a good distribution of reconciliation work across available controller instances.
Also, the design enables dynamic scaling of the controller replicas during runtime by facilitating automatic rebalancing.
By using shard-specific label selectors for watch requests, the CPU and memory usage related to processing watch events and caching objects is distributed well.

The design is implemented generically in the controller-runtime library [@controllerruntime].
With this, it can be reused in other controllers that are written in Go and based on controller-runtime.
Controllers that are not written in Go or that don't use controller-runtime can leverage the same sharding mechanisms, but the presented implementation cannot be reused in such controllers.
Another drawback of the design is the extra CPU and memory usage of the sharder's watches and caches for sharded API objects.
The design requires watching all sharded API objects in one of the controller instance and thus causes CPU and memory usage that is proportional to the number of sharded objects.
With this, the scalability limitation of controllers is not resolved but only shifted to the active sharder instance (see [@fig:study-project-memory]).
Additionally, the assignments per object require many sharder reconciliations and API requests, especially during rolling updates.
This increases the load on the control plane.

![Study project memory usage by pod [@studyproject]](../assets/study-project-memory.pdf){#fig:study-project-memory}

## knative

In knative [@knative], controllers also use leader election but not on a global level[^knative-issue].
Instead, the controllers perform leader election per reconciler[^reconciler] and per bucket.
When running multiple instances of the controllers, each instance might acquire a subset of all leases and run only the corresponding reconcilers.
Some of the reconcilers are leader-aware and run in all instances but behave differently according to the leadership status.
E.g., the webhook components use reconcilers also for building up indices.
The reconcilers run in non-leader instances as well, but only perform writing actions in the leader instance.
Additionally, the keys of all objects are split into a configurable number of buckets.
Each reconciler leases a subset of buckets, i.e., a shard of objects.
Before reconciling an object, the reconciler checks if its instance is responsible for the object.
Only if it is responsible, it continues with the usual reconciliation.
[@mooresharding]

![Failover with leader election per controller and bucket [@mooresharding]](../assets/reconciler-buckets.pdf)

For realizing these mechanisms, all controller instances run all informers.
I.e., they watch all objects independent of whether they need to reconcile them or not.
With this, the controllers' watches are not restricted to the relevant subset of objects.
While the CPU usage related to reconciliations is distributed across controller instances, the memory usage related to the watch cache is not distributed but rather duplicated.
Furthermore, the mechanisms doesn't guarantee an even distribution of objects across instances.
To counteract an uneven distribution, a higher number of buckets needs to be configured.
This in turn increases the additional API request volume for `Lease` objects even further.

The described sharding mechanisms in knative achieve fast fail-overs as informers are warmed in all instances.
However, the scalability of the system is still limited as the watch caches resource impact is duplicated and not distributed.
Applying the described concepts to other controllers is complex and requires notable changes to the controller implementation.
To summarize, the system benefits from these mechanism in terms of availability, but not in terms of scalability.

[^reconciler]: Here, the term reconciler describes a single controller type for a specific object kind.
[^knative-issue]: The implementation efforts were tracked in <https://github.com/knative/pkg/issues/1181>.

## Flux

<!--
See <https://fluxcd.io/flux/installation/configuration/sharding/>.

- label-based sharding
- users need to set up multiple instances with distinct label selectors manually
- users need to label objects manually, no automatic assignment to shards
-->

## ArgoCD

<!--
See:

- benchmarks:
  - <https://aws.amazon.com/blogs/opensource/argo-cd-application-controller-scalability-testing-on-amazon-eks/>
  - <https://cnoe.io/blog/argo-cd-application-scalability>
- docs:
  - <https://argo-cd.readthedocs.io/en/stable/operator-manual/high_availability/#argocd-application-controller>
  - <https://www.infracloud.io/blogs/sharding-clusters-across-argo-cd-application-controller-replicas/>
  - <https://argocd-operator.readthedocs.io/en/latest/reference/argocd/#controller-options>
- initial implementation: <https://github.com/argoproj/argo-cd/issues/4284>
- dynamic rebalancing: <https://github.com/argoproj/argo-cd/pull/15036>
  - <https://github.com/argoproj/argo-cd/blob/master/docs/proposals/rebalancing-clusters-across-shards-dynamically.md>

Summary:

- application controller is sharded by cluster (shard key = cluster)
- all applications on one cluster are assigned to the same shard
- shard can be assigned manually in cluster secret
- algorithm:
  - legacy: `hash(cluster secret UID) % replicas`
  - now: round-robin
- supports dynamic scaling based on clusters per shard
-->

## KubeVela

<!--
See <https://kubevela.io/docs/platform-engineers/system-operation/controller-sharding/>

- also uses labels to assign objects to shards
- also uses webhook (in master) to add labels
- dynamic shard discovery by default?
- only runs shards for the "main" controller, other controllers still run in master
- no resyncs: objects need to be recreated/assigned/reassigned manually
  - when master is down, objects stay unassigned
  - when assigned shard is down, objects are not moved
- static shard names?
-->

<!--
## Sharding on Workload Level?

- ingress controller sharding by route: <https://docs.openshift.com/container-platform/4.14/networking/ingress-sharding.html>
- machine learning applications: <https://medium.com/workday-engineering/implementing-a-fully-automated-sharding-strategy-on-kubernetes-for-multi-tenanted-machine-learning-4371c48122ae>

### Prometheus

- not controller-based sharding, but uses API machinery for service discovery
- `modulus` in service discovery config: <https://prometheus.io/docs/prometheus/latest/configuration/configuration/#relabel_config>
- support for automatic sharding in prometheus-operator: <https://github.com/prometheus-operator/prometheus-operator/blob/main/Documentation/user-guides/shards-and-replicas.md>
- hash the discovered `__address__` label to distribute scrape targets across multiple instances
- no dynamic resharding/rebalancing, only applies to new scrapes
  - scaling down shards does not reshard data onto remaining instances, it must be manually moved
  - scaling up shards does not reshard data, but it will continue to be available from the same instances

### kube-state-metrics

See <https://github.com/kubernetes/kube-state-metrics#horizontal-sharding>.

- horizontal sharding with multiple `Deployments`
  - only serve a subset of object metrics
  - all instances watch, marshal, and cache all objects!
  - sharding benefit is only on the serving/scraping side -> quickly return to Prometheus
  - each instance must have a shard index (`--shard`) and the total number of shards configured (`--total-shards`) -> no membership, failure detection, etc.
  - partitioning using md5 of UID and modulo `--total-shards`
  - coordination, object assignment not needed: Prometheus deduplicates time series (or rather the queries `without(instance)`)
- automated horizontal sharding via `StatefulSet`
  - automatically discover shard index and total number of shards
  - rollout includes a downtime for each shard
- sharding by node for pod metrics using `DaemonSet`
  - watch with field selector for `spec.nodeName`
  - distributes watch and cache across instances
  - rollout includes a downtime for each shard
-->
