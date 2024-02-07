# Conclusion and Future Work {#sec:conclusion}

Conclusion:

- go over requirements: all requirements fulfilled
- restriction of having a single active controller (leader election) is removed
- design makes Kubernetes controllers horizontally scalable
- req. \ref{req:membership} Membership and Failure Detection
  - suitable for dynamic environments
  - automatic failover for failed and removed shards (better than Flux, ArgoCD, KubeVela)
- req. \ref{req:partitioning} Partitioning
  - balanced distribution for all ring sizes
  - controlled objects assigned to same shard as owner
- req. \ref{req:coordination} Coordination and Object Assignment
  - automatic, no user action needed (better than Flux, ArgoCD)
  - uses label selector to filter caches (better than ArgoCD)
- req. \ref{req:concurrency} Preventing Concurrency
  - still guaranteed although no leader is elected
- req. \ref{req:scale-out} Incremental Scale-Out
  - shown in [@sec:eval-scale-out]
- req. \ref{req:reusable} Reusable Implementation
  - few steps required for reuse
  - steps shown in [@sec:impl-shard]
  - better than all other implementations listed in related work
- req. \ref{req:constant} Constant Overhead
  - shown in [@sec:eval-comparison]
  - better than study project
- req. \ref{req:ecosystem} Only Use API and Controller Machinery
  - simple to reason about
  - no external components with additional complexity
  - clients don't need to know about sharding, can keep using APIs as before
- simple to apply mechanism to existing controllers, fosters adoptions
- doesn't depend on Kubernetes version, simplifies development in open source community

Future Work:

- further evaluation in productive controllers
- sharding can be used for canary deployments, similar to KubeVela's grayscale controller release [@kubevela]
