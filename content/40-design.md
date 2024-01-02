# Design

- design based on study project
- evolve design to address extended requirements

## Sharding Events

Analyze design of study project: which events are handled by the sharding mechanism.
Which actions need to performed for them:

- evt. 1: new object is created or object is drained (drain and shard label are not present)
  - object is unassigned, assign directly
  - if no shard is available, no assignment is performed (handled later on by action 2)

- evt. 2: new shard becomes available
  - determine objects that should be assigned to new shard
  - if object is not assigned yet, assign directly
  - if object is assigned to unavailable shard, assign directly
  - if object is assigned to available shard, drain object

- evt. 3: existing shard becomes unavailable
  - determine objects that are assigned to shard
  - assign all objects to another shard directly
  - if no shard is available, unassign objects OR no assignment is performed? (handled by action 2)

## Overview

How to address extended requirements:

- generalization (req. 6): independent from controller framework and programming language
  - addressed in step 1 ([@sec:design-external])
  - move partitioning, assignment, coordination logic to external sharder
  - design how to configure which objects should be sharded
- constant overhead (req. 7): required design/implementation enhancements:
  - addressed in step 2 ([@sec:design-admission])
  - reduce memory overhead by sharder
    - eliminate cache for sharded objects (grows with the number of sharded objects)
    - consider required actions again
    - object cache was only needed to detect evt. 1
    - find different mechanism to trigger assignments
  - reduce API request volume caused by assignments and coordination
    - during creation: two requests are used for creation and initial assignment
    - during drain: three requests are used for starting drain, acknowledging drain, and reassignment
  - non-goal: reduce API request volume of membership and failure detection
    - keep lease-based membership

## External Sharder {#sec:design-external}

Goals:

- address req. 6: generalization
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

## Assignments in Admission {#sec:design-admission}

Goals:

- address req. 7: constant overhead
- reduce CPU/mem overhead
- reduce API request volume

Ideas:

- shard labels are added to objects during admission: either in admission plugin or webhook
- when ring state changes, controller triggers reassignment or drain on all relevant objects
- admission handles event 1 (new object or object drained)
  - handles object-related events, that can be detected solely by mutating API requests to objects
  - currently, watch events (~cache) for the sharded objects are used for this
  - with assignments in admission, watches and caches can be dropped
  - webhook adds significant latency to mutating API requests
    - only needs to act on unassigned objects -> add object selector
- controller handles event 2 and 3 (ring state changes)
  - handles ring-related events, that can be detected solely by watch events for leases
  - sharder controller doesn't need to watch objects, only needs watch for leases
  - event 2 (new shard)
    - list all objects and determine desired shard
    - add drain label to all objects that are not assigned to desired shard
  - event 3 (dead shard)
    - list all objects assigned to dead shard
    - reassign all objects immediately
  - controller might interfere with itself (might act on a single object concurrently) -> use optimistic locking for all object mutations
- controller and admission view on ring state could be slightly out of date
  - objects might end up on "wrong" shards
    - event 1: new shard just got ready, not observed by admission, new object incorrectly assigned to another shard
    - event 2: sharder drains object, controller removes drain/shard label, admission assigns to the same shard again
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
