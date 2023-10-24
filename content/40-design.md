# Design

- go over new requirements and suggest solutions

- reduce CPU and memory overhead by sharder
  - a: make slot-based assignments
  - b: move sharder controllers to API server: already has object in cache
- reduce API request volume caused by assignments and coordination
  - especially on rolling updates
  - how to persist assignments efficiently? -> make assignments transparent without persistence?
  - is also reduced with slot-based assignments
- generalization: server-side implementation, independent from controller framework, programming language
  - move partitioning, assignment, coordination logic to control plane

## Rough Ideas

- keep lease-based membership
- assign objects in bulk? -> slot-based sharding
  - don't persist assignments on object labels
  - persist slot assignments on leases?
  - preventing concurrency requires controllers to look up slot assignments in object reconciliation
  - too hard to achieve consistency with this
- move assignments to API server
  - transparent label on objects (not persisted in etcd)?
  - -> no resource version bumps, no watch events
  - how are are watch events triggered on assignment changes?
    - investigate how CR of CRDs handle this
    - custom resource watch terminates when CRD spec changes: <https://github.com/kubernetes/kubernetes/blob/746dfad769ad289bc06e411ada1e58cc0262461b/staging/src/k8s.io/apiextensions-apiserver/pkg/apiserver/customresource_handler.go#L504-L505>
    - terminating watches on assignment changes is not enough
      - controller will restart the watch with the last observed resource version
      - without bumps to resource version, there will be no new watch events
      - we still can't be sure if the controller observed the change
  - client sends label back to API server in patch/update request as prerequisite (similar to optimistic locking)?
    - doesn't work on owned objects
  - API server needs to be aware of object relationship and the reconciler's "main object", e.g. owner references
- assignments and coordination must be consistent across API server instances
- watch per slot? -> needs to be implemented in every language/framework
- watch with shard selector
- lease per slot
  - too high request volume for coordination (ref knative)
- shard needs to acknowledge slot movement
  - include some kind of observed generation number of assignments in regular lease updates

## Approach 1: Move Sharder to API Server

- simply move sharder to API server without changing its logic
- keep assigning objects via labels
- define label patterns for object selector
- design how API server recognizes shard leases
- design how to configure which objects should be sharded
- sharder is deployed multiple times without leader election
  - should be fine as long as controller uses optimistic locking
  - leader election was only a trick to pin sharder resource usage to a single controller instance
