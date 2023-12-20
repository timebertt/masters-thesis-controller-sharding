# Requirements Analysis

- take scalability limitations ([@sec:scalability-limitations])
- resolve limitations and make controllers horizontally scalable
- remove restriction to have only a single active instance
  - leader election on global level needs to be replaced
  - need another way to prevent concurrent reconciliations without locking reconciliation on global level
  - distribute work across multiple instances
- use sharding mechanisms to resolve limitations and fulfill requirements of horizontally scalable controllers
- refer to scalability definition ([@sec:kubernetes-scalability]): once work can distributed, adding a new instance yields higher load capacity

## Requirements

Refer to requirements from study project:
[@studyproject]

- req. 1: membership and failure detection
- req. 2: partitioning
- req. 3: coordination and object assignment
- req. 4: preventing concurrency
- req. 5: incremental scale-out

Extended requirements:

- req. 6: generic, reusable implementation
  - controllers can be implemented in any programming language, using any framework
  - hence, sharding implementation should also be independent from controller framework and programming language
  - some parts will still need to be implemented in every controller framework (e.g., shard leases, selecting the objects)
  - core logic should be implemented in reusable way
  - necessary logic in every controller/framework should be limited in scope and simple to implement
- req. 7: constant overhead
  - sharding always comes with overhead for management, coordination, etc.
  - overhead must not increase proportionally to the number of sharded objects
  - otherwise, sharding components would face similar scalability limitations, problem not solved
  - hence, overhead must be constant, i.e., independent from number of objects
  - only then, adding more replicas brings horizontal scalability
- req. 8: don't leave the "controller ecosystem" / API machinery
  - e.g., introduce external dependencies/infrastructure like event queue or message broker
  - brings additional operational complexity, decreases comprehensibility, makes it harder to reason about
  - conflicts with req. 6: external dependencies make it harder to reuse in arbitrary controllers

## Required Actions/Events

\todo[inline]{find a good name for this}

Precisely define the actions that the sharding mechanism needs to perform on which events:

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

\todo[inline]{make event descriptions generic, eliminate implementation-specifics}
