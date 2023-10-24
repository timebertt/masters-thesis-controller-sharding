# Previous Work

## Community Work

- namespace-based and kind-based sharding
  - why it doesn't scale
  - more watches because of less shared watches
  - See <https://github.com/kubernetes/kubernetes/issues/14978#issuecomment-217507896>

### knative

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
  - goal: bound worst-case downtime to 1/N, avoid SPOF
  - no fast failovers

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

## Study Project

- describe shortcomings
- needs increased load tests

- implementation on controller-side
- implementation in controller-runtime, can be reused in other controllers based on controller-runtime
- watches are restricted to shard
  - CPU and memory usage are distributed
- sharder component required
  - extra memory usage
- assignments on a per-object basis needs to many reconciliations and API requests

## Requirement Analysis

- eliminate extra CPU and memory usage by sharder
- reduce API request volume and the number of reconciliations
- generalization: server-side implementation, independent from controller framework, programming language
