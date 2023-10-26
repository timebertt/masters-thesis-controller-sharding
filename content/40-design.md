# Design

go over new requirements and suggest solutions

How to address requirements:

- generalization: independent from controller framework and programming language
  - move partitioning, assignment, coordination logic to control plane
  - design how to configure which objects should be sharded
    - best option: not configured at all, determined by watch requests
    - -> transparent assignments
- reduce CPU and memory overhead by sharder
  - a: make slot-based assignments
  - b: move assignments to API server: already has objects in cache
- reduce API request volume caused by assignments and coordination
  - how to persist assignments efficiently? -> make assignments transparent without persistence?
  - is also reduced with slot-based assignments

## Rough Ideas

- keep lease-based membership
  - has to be implemented in all controller frameworks
  - necessary, no way around it

## Step 1: Move Sharder to Control Plane

Goals:

- generalization
- will not reduce CPU/mem overhead, only move it to control plane
- will not reduce API request volume

Ideas:

- simply move sharder to controller manager without changing its core logic
- keep assigning objects via labels
- design how shard leases are recognized
- design how to configure which objects should be sharded
- define label patterns for object selector
- design how object relationships are handled, e.g. owner references to the controller's "main object"

Problems:

- controller-side still has to comply with drain label
  - must only be implemented once in the controller framework
  - might be acceptable

## Approach 1: Transparent Assignments

Goals:

- reduce CPU/mem overhead
- reduce API request volume

Ideas:

- move lease controller to controller manager as in step 1
- teach API server to calculate assignments in watch cache, piggy-back on caches -> reduce resource overhead
- make assignments transparent, don't persist in etcd -> reduce API request volume
  - no resource version bumps, no watch events
  - how are are watch events triggered on assignment changes?
    - investigate how CR of CRDs handle this
    - custom resource watch terminates when CRD spec/schema changes: <https://github.com/kubernetes/kubernetes/blob/746dfad769ad289bc06e411ada1e58cc0262461b/staging/src/k8s.io/apiextensions-apiserver/pkg/apiserver/customresource_handler.go#L504-L505>
    - terminating watches on assignment changes is not enough
      - controller will restart the watch with the last observed resource version
      - without bumps to resource version, there will be no new watch events
      - we still can't be sure if the controller observed the change
- preventing concurrency: how is drain handled?
  - reassignment could send a `DELETE` event just like a label change on watches with label selector
  - API servers need to ensure that the client observed the change
  - client sends assignment label back to API server in patch/update request as prerequisite
    - request is rejected with a conflict error if assignment doesn't match (similar to optimistic locking)
    - doesn't work on owned objects
- assignments and coordination must be consistent across API server instances

## Approach 2: Slot-based Assignments

Goals:

- reduce API request volume
- reduce CPU/mem overhead?

Ideas:

- move all sharder controllers to controller manager
- assign objects in bulk like in redis
- don't persist assignments on object labels
- persist slot assignments on leases?
- preventing concurrency requires controllers to look up slot assignments in object reconciliation
- hard to achieve consistency with this?
- watch per slot? -> significant implementation effort in every language/framework
- lease per slot
  - too high request volume for coordination (ref knative)
- shard needs to acknowledge slot movement
  - include some kind of observed generation number of assignments in regular lease updates
