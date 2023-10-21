# Background

- go deeper into core problem
  - big singleton controller loads only one API server, sharded setup better distributes load across API server instances
- define how scalability of controllers can be measured / SLIs
  - sig-scalability tests
  - e.g., p99 queue time
