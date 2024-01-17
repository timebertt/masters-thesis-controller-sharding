# Evaluation {#sec:evaluation}

## Experiment Setup

- based on example setup [@sec:impl-setup]
- adds webhosting-operator from study project [@studyproject]
  - adapted to external sharder
  - internal sharder optional
  - both mechanisms supported for comparison
- precisely describe experiment setup: scale/compute resources of control plane
  - observe that the system is not limited:
    - etcd: CPU throttling, disk IOPS, WAL sync, DB sync
    - API server: CPU throttling, max inflight requests
    - webhosting-operator: CPU throttling, max active workers, ...
  - kube-controller-manager API rate limits
- load test
  - ref load dimensions in [@sec:controller-scalability]: number of objects, churn rate
  - different scenarios with different and varying load

## Measurements

- define scalability requirements / SLOs
- Kubernetes SLO 1 and 2 must be satisfied [@sec:kubernetes-scalability]
  - in experiment stricter: needs to include extended resources, needs to include webhook latency
- ref SLIs defined in fundamentals, [@sec:controller-scalability]
  - measure over experiment time instead of cluster-day
  - SLI 1: p99 queue duration < 1s
    - measurement: `TODO` (workqueue metrics)
  - SLI 2: p99 website reconciliation latency < 30s
    - measurement: record time from creation/update to observed watch event of ready status in `experiment`
    - measurement stricter: include controlled objects (e.g., depends on kube-controller-manager: Deployment `Ready` condition)
    - includes sharding assignment latency
- using multiple resources configurations and finding the maximum load capacity each is difficult and costly
  - adding resources difficult for some resources, e.g., network bandwidth
  - restraining resources difficult, e.g., memory -> would crash
- instead, run load tests with varying load, ensure the SLOs are met, and observe the required resource usage
  - higher resource usage means added resources
  - similar to k8s scalability tests
- measure resource consumption using cadvisor
  - CPU, memory, network traffic

## Experiments

### Basic Load

- increase load until a pre-defined limit
- measure resource usage, ensure SLOs are met
- run with singleton, internal sharder, external sharder
- show distribution of work/resource usage proportional to number of objects
- show that overhead of sharder doesn't increase with number of objects any more (req. \ref{req:constant})

### Scale Out

- show that more replicas bring more performance, allow increasing the load while keeping SLOs (req. \ref{req:scale-out})
- this is what proves that controllers are horizontally scalable now!
- limit instances: CPU, memory, concurrent workers
- run basic scenario against external sharder setup with 1, 2, 3 replicas
- measure the maximum load under which SLOs are still satisfied
- show that more replicas bring higher maximum load
- show that overhead of sharding is constant, independent of number of objects (load) (req. \ref{req:constant})

### Rolling Updates

- rolling updates of controller
- evaluate coordination on object movements
- show that SLOs are still met

### Chaos Testing

- randomly kill instances/leader
- similar to [knative chaosduck](https://github.com/knative/pkg/blob/main/leaderelection/chaosduck/main.go#L17)
- show that SLOs are still met

### Autoscaling

- similar to scale out scenario
- horizontal autoscaling of controller according to load
  - HPA on queue duration (SLI 1)
- evaluate coordination on object movements

## Discussion
