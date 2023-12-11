# Design

## Overview

How to address new requirements:

- generalization: independent from controller framework and programming language
  - move partitioning, assignment, coordination logic to external sharder
  - design how to configure which objects should be sharded
- reduce memory overhead by sharder
  - consider required actions again
  - find different triggers for action 1 than using watch events
- reduce API request volume caused by assignments and coordination
  - how to persist assignments efficiently? -> make assignments transparent without persistence?
  - is also reduced with slot-based assignments
- keep lease-based membership
  - has to be implemented in all controller frameworks
  - necessary, no way around it

## Step 1: External Sharder

Goals:

- generalization
- will not reduce CPU/mem overhead, only move it to an external component
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
  - must only be implemented once in the controller framework, is acceptable

## Step 2: Assignments in Admission

Goals:

- reduce CPU/mem overhead
- reduce API request volume

Ideas:

- move sharder controllers to controller manager or dedicated components
- shard labels are added to objects during admission: either in admission plugin or webhook
- when ring state changes, controller triggers reassignment or drain on all relevant objects
- admission handles action 1 (new object or object drained)
  - handles object-related events, that can be detected solely by mutating API requests to objects
  - currently, watch events (~cache) for the sharded objects are used for this
  - with assignments in admission, watches and caches can be dropped
  - webhook adds significant latency to mutating API requests
    - only needs to act on unassigned objects -> add object selector
- controller handles action 2 and 3 (ring state changes)
  - handles ring-related events, that can be detected solely by watch events for leases
  - sharder controller doesn't need to watch objects, only needs watch for leases
  - action 2 (new shard)
    - list all objects and determine desired shard
    - add drain label to all objects that are not assigned to desired shard
  - action 3 (dead shard)
    - list all objects assigned to dead shard
    - reassign all objects immediately
  - controller might interfere with itself (might act on a single object concurrently) -> use optimistic locking for all object mutations
- controller and admission view on ring state could be slightly out of date
  - objects might end up on "wrong" shards
    - action 1: new shard just got ready, not observed by admission, new object incorrectly assigned to another shard
    - action 2: sharder drains object, controller removes drain/shard label, admission assigns to the same shard again
  - might be acceptable
    - objects are only assigned to available shards
    - single responsible shard is guaranteed
    - doesn't violate original requirements
  - if eventual consistency should still be guaranteed:
    - periodically resyncs all leases
    - determine objects that should not be assigned to that lease and reassign
  - moving into a single component (running controller and serving webhook) doesn't solve the problem: will need to run multiple instances which watch individually again
- webhooks need to be created for all objects that should be sharded

Summary:

- trades resource overhead (object cache) for a few API requests (lists) and latency (webhook)
- latency can be reduced with object selector and/or by moving to admission plugin
- reduces API request volume a bit because drain and new assignment are now combined into a single API request

<!--
## Approach 1: Transparent Assignments

Goals:

- reduce CPU/mem overhead
- reduce API request volume

Ideas:

- move lease controller to controller manager as in step 1
- teach API server to calculate assignments in watch cache, piggy-back on caches -> reduce resource overhead
- make assignments transparent, don't persist in etcd -> reduce API request volume
  - no resource version bumps, no watch events!?
  - how are are watch events triggered on assignment changes?
    - investigate how CR of CRDs handle this
    - custom resource watch terminates when CRD spec/schema changes
    - terminating the watch connection would cause a re-list
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
-->

<!--
## Approach 3: Slot-based Assignments

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
-->
