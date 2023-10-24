# Background

- go deeper into core problem
  - big singleton controller loads only one API server, sharded setup better distributes load across API server instances
  - leader election
    - fulfills requirement to prevent concurrent reconciliations of a single object in multiple controllers
    - wraps entire process, only executes controller when lock is acquired, terminates when lost
- define how scalability of controllers can be measured / SLIs
  - sig-scalability definition for Kubernetes scalability: <https://github.com/kubernetes/community/blob/master/sig-scalability/slos/slos.md#how-we-define-scalability>
  - sig-scalability tests
  - e.g., p99 queue time
- non-goals
  - reduce API request volume of leader election

## Distributed Databases

### Partitioning

### Storage Assignments
