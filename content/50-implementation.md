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

The sharder runs several components including controllers and webhooks that facilitate the core logic of the sharding mechanism.

The `ClusterRing` controller is responsible for configuring the sharder webhooks.
For every `ClusterRing` object it creates one `MutatingWebhookConfiguration` ([@lst:sharder-webhook]).
The configuration contains a single webhook, that is called for unassigned objects of all resources listed in the `ClusterRing` specification.
In addition to watching `ClusterRing` objects for spec changes, the controller also watches shard `Leases` for availability changes.
It reports the total number and the number of available shards as well as the `Ready` condition in the `ClusterRing` status ([@lst:clusterring-status]).

The shard lease controller is responsible for detecting instance failures based on the `Lease` objects that every shard maintains.
Like in the study project implementation, it watches all shard `Leases` and determines the state of each individual shard following the conditions in [@tbl:shard-states].
When a shard becomes uncertain, it tries to acquire the lease to ensure connectivity with the API server.
Only if the controller is able to acquire the `Lease`, the shard is considered unavailable and removed from partitioning.
I.e., all shards in states ready, expired, and uncertain are considered available and included in partitioning.
Orphaned `Leases` are garbage collected by the shard lease controller.
For increased observability, the shard lease controllers writes the determined state to the `alpha.sharding.timebertt.dev/state` label on the respective `Lease` objects.
[@studyproject]

|Shard State|Conditions|
|---:|-------------------|
|ready|held by shard (`metadata.name == spec.holderIdentity`), not expired|
|expired|held by shard, expired up to `spec.leaseDurationSeconds` ago|
|uncertain|held by shard, expired more than `spec.leaseDurationSeconds` ago|
|dead|not held by shard (released or acquired by sharder)|
|orphaned|not held by shard, expired at least 1 minute ago|

: Shard states [@studyproject] {#tbl:shard-states}

To ensure responsiveness, the controller watches the `Lease` objects for relevant changes.
However, it also needs to requeue visited `Leases` after a certain duration when their state would change if no update event occurs.
E.g., the transition from ready to expired happens if the shard fails to renew the `Lease` in time, which doesn't incur a watch update event.
For this, the controller calculates the time until the transition would occur and revisits the `Lease` after this duration.
It also watches `ClusterRings` and triggers reconciliations for all `Lease` objects belonging to a given ring, e.g., to ensure correct sharding decisions when the `ClusterRing` object is created after the shard `Leases`.

For partitioning, the sharder reads all shard `Leases` of a given `ClusterRing` from its watch cache and constructs a consistent hash ring including all available shards.
In this process, `Leases` are always read from the cache and a new ring is constructed every time instead of keeping a single hash ring up-to-date.
This is done to ensure consistency with the cache and watch events seen by the individual controllers.
Reading from a shared active hash ring, which can be considered another cache layer, can lead to race conditions where the hash ring has not been updated to reflect the state changes for which a controller was triggered.

The partitioning key of an object is determined based on whether it is configured as a main or controlled resource in the corresponding `ClusterRing`.
For main resources, the key is composed of `apiVersion`, `kind`, `namespace`, and `name`.
For controlled resources, the same key is constructed based on the controller reference information.
The `uid` field cannot be used as a partitioning key as it is unset during admission for `CREATE` requests.
With this, different object instances with the same name use the same key.
Only fields that are also present in owner references can be used as part of the partitioning key as owners and controlled objects must be assigned to the same shard.
With this, `generateName` cannot be used on main resources of sharded controllers, as this information is not present on controlled resources and the generated `name` is not set during admission for `CREATE` requests.

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingWebhookConfiguration
metadata:
  name: sharding-clusterring-50d858e0-example
webhooks:
- clientConfig:
    caBundle: LS0t...
    service:
      name: sharder
      namespace: sharding-system
      path: /webhooks/sharder/clusterring/example
      port: 443
  name: sharder.sharding.timebertt.dev
  namespaceSelector:
    matchLabels:
      role: project
  objectSelector:
    matchExpressions:
    - key: shard.alpha.sharding.timebertt.dev/clusterring-50d858e0-example
      operator: DoesNotExist
  rules:
  - apiGroups:
    - ""
    apiVersions:
    - '*'
    operations:
    - CREATE
    - UPDATE
    resources:
    - configmaps
    scope: '*'
  # ...
  failurePolicy: Ignore
  timeoutSeconds: 5
```

: Example sharder webhook configuration {#lst:sharder-webhook}

As shown in [@lst:sharder-webhook], the sharder webhook configuration points to a ring-specific webhook path.
The sharder uses the request path to determine for which `ClusterRing` the object should be assigned.
The `namespaceSelector` of the webhook configuration is copied from the `ClusterRing` specification.
If a `namespaceSelector` is configured neither in the `ClusterRing` nor the global sharder configuration, it defaults to excluding the `kube-system` and `sharding-system` namespaces.
This is done, to ensure the webhook doesn't interfere with the management of the cluster's system components and the sharder components themselves.
Additionally, an `objectSelector` is added that selects only unassigned objects of the ring, i.e., objects that don't carry the ring-specific `shard` label.
This ensures that the webhook is only requested when a label change is actually needed and not for all requests.
With this, the impact on API request latency is limited to the minimum.

Furthermore, the sharder is deployed with multiple replicas.
As usual, it performs leader election to determine a single active instance that should run the controllers to prevent conflict actions in concurrent reconciliations.
However, as webhook handlers are never called concurrently, it is safe to execute them in all instances even if they are not the elected leader.
With this, the sharder webhook is highly-available.
Problems in communicating with the sharder or executing the webhook handler should not cause API requests for sharded resources to hang or fail.
Hence, the webhook configuration sets a short timeout and instructs the API server to ignore failures in calling the webhook.
For managing the webhook server's certificate and populating the certificate bundle in the webhook configuration, the sharder relies on cert-manager [@certmanagerdocs] per default by adding the `cert-manager.io/inject-ca-from` annotation.

Finally, the sharder runs the "sharder" controller that handles changes to the set of available shards and to the ring's configuration.
It watches `ClusterRings` and shard `Leases` and reconciles all object assignments of a ring whenever its configuration changes or when a shard becomes available or unavailable (evt. \ref{evt:new-shard} and \ref{evt:shard-down}).
With this, the sharder can perform automatic rebalancing in response to dynamic instance changes or configuration changes (e.g., additional sharded resources) without human interaction.
Additionally, it is triggered periodically (every 5 minutes by default) to perform assignments of objects that were not assigned by the sharder webhook due to intermediate failures.

On each reconciliation, the sharder controller lists all objects for all sharded resources in a given `ClusterRing`.
For this, it uses multiple mechanisms to limit the resource usage and caused load on the control plane.
First, it lists only the metadata of the sharded objects to reduce the amount of network transfer and effort for encoding and decoding.
Second, it sets the `resourceVersion` request parameter to `0`, which instructs the API server to respond with a recent list state from its internal watch cache instead of performing a quorum read from etcd [@k8sdocs].
And finally, the controller performs paginated list requests to keep a limited number of objects in memory at any given time (500 objects by default).
This prevents spikes in the sharder's memory consumption.
Such spikes would be proportional to the number of sharded objects, which would limit the scalability of the system and conflict with req. \ref{req:constant}.

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
