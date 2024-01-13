# Implementation

- ClusterRing
  - namespace selector
- webhook configuration
  - ring-specific path
  - object selector
- (periodic) sharder syncs =~ rebalancing
  - paginated lists
  - otherwise, memory consumption would spike proportional to number of objects during syncs
  - also reduces load on API server
