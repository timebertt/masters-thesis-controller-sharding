# Background

- go deeper into core problem
  - big singleton controller loads only one API server, sharded setup better distributes load across API server instances
  - leader election
    - fulfills requirement to prevent concurrent reconciliations of a single object in multiple controllers
    - wraps entire process, only executes controller when lock is acquired, terminates when lost
- define how scalability of controllers can be measured / SLIs
  - sig-scalability tests
  - e.g., p99 queue time
- non-goals
  - reduce API request volume of leader election
