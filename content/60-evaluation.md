# Evaluation

- define scalability requirements / SLOs
  - ref SLIs defined in background
  - p99 queue time < 1s
    - check k8s scalability goals
  - sharding assignment latency
  - website readiness (fix kube-state-metrics issue) -> caution: depends on kube-controller-manager!
- precisely describe experiment setup: scale/compute resources of control plane
  - observe that the system is not limited:
    - etcd: CPU throttling, disk IOPS, WAL sync, DB sync
    - API server: CPU throttling, max inflight requests
    - webhosting-operator: CPU throttling, max active workers, ...
- randomly kill instances/leader
  - similar to [knative chaosduck](https://github.com/knative/pkg/blob/main/leaderelection/chaosduck/main.go#L17)
- rolling updates of controller
- horizontal (auto-)scaling of controller during load
- show that more replicas bring more performance / proportionally decrease the load
