# Fundamentals

## API Machinery {#sec:apimachinery}

Kubernetes is an open-source system for orchestrating container-based applications [@soltesz2007container] and cloud native infrastructure [@cncftoc] on clusters of machines.
It is an API-centric and declarative system in which clients specify the desired state of applications and infrastructure instead of managing them via imperative commands.
This approach is essential to Kubernetes' reliability, scalability, and manageability. [@k8sdesign]

The architecture of Kubernetes is divided into two parts: control plane and data plane.
The control plane oversees the cluster's state and orchestrates various operations, while the data plane executes workload containers and serves application traffic.
The core of the control plane is the API server, which stores cluster metadata and state in etcd, a highly-available key-value store that acts as the source of truth for the entire cluster [@etcddocs].
The state is specified and managed in the form of objects via RESTful [@fielding2000architectural] HTTP endpoints (resources).
All human and machine clients interact with the system through these resources. [@k8sdocs]

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
  namespace: dev
  labels:
    app: nginx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx
status:
  availableReplicas: 1
  readyReplicas: 1
  replicas: 1
  updatedReplicas: 1
```

: Example API object {#lst:deployment}

The Kubernetes resource model specifies patterns that all API resources follow.
Notably, both the desired and actual state are stored together in etcd.
[@Lst:deployment] shows an example object of the `deployments` resource in its YAML representation, including the common set of fields and sections: `apiVersion`, `kind`, `metadata`, `spec`, and `status`.
The `apiVersion` and `kind` fields combined map to the API resource, i.e., the particular API endpoint for retrieving and updating the given object.
All objects are referenced by name (`metadata.name`) and optionally – depending on the API resource – grouped into namespaces (`metadata.namespace`).

The `spec` section contains the desired state of the object, while the `status` section holds the actual state as reported by the responsible controller.
Although the desired and actual state are stored and managed together, the `status` section can only be updated by calling the `/status` subresource of the API resource.
This allows segregating authorization policies between individual API clients like users and controllers.

In contrast to imperative systems, Kubernetes strictly follows a declarative paradigm.
Imperative commands like `kubectl set image` [@k8sdocs] only modify the desired state, requesting the controllers to reconcile the actual state with the declared state.

In addition to serving endpoints for creating, updating, and deleting objects, the API server enhances the core functionality with a comprehensive set of API machinery.
It includes API discovery, versioning, defaulting, validation, authentication, authorization, and extensibility [@studyproject].
The most critical mechanisms in Kubernetes API machinery for this thesis are lookout requests, label selectors, optimistic locking, admission webhooks, and owner references.

Watch requests are a specialized form of list requests, identified by the included `watch=true` query parameter.
As for list requests, watch requests target all or a filtered set of objects of a single API resource.
Clients start a long-running watch request to subscribe to change events of the cluster's state.
Watch events are categorized as `ADDED`, `MODIFIED`, or `DELETED`, denoting different changes to the watched resource.
Each watch event contains the new state of the respective object.
This allows clients to build up a local cache of objects they can read from instead of contacting the API server. [@k8sdocs]

Under the hood, the Kubernetes API server leverages the watch feature of etcd [@etcddocs].
The API server watches a resource only once in etcd and maintains a short history of revisions within its internal watch cache.
I.e., it multiplexes client watch requests onto a single watch connection to etcd through this cache.
Watch requests can request change events starting from a specific revision in the kept history by setting the `resourceVersion` query parameter accordingly.
Typically, clients start the process with an initial list request, followed by a watch request with the `resourceVersion` parameter set to the value returned in the list response.

Clients can resume change notifications when the watch connection is interrupted by initiating a new watch request and specifying the last observed `resourceVersion`.
This mechanism ensures continuity in monitoring the cluster state, allowing clients to pick up where they left off.
As Kubernetes is a distributed system, delays and timeouts of watch requests can occur at any time.
Thus, clients must always expect the state observed via watch requests to be slightly out-of-date. [@k8sdesign]

Standard get and list requests utilize quorum read operations from etcd by default.
However, when a client sets the `resourceVersion` parameter, the API server responds based on its internal watch cache without directly querying etcd.
This can be used to retrieve a specific recent revision of objects or the latest revision as observed by the API servers watch connection to etcd. [@k8sdocs]

Clients can add label selectors to list and watch requests for filtering API objects based on key-value pairs in their `metadata.labels`.
Note that the API server always retrieves the complete list of objects from etcd or events from its watch cache.
It subsequently filters objects or events based on the specified label criteria and transmits a filtered list to the client.
This approach reduces the transferred data size, the effort for encoding and decoding in the API server and client, and the needed memory on the client side.
However, it neither reduces the transferred data size between the etcd and API server nor the effort for processing objects and events in the API server.

Additionally, field selectors offer another option for filtering objects based on specific field values.
However, this mechanism is only available for built-in resources and resources served by extension API servers [@studyproject].
Notably, only fields pre-defined by the API server can be used in selectors, eliminating the possibility of ad-hoc field queries.
Internally, the API server indexes the pre-defined fields in its watch cache to reduce processing and selection effort for watch requests.
Because of this, the application of field selectors is confined to particular cases, limiting their utility in a broader context.

\newpage

The Kubernetes API server resolves conflicts between concurrent updates through optimistic locking [@harder1984observations].
This mechanism builds upon etcd's multi-version concurrency control architecture [@etcddocs].
A key component in this approach is the `metadata.resourceVersion` field embedded in all objects, representing the specific revision of an object in the cluster.
Clients performing update or patch requests transmit the `resourceVersion` associated with their intended changes.
The API server, in turn, compares this version with the current `resourceVersion` of the object stored in etcd.
Conflict errors are triggered if the versions do not align, denying the requested changes.
This concurrency control mechanism ensures data consistency and integrity, enabling to handle simultaneous updates from multiple clients without active locking. [@k8sdocs]

The API server has internal admission plugins that perform dynamic validation and mutations to requests after API validation and defaulting.
Apart from admission plugins for built-in resources, the admission control logic can be augmented during runtime by the use of webhooks.
These webhooks can be applied to both built-in and custom resources, and can be registered through `ValidatingWebhookConfiguration` and `MutatingWebhookConfiguration` objects.
A webhook configuration defines which server should be contacted for specific requests and allows selection based on the requested resource, the operation type, as well as namespace and object labels.
When a client performs a relevant request, the API server dispatches an `AdmissionReview` object including the requested object and relevant request metadata to the designated webhook server.
After processing the `AdmissionReview` object, the webhook server responds with a validation result and in case of mutating webhooks, it may include patches to the object.
The API server considers the returned validation result and optionally applies the returned patches to the object before storing the updated object in etcd. [@k8sdocs]

All Kubernetes API objects can reference owning objects for establishing relationships between objects.
Controllers can mark objects owned by other objects by setting the `metadata.ownerReferences` field accordingly.
The garbage collector in the Kubernetes controller manager ensures that owned objects are deleted when all their owners have been deleted.
An API object can have multiple owner references, but only one of them may set the `controller` field to `true` (controller reference).
This mechanism resolves conflicts where multiple objects select an overlapping set of owned objects.
For this, controllers adopt existing objects by setting the respective controller reference before acting on them.
Typically, API objects have only one owner reference, which is also the controller reference. [@k8s]

## Controller Machinery {#sec:controller-machinery}

As described in the previous section, Kubernetes facilitates declarative configuration management.
When clients declare the desired state of an API object, the API server accepts the change and stores it in etcd, but it does not perform the necessary changes to fulfill the desired state.
When a new object is created or deleted, or the specification of an existing object is changed, the responsible controller needs to pick up the change to drive the actual state to match the desired state.
This process is called reconciliation.
Although controllers use watch events to get notified about changes, the system is asynchronous and only eventually consistent [@brewer2000towards; @vogels2008eventually].

Controllers can reconcile arbitrary API resources: built-in and extended resources registered via `CustomResourceDefinitions` or served by extension API servers.
With this, controllers are a powerful mechanism for orchestrating applications and infrastructure according to the user's needs.
The Kubernetes components include controllers for implementing the core API resources, but additional controllers can be installed in the cluster as desired.
Controllers working with extended API resources for automating application-specific operations are commonly referred to as operators. [@k8sdocs]

At the core, controllers watch and manipulate the cluster's state using a standard Kubernetes client.
All operations on API objects are performed via the usual endpoints served by the API server.
As such, controllers are stateless components, as their state is persisted externally.
If a controller restarts or crashes, it can pick up earlier work by reading the current state from the API server again.

The core components of Kubernetes controllers are the watch cache, event handlers, work queue, and worker routines.
A controller's cache is responsible for monitoring the object type on the API server, notifying the controller of changes to the objects, and maintaining object copies in memory as an indexed store.
For this, the controller initiates a reflector, which lists and watches the specified object type, emitting delta events added to a queue.
Subsequently, an informer reads events from the queue, updating the store with changed objects.
The flat key-value store has additional indices to increase the performance of frequently used namespaced queries or queries with field selectors.
Controllers can utilize caches for multiple object types, and typically, these caches are shared among all controllers within a single binary to optimize CPU and memory usage.
Additionally, caches can be configured to use filtered list and watch requests to reduce overhead for controllers not interested in certain objects. [@studyproject]

![Building blocks of a controller [@samplecontroller]](../assets/controller-components.jpg)

\newpage

The watch cache (the informer) also dispatches watch events to event handlers registered by controllers.
Event handlers typically filter relevant changes based on the updated object, minimizing unnecessary reconciliation work.
Based on this, event handlers optionally enqueue the object's key (`namespace/name`) to the work queue.
Event handlers may also perform mappings between watched objects and objects the controller is responsible for.
For example, the `Job` controller watches `Pods` and enqueues the owning `Job` when the corresponding `Pod` finishes its work.
On startup of a controller, it receives `ADDED` events for all existing objects.
To prevent inconsistencies due to watch events missed during a previous downtime, controllers should reconcile all objects on startup. [@studyproject]

The controller's work queue lines up keys of objects requiring reconciliation, decoupling event handling and reconciliation.
The work queue ensures that only a single worker processes each object key at a time and deduplicates keys added multiple times.
If a key of an object that is currently being reconciled is added to the queue again, it will only be reconciled again once the ongoing work has finished.
The queue also implements retries with exponential backoff and rate limiting for failed items.

Worker routines execute the controller's business logic (reconciliation), picking a single key from the work queue at a time.
After picking a key from the queue and marking it as being worked on, workers retrieve the entire object from the watch cache and perform reconciliation based on the state read from the cache.
Notably, controllers should not be purely event-driven.
Instead, controllers are designed to be edge-triggered but level-driven.
In other words, controllers must always act on the entire observed state of the cluster and not only based on an observed change.
Change notifications are only an optimization for immediately triggering reconciliations when required. [@studyproject; @k8sdesign; @hausenblas2019programming]

Kubernetes controllers can be implemented in any programming language that can interact with the API server via standard HTTP requests.
Many libraries and frameworks are available that implement Kubernetes clients and reusable building blocks for controllers as described above.
The following list includes popular controller libraries that are actively maintained at the time of writing: [@k8sdocs]

- **client-go** is the official Kubernetes client in Go that Kubernetes core components also use. It provides great flexibility but requires a deep understanding of controller concepts and much boilerplate code. [@clientgo]
- **controller-runtime** offers useful abstractions on top of the core implementations in client-go, making it easier to implement controllers in Go. This library is the foundation for higher-level generative tooling like Kubebuilder and Operator SDK. [@controllerruntime; @kubebuilderbook; @operatorsdk]
- **Java Operator SDK** implements similar abstractions as controller-runtime for controllers written in Java. [@javaoperatorsdk]
- **kube-rs** offers similar abstractions and tooling as client-go, controller-runtime, and Kubebuilder for controllers written in Rust. [@kubers]

Other frameworks are also available for implementing Kubernetes controllers that deviate conceptually from the typical controller mechanisms described above.
For example:

- **Metacontroller** is a controller implemented in Go that allows specifying controllers declaratively. It runs the common part of custom controllers and calls webhooks that implement the business logic of the custom controller. The webhook servers can be implemented in any programming language. [@metacontroller]
- **shell-operator** is a controller implemented in Go that allows running shell scripts for handling watch events. [@shelloperator]
- **kopf** is a framework for building controllers in python designed around modelling domain knowledge. In contrast to the typical controller structure, it is event-driven and directly handles watch events instead of enqueueing objects for reconciliation in worker routines. It also stores the last object state handled by the controller and the state of the controller itself in the API object. [@kopf]

The scalability of Kubernetes controllers is underpinned by several key mechanisms, reflecting learnings from running Kubernetes at scale.
Most importantly, watch requests are essential in running controllers for large-scale clusters by leveraging change notifications rather than relying on polling mechanisms.
This approach significantly reduces unnecessary communication overhead and ensures controllers can promptly react to relevant changes in the cluster state.
Built on that, controllers maintain a local cache, which is continually synchronized based on watch events received from the API server.
By storing all relevant state locally, controllers reduce the need to contact the API server for every reconciliation, thereby minimizing latency and enhancing overall system scalability.
Controllers always read the object for the enqueued object key from the watch cache instead of interacting with the API server.

Furthermore, using filtered watches enhances the system's scalability by reducing the volume of data processed and stored by controllers.
For instance, the kubelet employs a field selector for the `spec.nodeName` field in `Pods` to filter watch requests for `Pods` running on the kubelet's `Node`.

In situations with a high rate of changes or latency of watch connections, controllers might read an outdated version of the object from their cache.
When this happens, the controller might run into a conflict error when updating the object on the API server due the usage of optimistic concurrency control.
In case of errors like conflicts, controllers rely on an exponential backoff mechanism to retry reconciliations until the cache is up-to-date with the current state and the reconciliation can be performed successfully.
This ensures eventual consistency while reducing the average amount of API requests and network transfers needed for reconciliations.
With this, optimistic concurrency control contributes to the scalability of Kubernetes controllers by facilitating safe concurrent state changes by a high number of different actors.

Concurrent worker routines are another factor in achieving scalability.
Multiple tasks for different objects can be executed concurrently by starting multiple processors of reconciliation requests.
This approach enhances throughput, decreases queue wait times, and contributes to the overall scalability of the system.

## Leader Election {#sec:leader-election}

In Kubernetes controllers, the leader election mechanism addresses critical requirements for managing reconciliations across multiple instances.
Without coordination, simultaneous reconciliations executed by different controller instances can lead to conflicting actions and compromise the system's integrity.
Hence, controllers use a mechanism for establishing a leader among multiple instances to prevent concurrent reconciliations of a single object. [@studyproject]

Kubernetes offers a designated `Lease` API resource, and each controller deployment uses a single central `Lease` object ([@lst:lease]) to perform leader election.
On startup, a race determines the leader among running instances, with the first to acquire the lease assuming the leadership role.
Only the leader may execute reconciliations, ensuring a singular point of control.

```yaml
apiVersion: coordination.k8s.io/v1
kind: Lease
metadata:
  creationTimestamp: "2023-12-05T10:07:29Z"
  name: gardener-controller-manager
  namespace: garden
  resourceVersion: "47821525"
  uid: c609a301-05b2-4de1-beb9-15e710dfba4f
spec:
  acquireTime: "2023-12-05T10:49:04.472127Z"
  holderIdentity: gardener-controller-manager-86944bbdcb-q4d68
  leaseDurationSeconds: 15
  leaseTransitions: 3
  renewTime: "2023-12-15T13:13:59.022104Z"
```

: Example Lease {#lst:lease}

The Lease object is always acquired for a specified duration, as defined in `spec.leaseDurationSeconds`.
The leader must continuously renew the lease to keep its leadership.
If the leader fails to renew the lease, it must stop all reconciliations.
When the lease expires, other instances are permitted to contend for leadership, resulting in a leadership change.
When an instance is terminated, such as during rolling updates, the leader can voluntarily release the lease to speed up leadership handovers and minimize disruption.

Leader election ensures that only a single active leader exists at any given time.
Deploying multiple instances of the same controller establishes an active-passive high-availability (HA) setup [@ahluwalia2006high].
This configuration allows for fast failovers, as another instance on standby is ready to assume the leadership role.
It is important to note that this approach is distinct from horizontal scaling, as it maintains a single leader rather than distributing the workload across multiple controllers [@bondi2000characteristics; @jogalekar2000evaluating].

While leader election satisfies the requirement to prevent concurrent reconciliations of a single object across multiple controllers, it operates globally rather than on a per-object basis.
With this, a controller instance reconcile either all objects or none – which is not inherently required.
The implementation typically encapsulates the entire controller process.
I.e., the actual controllers are only executed when the lease lock is acquired, and the process is stopped immediately when leadership is lost.

In essence, leader election in Kubernetes controllers is essential to preventing conflicts arising from concurrent reconciliations.
However, it also restricts reconciliations of all objects to be performed by a single controller instance.

## Kubernetes Scalability {#sec:kubernetes-scalability}

[^k8s-scalability]: <https://github.com/kubernetes/community/blob/master/sig-scalability/README.md#kubernetes-scalability-definition-1>
[^k8s-thresholds]: <https://github.com/kubernetes/community/blob/master/sig-scalability/configs-and-limits/thresholds.md>
[^k8s-slos]: <https://github.com/kubernetes/community/blob/master/sig-scalability/slos/slos.md>

Scalability describes the ability of a system to handle increased load with adequate performance given that more resources are added to the system [@herbst2013elasticity; @bondi2000characteristics].
Note that quantifying the scale or load of a system reveals different dimensions depending on the system in question.
A commonly accepted approach for measuring the scalability of a system is to evaluate at which scale the system can operate without faults or decreased performance and then add resources to observe resulting changes in the system's load capacity.
[@duboc2007framework]

The basis for evaluating the scalability of a system is to define central performance indicators directly related to user experience.
In the context of reliability engineering, these are called service level indicators (SLIs) and must be measurable in a running system [@beyer2016site].
Next, target values – or service level objectives (SLOs) – for the chosen performance indicators must be defined.
As long as the measured performance indicators meet the desired targets, the system can be considered to be performing adequately and without faults.
Based on this, experimentation determines the maximum load the system can handle while satisfying the objectives.
[@jogalekar2000evaluating; @sanders201578]

While there is no definition for the scalability of Kubernetes controllers, the community (SIG scalability) has established a definition for the scalability of Kubernetes as a whole[^k8s-scalability].
In order to evaluate the scalability of controller setups in the scope of this thesis, a definition for the scalability of controllers is derived from the Kubernetes scalability definition.

The load on or scale of a Kubernetes cluster has many dimensions, for example: number of nodes, number of pods, pod churn, API request rate.
Evaluating the scalability of Kubernetes in every dimension is difficult and costly.
Hence, the community has declared a set of thresholds[^k8s-thresholds] for these load dimensions together, which can be considered as the limits for scaling a single Kubernetes cluster.
Most thresholds define a maximum supported number of API objects, while others define a maximum supported `Pod` churn rate or API request rate.
As long as a cluster is configured correctly and the load is kept within these limits, the cluster is guaranteed work reliably and perform adequately.
In Kubernetes development, regular load tests [@perftests] put test clusters under load as high as the declared thresholds to detect performance or scalability regressions.
[@k8scommunity]

Key SLIs are defined and measured during load tests to evaluate whether a cluster performs as desired under load.
For all SLIs, a corresponding SLO[^k8s-slos] is defined.
If the SLOs are not satisfied while keeping load within the recommended limits, the declared scalability goals are not met.
On the other hand, if the load thresholds can be increased while still satisfying SLOs, the system's scalability has improved.

It is important to note that such tests always evaluate a single setup with a static configuration.
Also, the load capacity of the test setup is directly influenced by configuration like the control plane machine size.
With this, the test results – whether or not SLOs are satisfied – might change even with slight changes to the setup's configuration.
In other words, these tests do not increase the load to determine the maximum under which the cluster still performs as desired.
Instead, the tests only verify that – given a reasonably large resource configuration – Kubernetes can perform as desired under a pre-defined amount of load.
I.e., the aim of these tests is not to measure the scalability of Kubernetes but to ensure that the community can satisfy its scalability goals.
[@k8scommunity]

At the time of writing, the Kubernetes community defines three official SLIs with corresponding SLOs that are satisfied when the load is below the recommended thresholds:
[@k8scommunity]

\newpage

I.  \slok{mutating}The latency of processing mutating API calls for single objects (`create`, `update`, `patch`, `delete`) for every (resource, verb) pair (excluding virtual and extended resources), measured as the 99th percentile per cluster-day, is at maximum 1 second.
II.  \slok{read}The latency of processing non-streaming read-only API calls (`get`, `list`) for every (resource, scope) pair (excluding virtual and extended resources), measured as the 99th percentile per cluster-day, is at maximum 1 second (for requests reading a single object) or at maximum 30 seconds (for requests reading all objects from a single namespace or all objects in the cluster).
III.  \slok{startup}The latency of starting pods without persistent volumes that don't required cluster autoscaling or preemption, excluding image pulling and init containers, until observed by a watch request, measured as the 99th percentile per cluster-day, is at maximum 5 seconds.

More SLIs and SLOs are being worked on but have not been defined precisely yet and are thus not guaranteed.
These SLIs include in-cluster network programming and execution latency, in-cluster DNS programming and lookup latency, and API-related latencies of watch requests, admission plugins, and webhooks.
[@k8scommunity]

## Controller Scalability {#sec:controller-scalability}

Based on the above definition of Kubernetes scalability, a definition for the scalability of Kubernetes controllers is derived.
In this context, "controller setup" refers to a set of coherent controller instances.
First, it is required to devise how to quantify the scale of or load on a specific controller setup.
As controllers are an essential part of Kubernetes, the load is quantified in a subset of Kubernetes' scaling dimensions.
For a given controller setup, the load has two dimensions:

1. \dimn{count}The number of API objects that the controller watches and reconciles.
2. \dimn{churn}The churn rate of API objects, i.e., the rate of object creations, updates, and deletions.

Next, the key SLIs and corresponding SLOs of a controller setup need to be specified.
As a prerequisite for these performance indicators to be meaningful, the official Kubernetes SLOs need to be satisfied by the cluster that the controllers are running on.
Most importantly, the control plane must facilitate reasonable API request processing latency.
To consider a controller setup as performing adequately, the following SLOs need to be satisfied:

1. \sloc{queue}The time of enqueuing object keys for reconciliation for every controller, measured as the 99th percentile per cluster-day, is at maximum 1 second.
2. \sloc{recon}The latency of realizing the desired state of objects for every controller, excluding reconciliation time of controlled objects, until observed by a watch request, measured as the 99th percentile per cluster-day, is at maximum $x$, where $x$ depends on the controller.

The queue duration (SLI \refsloc*{queue}) is comparable to the API request latency SLIs of Kubernetes (SLI \refslok*{mutating}, \refslok*{read}).
It captures the system's responsiveness, where a low queue duration results in a better user experience.
If the time object keys are queued for reconciliation is too high, changes to the objects' desired state are not processed promptly, and changes to objects' observed state are not recorded promptly.
The reconciliation latency (SLI \refsloc*{recon}) is comparable to Kubernetes' pod startup latency SLI (SLI \refslok*{startup}).
It measures how fast the system can bring the desired state of objects to reality.
However, it strongly depends on the type of controller.
For example, a simple controller owning a small set of objects should only take 5 seconds at maximum to configure them as desired, while a controller orchestrating a large set of objects or external infrastructure might take up to 1 minute to reach the desired state.

Based on these definitions, experimentation can be performed to determine the maximum amount of load under which the controller setup can still satisfy the SLOs.
The controller setup has a greater load capacity if the load is increased without violating the SLOs.
For the setup to be scalable, the load capacity must grow when more resources are added to the system.

Like Kubernetes, evaluating the scalability of controller setups in every dimension can become costly depending on the number of different API resources the controllers reconcile and watch.
Accordingly, a set of thresholds for each load dimension may be specified under which the controller setup is expected to satisfy the SLOs.

As in Kubernetes scalability tests, controller scalability tests evaluate a concrete setup.
Therefore, it is essential to record the critical configuration parameters of the evaluated setup.
These include the control plane's compute resources and other configurations relevant to the evaluated controller, e.g., the number of worker routines of dependant controllers and rate limits of kube-controller-manager.
Other important parameters are the controller's compute resources and the number of worker routines.

## Scalability Limitations {#sec:scalability-limitations}

While Kubernetes and its controllers are already scalable to a good extent, there are limitations to scaling controllers inherent in the leader election mechanism.
Understanding how a controller's load dimensions, SLIs, and resource usage are related is essential to discuss these limitations.

When increasing the load by adding more objects (\refdimn{count}), the controller's watch cache requires more memory for caching the additional objects.
This doesn't have a direct impact on the SLIs.
However, when consuming more memory than available, the controller might fail due to out-of-memory faults.
When the load on a controller grows by increasing the object churn rate (\refdimn{churn}), more watch events for relevant objects are transferred over the network.
The processing of the additional watch events also results in a higher CPU usage for decoding and for performing reconciliations.
If the number of worker routines is not high enough to facilitate the needed rate of reconciliations, the queue time (SLI \refsloc*{queue}) increases.
Also, if performing reconciliations is computationally intensive, the extra CPU usage might exhaust the available CPU cycles, increasing the reconciliation latency (SLI \refsloc*{recon}).

More resources can be added to the setup to expand the load capacity of the controller setup or to fulfill the SLOs under increased load.
One option is to allocate more memory for the controller, which can increase the maximum number of objects that a controller's watch cache can store.
Another option is to add more worker routines or allocate more CPU cycles for the controller, which can reduce queue times and reconciliation latency.
Lastly, the network bandwidth can be expanded to ensure prompt delivery of watch events and API requests, reducing reconciliation latency.
Increasing CPU allocation and network bandwidth can allow the controller to handle higher churn rates.
[@studyproject; @flux]

As described, Kubernetes controllers are scalable, as their load capacity can be increased by adding more resources to the system.
However, they can only be scaled vertically, i.e., by adding more resources to the existing controller instance.
Due to the controller's leader election ([@sec:leader-election]), the reconciliation work cannot be distributed across multiple instances.
Hence, this does not allow active-active setups, i.e., the load capacity cannot be increased by adding more resources in the form of additional instances.
In other words, Kubernetes controllers are not horizontally scalable.
Vertical scaling is required to keep fulfilling the SLOs when the load on a controller setup increases.
[@jogalekar2000evaluating; @studyproject; @kubevela]

While scaling controllers vertically increases the setup's load capacity, one cannot perform vertical scaling infinitely.
Running controllers at extreme vertical scale can cause the setup to violate the SLOs due to other limitations, e.g., the maximum available machine size or network bandwidth.
With this, the maximum scale of a controller setup in terms of the number of objects and object churn rate is limited because controllers cannot be scaled horizontally.
[@studyproject; @kubevela]

Relying on a single active controller instance and vertical scaling only poses additional challenges and drawbacks.
For example, running multiple instances of a controller, even if only one of them is active for facilitating fast failovers and achieving higher availability, is desirable.
However, this wastes compute resources allocated for instances in standby, and right-sizing resource requests becomes difficult as the actual resource consumption depends on the leadership status.
Also, a failure or performance degradation in a single controller instance blocks or affects the reconciliation of all objects [@kubevela].
Additionally, scaling up controllers vertically might only work with downtime, e.g., when migration to a bigger machine size is required.
Lastly, depending on the control plane networking setup, running a single controller instance with HTTP2 enabled might only load a single API server instance, as all API requests are multiplexed over a single TLS connection.
