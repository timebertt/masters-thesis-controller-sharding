# Evaluation

- define scalability requirements / SLOs
  - ref SLIs defined in background
  - e.g., p99 queue time < 1s
- precisely describe experiment setup: scale/compute resources of control plane
  - observe that the system is not limited:
    - etcd: CPU throttling, disk IOPS, WAL sync, DB sync
    - API server: CPU throttling, max inflight requests
    - webhosting-operator: CPU throttling, max active workers, ...
