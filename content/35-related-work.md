# Related Work

## General Mechanisms

- general ideas supported by many controllers/operators
- namespace-based and kind-based sharding
  - why it doesn't scale
  - more watches because of less shared watches, see <https://github.com/kubernetes/kubernetes/issues/14978#issuecomment-217507896>
- ingress controller sharding (by route)
  - <https://docs.openshift.com/container-platform/4.14/networking/ingress-sharding.html>
- Workload level:
  - machine learning applications: <https://medium.com/workday-engineering/implementing-a-fully-automated-sharding-strategy-on-kubernetes-for-multi-tenanted-machine-learning-4371c48122ae>

## Prometheus

- not controller-based sharding, but uses API machinery for service discovery
- `modulus` in service discovery config: <https://prometheus.io/docs/prometheus/latest/configuration/configuration/#relabel_config>
- support for automatic sharding in prometheus-operator: <https://github.com/prometheus-operator/prometheus-operator/blob/main/Documentation/user-guides/shards-and-replicas.md>
- hash the discovered `__address__` label to distribute scrape targets across multiple instances
- no dynamic resharding/rebalancing, only applies to new scrapes
  - scaling down shards does not reshard data onto remaining instances, it must be manually moved
  - scaling up shards does not reshard data, but it will continue to be available from the same instances

## kube-state-metrics

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

## Study Project

- describe shortcomings
- needs increased load tests

Summary:

- implementation on controller-side
- implementation in controller-runtime, can be reused in other controllers based on controller-runtime
- watches are restricted to shard
  - CPU and memory usage are distributed
- sharder controller required
  - extra memory usage
- assignments on a per-object basis needs to many reconciliations and API requests
  - especially on rolling updates
