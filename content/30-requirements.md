# Requirements Analysis

- go from approach in study project
- define requirements for enhancing the approach/implementation

## Requirements

- generalization: independent from controller framework and programming language
  - some parts will still need to be implemented in every controller framework (e.g., shard leases, selecting the objects)
  - core logic should be implemented externally
  - necessary logic on controller-side should be limited and simple to implement
- reduce memory overhead by sharder
  - eliminate cache for sharded objects
  - eliminate caches that grow with the number of sharded objects
- reduce API request volume caused by assignments and coordination
  - during creation: two requests are used for creation and initial assignment
  - during drain: three requests are used for starting drain, acknowledging drain, and reassignment

## Non-Goals

\todo[inline]{invert to positive goals}

- reduce API request volume of leader election
- leave the "controller ecosystem" / API machinery
  - e.g., introduce external dependencies/infrastructure, e.g., event queue / message broker
  - brings additional operational complexity, decreases comprehensibility, makes it harder to reason about

## Required Actions

Precisely define the actions that the sharding mechanism needs to perform in which cases:

1. new object is created or object is drained (drain and shard label are not present)
   - object is unassigned, assign directly
   - if no shard is available, no assignment is performed (handled later on by action 2)

2. new shard becomes available
   - determine objects that should be assigned to new shard
   - if object is not assigned yet, assign directly
   - if object is assigned to unavailable shard, assign directly
   - if object is assigned to available shard, drain object

3. existing shard becomes unavailable
   - determine objects that are assigned to shard
   - assign all objects to another shard directly
   - if no shard is available, unassign objects OR no assignment is performed? (handled by action 2)
