# Implementation {#sec:implementation}

This chapter describes an implementation of the design presented in chapter [-@sec:design].
It elaborates on the most critical aspects of implementing the sharding mechanism.
Afterward, the implementation is evaluated in chapter [-@sec:evaluation].

## ClusterRing Resource {#sec:impl-clusterring}

The central element of the sharding design is the `ClusterRing` custom resource.
A corresponding `CustomResourceDefinition` is installed together with the sharder itself.
It serves as a configuration point for aligning the sharder's actions with the needs of the sharded controller.
The sharded controller does not communicate directly with the sharder or vice versa.
Instead, all necessary information is persisted in API objects, e.g., configured in the `ClusterRing` resource when deploying the controller.

```text
alpha.sharding.timebertt.dev/clusterring=<clusterring-name>
```

: Ring-specific lease label pattern {#lst:lease-label}

Both the sharder's and the shard's components must follow the contracts related to the `ClusterRing` configuration.
Most importantly, this includes patterns for shard leases and the labels on sharded objects.
For announcing themselves to the sharder, controller instances need to label their individual `Lease` objects with the `clusterring` label according to the pattern shown in [@lst:lease-label].
This allows the sharder to select all `Lease` objects belonging to a given `ClusterRing` for partitioning.
Additionally, the sharder can add a label selector to its `Lease` watch cache to filter out any `Lease` objects not related to shards, e.g., leader election locks of other controllers.

```text
shard.alpha.sharding.timebertt.dev/clusterring-<hash>-<clusterring-name>
```

: Ring-specific shard label pattern {#lst:shard-label}

As resources can be part of multiple `ClusterRings`, the sharder uses ring-specific labels to assign objects to shards and initiate the handover protocol.
The shard label follows the pattern shown in [@lst:shard-label].
The pattern includes the first eight hex characters of the SHA256 checksum of the `ClusterRing` name.
This is done because the label part after the slash must not exceed the 63-character limit.
If the `ClusterRing` name is too long, the second label part is shortened to 63 characters.
However, by including a name hash, the sharder can still derive a unique label for each `ClusterRing` even if they have long names with a common prefix.

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

: Example ClusterRing with status {#lst:clusterring-status}

As the resource name suggests, the `ClusterRing` resource is cluster-scoped.
I.e., the object itself does not reside in a namespace and configures behavior on a cluster-global level.
This means that the controller's resources are sharded in multiple namespaces.
However, besides listing the sharded API resources, the `ClusterRing` specification also allows configuring a `namespaceSelector` to select namespaces in which the configured API resources should be sharded.
Only if the labels of the object's namespace match the configured `namespaceSelector` is the object considered for assignments by the sharder.

The ring configuration could also be implemented as a namespace-scoped `Ring` resource that acts only on objects in the same namespace.
However, by using the `namespaceSelector` feature, a `ClusterRing` can be restricted to a single namespace, effectively implementing namespace-scoped sharding.

Finally, the sharder populates the `ClusterRing` status with information about the number of discovered ring members.
The `status.shards` field describes how many shard leases with a matching `clusterring` label have been discovered.
Additionally, the `status.availableShards` field depicts how many of these shards are healthy and available for assignments.
Also, the `Ready` reflects whether the sharding mechanism configured by the `ClusterRing` has been successfully reconciled.

## Sharder Components {#sec:impl-sharder}

The sharder runs several components, including controllers and webhooks, that facilitate the core logic of the sharding mechanism.

The `ClusterRing` controller is responsible for configuring the sharder webhooks.
Every `ClusterRing` object generates one `MutatingWebhookConfiguration` ([@lst:sharder-webhook]).
The configuration contains a single webhook for unassigned objects of all resources listed in the `ClusterRing` specification.
In addition to watching `ClusterRing` objects for spec changes, the controller also watches shard `Leases` for availability changes.
It reports the total number, the number of available shards, and the `Ready` condition in the `ClusterRing` status ([@lst:clusterring-status]).

The shard lease controller is responsible for detecting instance failures based on the `Lease` objects that every shard maintains.
Like in the study project implementation, it watches all shard `Leases` and determines the state of each shard following the conditions in [@tbl:shard-states].
When a shard becomes uncertain, it tries to acquire the `Lease` to ensure connectivity with the API server.
Only if the controller can acquire the `Lease` is the shard considered unavailable and removed from partitioning.
I.e., all shards in states ready, expired, and uncertain are considered available and included in partitioning.
Orphaned `Leases` are garbage collected by the shard lease controller.
For increased observability, the shard lease controller writes the determined state to the `alpha.sharding.timebertt.dev/state` label on the respective `Lease` objects.
[@studyproject]

|Shard State|Conditions|
|---:|-------------------|
|ready|held by shard (`metadata.name == spec.holderIdentity`), not expired|
|expired|held by shard, expired up to `spec.leaseDurationSeconds` ago|
|uncertain|held by shard, expired more than `spec.leaseDurationSeconds` ago|
|dead|not held by shard (released or acquired by sharder)|
|orphaned|not held by shard, expired at least 1 minute ago|

: Shard lease states [@studyproject] {#tbl:shard-states}

The controller watches the `Lease` objects for relevant changes to ensure responsiveness.
However, it also revisits `Leases` after a specific duration when their state would change if no update event occurs.
E.g., the transition from ready to expired happens if the shard fails to renew the `Lease` in time, which does not incur a watch update event.
For this, the controller calculates the time until the transition would occur and revisits the `Lease` after this duration.
It also watches `ClusterRings` and triggers reconciliations for all `Lease` objects belonging to a ring, e.g., to ensure correct sharding decisions when the `ClusterRing` object is created after the shard `Leases`.

For partitioning, the sharder reads all shard `Leases` of a given `ClusterRing` from its watch cache and constructs a consistent hash ring of all available shards.
In this process, `Leases` are always read from the cache, and a new ring is constructed every time instead of keeping a single hash ring up-to-date.
This ensures consistency with the cache and watch events seen by the individual controllers.
Reading from a shared hash ring, which can be considered another cache layer, can lead to race conditions where the hash ring still needs to be updated to reflect the state changes for which a controller has been triggered.

The partitioning key of an object is determined based on whether it is configured as a main or controlled resource in the corresponding `ClusterRing`.
For main resources, the key is composed of `apiVersion`, `kind`, `namespace`, and `name`.
The same key is constructed for controlled resources based on the controller reference information.
The `uid` field cannot be used as a partitioning key as it is unset during admission for `CREATE` requests.
With this, different object instances with the same name use the same key.
Only fields in owner references can be part of the partitioning key, as owners and controlled objects must be assigned to the same shard.
With this, `generateName` cannot be used on the main resources of sharded controllers, as this information is not present on controlled resources, and the generated `name` is not set during admission for `CREATE` requests.

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
This ensures the webhook does not interfere with managing the cluster's system and sharder components.
Additionally, an `objectSelector` selects only unassigned objects of the ring, i.e., objects that do not carry the ring-specific `shard` label.
With this, the webhook is only requested when a label change is needed and not for all requests.
With this, the impact on API request latency is minimal.

Furthermore, the sharder is deployed with multiple replicas.
It performs a leader election to determine a single active instance that should run the controllers to prevent conflict actions in concurrent reconciliations.
However, as webhook handlers are never called concurrently for the same object, executing them in all instances is safe, even if they are not the elected leader.
With this, the sharder webhook is highly available.
Problems in communicating with the sharder or executing the webhook handler should not cause API requests for sharded resources to hang or fail.
Hence, the webhook configuration sets a short timeout and instructs the API server to ignore failures in calling the webhook.
For managing the webhook server's certificate and populating the certificate bundle in the webhook configuration, the sharder relies on cert-manager [@certmanagerdocs] per default by adding the `cert-manager.io/inject-ca-from` annotation.

```json
{
  "kind": "AdmissionReview",
  "apiVersion": "admission.k8s.io/v1",
  "response": {
    "allowed": true,
    "status": {
      "message": "assigning object",
      "code": 200
    },
    "patchType": "JSONPatch",
    "patch": [
      {
        "op": "add",
        "path": "/metadata/labels/ shard.alpha.sharding.timebertt.dev~1clusterring-50d858e0-example",
        "value": "shard-74bbb768b9-wpsfb"
      }
    ]
  }
}
```

: Example sharder webhook response {#lst:webhook-response}

When the API server calls the webhook, the sharder first determines the corresponding `ClusterRing` object from the request path and the partitioning key to use for the requested object.
It then reads all shards of the ring from the `Lease` cache and constructs a consistent hash ring with all available instances.
Afterward, it determines the desired shard and responds to the API server with an object patch, adding the `shard` label as shown in [@lst:webhook-response].

Finally, the sharder runs the "sharder" controller that handles changes to the set of available shards and the ring's configuration.
It watches `ClusterRings` and shard `Leases` to reconcile all object assignments of a ring whenever its configuration changes or when a shard becomes available or unavailable (evt. \ref{evt:new-shard} and \ref{evt:shard-down}).
With this, the sharder can perform automatic rebalancing in response to dynamic instance changes or configuration changes (e.g., additional sharded resources) without human interaction.
Additionally, it is triggered periodically (every 5 minutes by default) to perform assignments of objects not assigned by the sharder webhook due to intermediate failures.

The sharder controller lists all objects for all sharded resources in a given `ClusterRing` on each reconciliation.
For this, it uses multiple mechanisms to limit the resource usage and the load on the control plane.
First, it lists only the metadata of the sharded objects to reduce the amount of network transfer and effort for encoding and decoding.
Second, it sets the `resourceVersion` request parameter to `0`, instructing the API server to respond with a recent list state from its internal watch cache instead of performing a quorum read from etcd [@k8sdocs].
Finally, the controller performs paginated list requests to keep a limited number of objects in memory at any given time (500 objects by default).
This prevents excessive spikes in the sharder's memory consumption.
Such spikes would be proportional to the number of sharded objects, limiting the system's scalability and conflict with req. \ref{req:constant}.

## Shard Components {#sec:impl-shard}

[^implementation]: <https://github.com/timebertt/kubernetes-controller-sharding>

While the external sharder implements the core sharding logic, sharded controllers still need to implement a few aspects to comply with the `ClusterRing` contract.
Developers need to implement the following aspects to use sharding in arbitrary Kubernetes controllers ([@sec:design-external]):

- The shards announce ring membership by maintaining individual `Leases` instead of performing leader election on a single `Lease`.
- The controllers only watch, cache, and reconcile objects assigned to the respective shard by adding a shard-specific label selector to their watches.
- The controllers acknowledge object movements during rebalancing by removing the `drain` and `shard` labels whenever the sharder adds the `drain` label and stop reconciling the object immediately.

The implementation repository[^implementation] contains reusable reference implementations for these aspects.
Developers can use them in controllers based on controller-runtime [@controllerruntime].
However, the aspects can also be implemented similarly in controllers not based on controller-runtime or written in another programming language than Go.

```yaml
apiVersion: coordination.k8s.io/v1
kind: Lease
metadata:
  labels:
    alpha.sharding.timebertt.dev/clusterring: my-clusterring
  name: my-operator-565df55f4b-5vwpj
  namespace: operator-system
spec:
  holderIdentity: my-operator-565df55f4b-5vwpj # must equal the Lease's name
  leaseDurationSeconds: 15 # similar to usual leader election
```

: Example shard lease {#lst:shard-lease}

Most controllers already perform leader elections using a central `Lease` lock object and are configured to stop any controllers when they lose their `Lease`.
Most implementations exit the entire process when failing to renew the lock for safety.
These leader election mechanisms can be reused to maintain the shard `Lease` as shown in [@lst:shard-lease].
Instead of using a central `Lease` object for all instances, each instance acquires and maintains its own `Lease` object to announce itself to the sharder.
A shard may only run its controllers if it holds its shard `Lease`.
For example, it must stop all controllers when it fails to renew the shard `Lease` in time.
Similar to the usual leader election, a shard may release its own shard `Lease` on graceful termination by removing the `holderIdentity`.
This immediately triggers reassignments by the sharder to minimize the duration where no shard acts on a subset of objects.

Essentially, the existing leader election machinery can be reused to maintain the shard `Lease` with two changes.
First, the shard `Lease` needs to be labeled with `alpha.sharding.timebertt.dev/clusterring=<clusterring-name>` to specify to which `ClusterRing` the shard belongs.
Second, the shard's `Lease` name needs to match the `holderIdentity`.
By default, the instance's hostname is used for both values.
If the `holderIdentity` differs from the name, the sharder assumes that the shard is unavailable.
In controller-runtime, the shard's manager can be configured to maintain a shard `Lease` as shown in [@lst:go-shard-lease].

```go
import (
  shardlease "github.com/timebertt/kubernetes-controller-sharding/pkg/shard/lease"
  "sigs.k8s.io/controller-runtime/pkg/client/config"
  "sigs.k8s.io/controller-runtime/pkg/manager"
)

func run() error {
  shardLease, err := shardlease.NewResourceLock(
    restConfig, nil, shardlease.Options{
      ClusterRingName: "my-clusterring",
    },
  )
  if err != nil {
    return err
  }

  mgr, err := manager.New(restConfig, manager.Options{
    // Use manager's leader election mechanism for maintaining the shard lease.
    // With this, controllers will only run as long as manager holds the shard
    // lease. After graceful termination, the shard lease will be released.
    LeaderElection:                      true,
    LeaderElectionResourceLockInterface: shardLease,
    LeaderElectionReleaseOnCancel:       true,

    // other options ...
  })
  if err != nil {
    return err
  }

  // add controllers and start manager as usual ...
  return nil
}
```

: Maintaining a shard lease in controller-runtime {#lst:go-shard-lease}

Next, the sharded controllers must use a label selector on watches for all sharded resources listed in the `ClusterRing` as described in [@sec:impl-clusterring].
The shard label's value is the name of the shard, i.e., the name of the shard lease and the shard lease's `holderIdentity`.
With this, the shard will only cache the objects assigned to it, and the controllers will only reconcile this subset of objects.
Note that when using a label selector on a watch request and the label changes so that the selector now matches or does not match anymore, the API server will emit a `ADD` or `DELETE` watch event respectively.
In controller-runtime, the shard's manager can be configured to watch and reconcile only objects assigned to it, as shown in [@lst:go-filter-cache][^filter-cache-version].

[^filter-cache-version]: The shown code works with controller-runtime v0.16 and v0.17, other versions might require deviating configuration.

```go
import (
  shardingv1alpha1 "github.com/timebertt/kubernetes-controller-sharding/pkg/apis/sharding/ v1alpha1"
  "k8s.io/apimachinery/pkg/labels"
  "sigs.k8s.io/controller-runtime/pkg/cache"
  "sigs.k8s.io/controller-runtime/pkg/manager"
)

func run() error {
  // ...

  mgr, err := manager.New(restConfig, manager.Options{
    Cache: cache.Options{
      // Configure cache to only watch objects that are assigned to this shard.
      // This shard only watches sharded objects, so we can configure the label
      // selector on the cache's global level. If the shard watches sharded
      // objects as well as non-sharded objects, use cache.Options.ByObject to
      // configure the label selector on object level.
      DefaultLabelSelector: labels.SelectorFromSet(labels.Set{
        shardingv1alpha1.LabelShard(shardingv1alpha1.KindClusterRing, "", "my-clusterring"): shardLease.Identity(),
      }),
    },

    // other options ...
  })

  // ...
}
```

: Filtering the watch cache in controller-runtime {#lst:go-filter-cache}

```text
drain.alpha.sharding.timebertt.dev/clusterring-<hash>-<clusterring-name>
```

: Ring-specific drain label pattern {#lst:drain-label}

Finally, the sharded controllers must comply with the handover protocol initiated by the sharder.
When the sharder needs to move an object from an available shard to another for rebalancing, it first adds the `drain` label to instruct the currently responsible shard to stop reconciling the object.
The shard must acknowledge this operation, as the sharder must prevent concurrent reconciliations of the same object in multiple shards.
The `drain` label's key is specific to the `ClusterRing` and follows the pattern shown in [@lst:drain-label].
The `drain` label's value is irrelevant; only the presence of the label is relevant.

```go
import (
  shardcontroller "github.com/timebertt/kubernetes-controller-sharding/pkg/shard/ controller"
  "sigs.k8s.io/controller-runtime/pkg/builder"
  "sigs.k8s.io/controller-runtime/pkg/manager"
  "sigs.k8s.io/controller-runtime/pkg/reconcile"
)

func add(mgr manager.Manager, clusterRingName, shardName string) error {
  var r reconcile.Reconciler

  // Use the shardcontroller package as helpers for:
  // - a predicate that triggers when the drain label is present
  //   (even if the actual predicates don't trigger)
  // - wrapping the actual reconciler in a reconciler that handles the drain
  //   operation
  return builder.ControllerManagedBy(mgr).
    Named("example").
    For(
      &corev1.ConfigMap{}, builder.WithPredicates(
        shardcontroller.Predicate(
          clusterRingName, shardName, MyConfigMapPredicate(),
        ),
      ),
    ).
    Owns(&corev1.Secret{}, builder.WithPredicates(MySecretPredicate())).
    Complete(
      shardcontroller.NewShardedReconciler(mgr).
        For(&corev1.ConfigMap{}). // must match the kind in For() above
        InClusterRing(clusterRingName).
        WithShardName(shardName). // must match the shard lease's name
        MustBuild(r),
    )
}
```

: Acknowledging drain operations in controller-runtime {#lst:go-wrapper}

Besides changing the controller's business logic to check the `drain` label, developers must ensure that the watch event filtering logic (predicates in controller-runtime) always reacts to events with the `drain` label set independent of the controller's actual predicates.
In controller-runtime, the helpers from the implementation repository can be used for constructing correct predicates and a wrapping reconciler that correctly implements the drain operation, as shown in [@lst:go-wrapper].

## Example Setup {#sec:impl-setup}

Users can install the sharding system components using manifests in the implementation repository.
The default installation includes the `sharding-system` namespace, the `ClusterRing` `CustomResourceDefinition`, a highly-available `sharder` deployment, and a cert-manager `Certificate` for the webhook server.

In addition to installing the system components, manifests are available for installing monitoring for the sharding setup.
This includes a Prometheus operator `ServiceMonitor` [@prometheusoperatordocs], configuring a Prometheus instance to scrape the sharder's metrics [@prometheusdocs].
The set of metrics includes various counters for the core actions taken by the sharder, e.g., the number of assignments performed by the sharder webhook.
These can be used to monitor the sharding mechanism and ensure the sharder is functioning correctly.

Furthermore, the monitoring installation includes a metrics exporter based on kube-state-metrics [@kubestatemetrics].
It exports metrics about the state of `ClusterRings` and shard `Leases`, e.g., the observed shard state and the number of available shards per `ClusterRing`.

For demonstrating the sharding mechanism, an example shard implementation is also available in the implementation repository.
It leverages the reusable shard components described in [@sec:impl-shard] for building a simple sharded controller based on controller-runtime.
The controller reconciles `ConfigMaps` in the `default` namespace and creates a `Secret` including the configmap's name prefixed with `dummy-`.
The created `Secrets` are controlled by the respective `ConfigMap`, i.e., they have an `ownerReference` with `controller=true` to the `ConfigMap`.

All these components are bundled together in a comprehensive development and testing setup.
It serves as an entry point for controller developers to get started with controller sharding.
The setup runs in a local kind cluster [@kinddocs] for development and testing without infrastructure cost.
In addition to the sharding system components and the example shard, the setup automatically installs several required external components for a smooth experience.
It includes cert-manager [@certmanagerdocs], a monitoring setup based on kube-prometheus [@prometheusoperatordocs], a profiling setup based on parca [@parcadocs], and an ingress controller.
[@lst:example-setup] shows how the example setup can be bootstrapped.

```text
$ make kind-up
$ export KUBECONFIG=$PWD/hack/kind_kubeconfig.yaml
$ make deploy TAG=latest

$ kubectl -n sharding-system get po
NAME                       READY   STATUS    RESTARTS   AGE
sharder-57889fcd8c-p2wxf   1/1     Running   0          44s
sharder-57889fcd8c-z6bm5   1/1     Running   0          44s

$ kubectl get po
NAME                     READY   STATUS    RESTARTS   AGE
shard-7997b8d9b7-9c2db   1/1     Running   0          45s
shard-7997b8d9b7-9nvr2   1/1     Running   0          45s
shard-7997b8d9b7-f9gtd   1/1     Running   0          45s

$ kubectl get clusterring
NAME      READY   AVAILABLE   SHARDS   AGE
example   True    3           3        64s

$ kubectl get lease -L alpha.sharding.timebertt.dev/clusterring, alpha.sharding.timebertt.dev/state
NAME                     HOLDER                   AGE   CLUSTERRING   STATE
shard-7997b8d9b7-9c2db   shard-7997b8d9b7-9c2db   75s   example       ready
shard-7997b8d9b7-9nvr2   shard-7997b8d9b7-9nvr2   75s   example       ready
shard-7997b8d9b7-f9gtd   shard-7997b8d9b7-f9gtd   76s   example       ready

$ kubectl get mutatingwebhookconfiguration -l app.kubernetes.io/ name=controller-sharding
NAME                                    WEBHOOKS   AGE
sharding-clusterring-50d858e0-example   1          2m50s
```

: Bootstrapping the example setup {#lst:example-setup}
