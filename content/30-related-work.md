# Related Work

This chapter describes work related to scaling Kubernetes controllers horizontally.
It presents approaches in previous scientific work as well as sharding mechanisms implemented in open-source projects.
Advantages and drawbacks of the described mechanisms are analyzed.

## Configuration-Based Sharding

Many projects allow limiting the controllers to a single or multiple namespaces instead of watching API resources in all namespaces.
Examples for this are Flux [@fluxdocs], ExternalDNS [@externaldns], cert-manager [@certmanagerdocs], Ingress-Nginx [@ingressnginxdocs], and prometheus-operator [@prometheusoperatordocs].
Based on these configuration options, sharding can be performed to scale controllers horizontally.
For example, one controller can be deployed for every namespace where a single instance is only responsible for API objects in the corresponding namespace.
This allows distributing work across multiple controller instances to increase the load capacity of the overall system.

In such a setup, concurrent reconciliations are prevented by defining responsibilities for objects based on the namespace criterion.
For this, controllers typically add a field selector to their list and watch requests to only retrieve objects and watch events for the namespace they are responsible for.
If such controllers work with cluster-scoped resources in addition to the controlled resources, they watch all cluster-scoped resources in all namespaced instances.
Controllers for cluster-scoped resources cannot be shared with this approach, as such objects are not located in a namespace.

Another approach for sharding Kubernetes controllers is to deploy multiple instances that each enable a distinct subset of controllers.
For example, cert-manager [@certmanagerdocs] and Gardener [@gardenerdocs] offer such configuration options.
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
Hence, these approaches cannot be used for solving generally making Kubernetes controllers horizontally scalable.

- workload level
  - ingress controller sharding by route: <https://docs.openshift.com/container-platform/4.14/networking/ingress-sharding.html>
  - machine learning applications: <https://medium.com/workday-engineering/implementing-a-fully-automated-sharding-strategy-on-kubernetes-for-multi-tenanted-machine-learning-4371c48122ae>
  - Prometheus, kube-state-metrics?

## Study Project

- describe shortcomings
- needs increased load tests

Summary:

- implementation on controller-side
- implementation in controller-runtime, can be reused in other controllers based on controller-runtime
  - cannot be reused for controllers not based on controller-runtime, or written in other programming languages
- watches are restricted to shard
  - CPU and memory usage are distributed
- sharder controller required
  - extra memory usage
- assignments on a per-object basis needs to many reconciliations and API requests
  - especially on rolling updates

## knative

See references in <https://github.com/timebertt/thesis-controller-sharding/issues/1>, tracking issue <https://github.com/knative/pkg/issues/1181>, documentation <https://knative.dev/docs/serving/config-ha/>.

- controller HA (per-reconciler leader election) [@mooresharding]
  - goal: fast failover for increased availability
  - split reconcilers' keyspaces into buckets
  - leader election per bucket
    - extra API request volume
  - implementation on controller-side
  - reconcilers need to check whether they are responsible for an enqueued object
  - all instances run all informers
  - watches are not restricted to shard
    - memory usage is not distributed, only CPU usage
  - no guarantees about even distribution of buckets

- StatefulSet-based controllers
  - goal: bound worst-case downtime to 1/N, avoid single point of failure
  - no fast fail-overs

Summary:

- purpose is high availability
- not horizontal scaling

## Flux

See <https://fluxcd.io/flux/installation/configuration/sharding/>.

- label-based sharding
- users need to set up multiple instances with distinct label selectors manually
- users need to label objects manually, no automatic assignment to shards

## ArgoCD

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

## KubeVela

See <https://kubevela.io/docs/platform-engineers/system-operation/controller-sharding/>

- also uses labels to assign objects to shards
- also uses webhook (in master) to add labels
- dynamic shard discovery by default?
- only runs shards for the "main" controller, other controllers still run in master
- no resyncs: objects need to be recreated/assigned/reassigned manually
  - when master is down, objects stay unassigned
  - when assigned shard is down, objects are not moved
- static shard names?

## (Prometheus)

- not controller-based sharding, but uses API machinery for service discovery
- `modulus` in service discovery config: <https://prometheus.io/docs/prometheus/latest/configuration/configuration/#relabel_config>
- support for automatic sharding in prometheus-operator: <https://github.com/prometheus-operator/prometheus-operator/blob/main/Documentation/user-guides/shards-and-replicas.md>
- hash the discovered `__address__` label to distribute scrape targets across multiple instances
- no dynamic resharding/rebalancing, only applies to new scrapes
  - scaling down shards does not reshard data onto remaining instances, it must be manually moved
  - scaling up shards does not reshard data, but it will continue to be available from the same instances

## (kube-state-metrics)

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
