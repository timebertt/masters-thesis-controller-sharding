# Design

- go over new requirements and suggest solutions

- eliminate extra CPU and memory usage by sharder
  - make slot-based assignments
- reduce API request volume and the number of reconciliations
  - see above
- generalization: server-side implementation, independent from controller framework, programming language
  - move assignments to API server
