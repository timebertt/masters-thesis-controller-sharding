# Implementation {#sec:implementation}

## ClusterRing Resource

- `ClusterRing`
  - label patterns
  - RBAC for sharder

## Sharder Components

- partitioning
  - consistent hash ring from leases
- controllers
  - clusterring
  - shard lease
  - sharder
    - (periodic) sharder syncs =~ rebalancing
      - reduce load on API server
      - paginated lists, metadata-only, `resourceVersion=0`
      - otherwise, memory consumption would spike proportional to number of objects during syncs
- webhook
  - namespace selector
    - exclude kube-system, sharding-system by default
  - ring-specific path
  - object selector
    - only handle unassigned objects, where label change is needed
    - reduce impact on request latency
  - cert-manager
  - failure policy Ignore, low timeout
  - HA setup

## Shard Components

- (reusable) shard components
  - written for controller-runtime
  - shard lease
  - label selector
  - controller wrapper

## Example Setup

- installation
  - CRDs
  - sharding-system
  - sharder, RBAC
  - monitoring
    - sharder metrics
    - sharding-exporter metrics
  - development/evaluation setup
  - kind
- example shard
  - run through demo (getting started)
  - dynamic instance changes

## Limitations

- `generateName` not supported for `main` resources
