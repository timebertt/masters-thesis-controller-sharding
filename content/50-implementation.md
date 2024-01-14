# Implementation {#sec:implementation}

- controllers
  - shard lease
  - consistent hash ring from leases
- ClusterRing
  - namespace selector
- webhook
  - ring-specific path
  - object selector
    - only handle unassigned objects, where label change is needed
    - reduce impact on request latency
  - failure policy Ignore
  - HA setup
- (periodic) sharder syncs =~ rebalancing
  - paginated lists
  - otherwise, memory consumption would spike proportional to number of objects during syncs
  - also reduces load on API server
- reusable shard components
