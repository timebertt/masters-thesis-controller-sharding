# Previous Work

## Community Work

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
