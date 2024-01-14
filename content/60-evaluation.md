# Evaluation

## Measurements

- define scalability requirements / SLOs
  - ref SLIs defined in fundamentals, [@sec:controller-scalability]
    - Kubernetes SLO 1 and 2 must be satisfied
    - in experiment stricter: needs to include extended resources, needs to include webhook latency
    - measure over experiment time instead of cluster-day
  - p99 queue time < 1s
  - sharding assignment latency
  - website readiness (fix kube-state-metrics issue) -> caution: depends on kube-controller-manager!

## Experiment Setup

- webhosting-operator
  - adapted to external sharder
  - internal sharder optional
  - both mechanisms supported for comparison
- precisely describe experiment setup: scale/compute resources of control plane
  - observe that the system is not limited:
    - etcd: CPU throttling, disk IOPS, WAL sync, DB sync
    - API server: CPU throttling, max inflight requests
    - webhosting-operator: CPU throttling, max active workers, ...
- load test
  - describe basic scenario

## Results

- basic scenario
- show that more replicas bring more performance, allow increasing the thresholds while keeping SLOs (req. \ref{req:scale-out})
  - this is what proves that controllers are horizontally scalable now!
  - load in individual instances is proportionally decreased
- show that overhead of sharding is constant, independent of number of objects (req. \ref{req:constant})

## Advanced Scenarios

- randomly kill instances/leader
  - similar to [knative chaosduck](https://github.com/knative/pkg/blob/main/leaderelection/chaosduck/main.go#L17)
- rolling updates of controller
  - evaluate coordination on object movements
- horizontal (auto-)scaling of controller during load
  - evaluate coordination on object movements
