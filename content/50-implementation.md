# Implementation {#sec:implementation}

This chapter describes an implementation of the design presented in chapter [-@sec:design].
It elaborates on the most important aspects of implementing the sharding mechanism in practice.
Afterwards, the implementation is used for evaluating the presented work in chapter [-@sec:evaluation].

## ClusterRing Resource

The central element of the sharding design is the `ClusterRing` custom resource.
A corresponding `CustomResourceDefinition` is installed together with the sharder itself.
It serves as a configuration point for aligning the sharder's actions with the needs of the sharded controller.
The sharded controller doesn't communicate directly with the sharder or vice versa.
Instead, all necessary information is written to API objects, e.g., published in the `ClusterRing` resource when deploying the controller itself.

```text
alpha.sharding.timebertt.dev/clusterring=<clusterring-name>
```

: Ring-specific lease label pattern {#lst:lease-label}

Both the sharder's and the shard's components are required to follow the contracts related to the `ClusterRing` configuration.
Most importantly, this includes patterns for shard leases and the labels on sharded objects themselves.
For announcing themselves to the sharder, controller instances need to label their individual `Lease` objects with the `clusterring` label according to the pattern shown in [@lst:lease-label].
This allows the sharder to select all `Lease` objects belonging to a given `ClusterRing` for partitioning.
Additionally, the sharder can add a label selector to its `Lease` watch cache to filter out any `Lease` objects not related to shards, e.g., leader election locks of other controllers.

```text
shard.alpha.sharding.timebertt.dev/clusterring-<hash>-<clusterring-name>
```

: Ring-specific shard label pattern {#lst:shard-label}

As resources can be part of multiple `ClusterRings`, the sharder uses ring-specific labels for assigning objects to shards and initiating the handover protocol.
The shard label follows the pattern shown in [@lst:shard-label].
The pattern includes the first 8 hex characters of the SHA256 checksum of the `ClusterRing` name.
This is done because the label part after the slash must not exceed the 63 character limit.
If the `ClusterRing` name is too long, the second label part is shortened to 63 characters.
However, by including a name hash, the sharder can still derive a unique label for each `ClusterRing` even if long names with a common prefix are used.

```yaml
apiVersion: sharding.timebertt.dev/v1alpha1
kind: ClusterRing
metadata:
  name: example
  generation: 1
spec:
  resources:
  - group: ""
    resource: configmaps
    controlledResources:
    - group: ""
      resource: secrets
  namespaceSelector:
    matchLabels:
      role: project
status:
  observedGeneration: 1
  shards: 3
  availableShards: 3
  conditions:
  - lastTransitionTime: "2024-01-16T08:09:02Z"
    message: ClusterRing was successfully reconciled
    observedGeneration: 1
    reason: ReconciliationSucceeded
    status: "True"
    type: Ready
```

: Example ClusterRing resource with status {#lst:clusterring-status}

As the resource name suggests, the `ClusterRing` resource is cluster-scoped.
I.e., the object itself doesn't reside in a namespace and configures behavior on a cluster-global level.
This means, that the controller's resources are sharded in multiple namespaces.
However, in addition to listing the sharded API resources, the `ClusterRing` specification also allows configuring a `namespaceSelector` to select namespaces in which the configured API resources should be sharded.
Only if the labels of the object's namespace match the configured `namespaceSelector`, the object is considered for assignments by the sharder.

The ring configuration could also be implemented as a namespace-scoped `Ring` resource that acts only on the namespace that it resides in.
However, by using the `namespaceSelector` feature, a `ClusterRing` can be restricted to a single namespace, effectively implementing namespace-scoped sharding.

Finally, the sharder populates the `ClusterRing` status with information about the number of discovered ring members.
The `status.shards` field describes how many shard leases with a matching `clusterring` label have been discovered.
Additionally, the `status.availableShards` field depicts how many of these shards are healthy and available for assignments.
Also, the `Ready` reflects whether the sharding mechanism configured by the `ClusterRing` has been successfully reconciled.

## Sharder Components

- clusterring controller
  - report status
  - configure webhook
- shard lease controller
  - shard states
  - `alpha.sharding.timebertt.dev/state` label
- partitioning
  - consistent hash ring from leases
  - leases read from cache, ring not cached, difficult to get consistency right when caching
- webhook
  - namespace selector
    - If no `namespaceSelector` is configured in a `ClusterRing` and the global sharder configuration, it defaults to excluding the `kube-system` and `sharding-system` namespaces.
  - ring-specific path
  - object selector
    - only handle unassigned objects, where label change is needed
    - reduce impact on request latency
  - cert-manager
  - failure policy Ignore, low timeout
  - HA setup
- sharder controller
  - (periodic) sharder syncs =~ rebalancing
    - also handles configuration changes (e.g., `namespaceSelector`)
    - reduce load on API server
    - paginated lists, metadata-only, `resourceVersion=0`
    - otherwise, memory consumption would spike proportional to number of objects during syncs

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
  - sharder
  - RBAC for sharder
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
