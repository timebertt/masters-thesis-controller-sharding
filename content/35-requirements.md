# Requirements Analysis

## Goals?

- generalization: independent from controller framework and programming language
  - some parts will still need to be implemented in every controller framework (e.g., shard leases, selecting the objects)
  - core logic should be implemented externally
  - necessary logic on controller-side should be limited and simple to implement
- reduce CPU and memory overhead by sharder
- (reduce API request volume caused by assignments and coordination)

## Non-Goals?

- reduce API request volume of leader election
- leave the "controller ecosystem" / API machinery
  - e.g., introduce external dependencies/infrastructure, e.g., event queue / message broker
  - brings additional operational complexity, decreases comprehensibility, makes it harder to reason about

## Required Actions

Define the actions that the sharding mechanism needs to perform in which cases:

1. new object is created or object is drained (drain and shard label are removed)
   - object is unassigned, assign directly
   - if no shard is available, no assignment is performed (handled by action 2)

2. new shard becomes available
   - determine objects that should be assigned to new shard
   - if object is not assigned yet, assign directly
   - if object is assigned to unavailable shard, assign directly
   - if object is assigned to available shard, drain object

3. existing shard becomes unavailable
   - determine objects that are assigned to shard
   - assign all objects to another shard directly
   - if no shard is available, unassign objects OR no assignment is performed? (handled by action 2)
