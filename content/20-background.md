# Background

## API Machinery

- Kubernetes is a declarative system
- users declare the desired state
- system state is stored in etcd
- API server serves state via REST HTTP endpoints
- adds API machinery: API discovery, API extensions, admission webhooks, Authentication/Authorization, watch requests

## Controller Machinery

- controllers drive the actual state to match the desired state (reconciliations)
- can reconcile any API resources: built-in and extended
- watch objects to get notified about changes
- controller building blocks?
- important aspects
  - queue deduplicates keys, prevents concurrent reconciliations in multiple worker routines
  - watch controlled & owned objects
  - need to enqueue all objects on startup (might have missed relevant events)
- can be implemented in any programming language (<https://kubernetes.io/docs/concepts/extend-kubernetes/operator/#writing-operator>)
- only list actively maintained projects
- frameworks/libraries implementing these mechanisms:
  - client-go (Go): <https://github.com/kubernetes/client-go>
  - controller-runtime (Go): <https://github.com/kubernetes-sigs/controller-runtime>
  - Java Operator SDK: <https://javaoperatorsdk.io/>
  - kube-rs (Rust): <https://kube.rs/>
  - KubeOps (.NET): <https://buehler.github.io/dotnet-operator-sdk/>
- other frameworks implementing conceptually different mechanisms:
  - Metacontroller: <https://metacontroller.github.io/metacontroller>
    - core controller implemented in Go
    - calls webhooks for business logic (can be implemented in any language)
  - shell-operator: <https://flant.github.io/shell-operator/>
    - core controller implemented in Go
    - calls scripts for business logic
  - kopf (Python): <https://kopf.readthedocs.io/>
    - designed around modelling domain knowledge
    - event-driven: primarily handles watch events
    - stores handled state in annotation
    - stores controller state in status/annotation
    - leader election via `{Cluster,}KopfPeering` custom resources

## Scalability of Controllers

- what already makes Kubernetes controllers scalable
  - watch requests
  - no polling, change notifications
  - controllers store all necessary state locally
  - don't contact API server for every reconciliation
  - can immediately react on changes
  - system is event-triggered, level-driven
- define how scalability of controllers can be measured / SLIs
  - sig-scalability definition for Kubernetes scalability: <https://github.com/kubernetes/community/blob/master/sig-scalability/slos/slos.md#how-we-define-scalability>
  - sig-scalability tests
  - see <https://github.com/kubernetes/community/blob/master/contributors/devel/README.md#sig-scalability>
  - e.g., p99 queue time

## Leader Election

- why it is needed
  - prevent concurrent reconciliations of a single object
  - reconciliations are not coordinated between multiple instances
  - can lead to conflicting actions
- how it is realized
  - fulfills requirement to prevent concurrent reconciliations of a single object in multiple controllers
  - but on the global level
  - wraps entire process, only executes controller when lock is acquired, terminates when lost
- multiple instances
  - only a single active leader at a time
  - active-passive HA setup
  - fast fail-overs
  - NOT horizontal scaling

## Scalability Limitations

- core mechanisms of controllers cause the heavy resource usage
  - watch events: CPU for decoding, network transfer
  - watch cache: memory
- no horizontal scalability, no distribution of work, no active-active setups
- due to global leader election, concurrent reconciliations are prevented on a global level
- rate of reconciliations, amount of objects, etc. limited to machine size and network bandwidth
- other perspective: fulfilling SLOs requires scaling controllers vertically when rate of reconciliations, amount of objects, etc. increase
- cannot increase throughput/capacity by adding more instances
- more ideas
  - makes precise vertical right-sizing more difficult, as resource consumption depends on leadership
  - big singleton controller loads only one API server, sharded setup better distributes load across API server instances -> not true for all cases: depends on control plane setup, HTTP2 usage
  - see background in <https://kubevela.io/docs/platform-engineers/system-operation/controller-sharding/>

## Sharding

- essential components?
  - ref <https://github.com/kubernetes/kubernetes/issues/1064#issuecomment-57700433>
  - ref Slicer [@slicer16]
  - ref study project, chapter 2.7 [@studyproject]
- why sharding enables horizontal scalability
