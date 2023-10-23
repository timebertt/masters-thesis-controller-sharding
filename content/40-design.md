# Design

- go over new requirements and suggest solutions

- reduce CPU and memory overhead by sharder
  - make slot-based assignments
- reduce API request volume caused by assignments and coordination
  - how to persist assignments efficiently?
  - is also reduced with above
- generalization: server-side implementation, independent from controller framework, programming language
  - move partitioning, assignment, coordination logic to API server

## Rough Idea

- keep lease-based membership
- assign objects in bulk -> slot-based sharding
  - don't persist assignments on object labels
  - persist slot assignments on leases?
  - preventing concurrency requires controllers to look up slot assignments in object reconciliation
- move assignments to API server
  - transparent label on objects (not persisted in etcd)
  - client sends label back to API server in patch/update request as prerequisite
    - doesn't work on owned objects
  - API server needs to be aware of object relationship and the reconciler's "main object", e.g. owner references
- assignments and coordination must be consistent across API server instances
- watch per slot? -> needs to be implemented in every language/framework
- watch with shard selector
- lease per slot
  - too high request volume for coordination (ref knative)
- shard needs to acknowledge slot movement
  - include some kind of observed generation number of assignments in regular lease updates
