# Fundamentals

## API Machinery

Kubernetes is an open-source system for orchestrating container-based applications [@soltesz2007container] and cloud native infrastructure [@cncftoc] on clusters of machines.
It is an API-centric and declarative system, in which clients specify the desired state of applications and infrastructure instead of managing them via imperative commands.
This approach is an essential aspect of the reliability, scalability, and manageability of Kubernetes. [@k8sdesign]

The architecture of Kubernetes can be separated into two parts: the control plane and the data plane.
The control plane oversees the cluster's state and orchestrates various operations, while the data plane executes workload containers and serves application traffic.
The core of the control plane is the API server which stores the cluster's metadata and state in etcd, a highly-available key-value store that acts as the source of truth for the entire cluster [@etcddocs].
The state is specified and managed in the form of objects via RESTful [@fielding2000architectural] HTTP endpoints (resources).
All clients – human and machine clients – interact with the system through these resources. [@k8sdocs]

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
Notably, both desired and actual state are stored together in etcd.
[@Lst:deployment] shows an example object of the `deployments` resource in its YAML representation, including the common set of fields and sections: `apiVersion`, `kind`, `metadata`, `spec`, and `status`.
The `apiVersion` and `kind` fields combined map to the API resource, i.e., the particular API endpoint for retrieving and updating the given object.
All objects are referenced by name (`metadata.name`) and optionally – depending on the API resource – grouped into namespaces (`metadata.namespace`).

The `spec` section contains the desired state of the object, while the `status` section holds the actual state as reported by the responsible controller.
Although desired and actual state are stored and managed together, the `status` section can only be updated by calling the `/status` subresource of the API resource.
This allows segregating authorization policies between individual API clients like users and controllers.

In contrast to imperative systems, Kubernetes strictly follows a declarative paradigm.
Imperative commands like `kubectl set image` [@k8sdocs] only modify the desired state, requesting the controllers to reconcile the actual state with the declared state.

In addition to serving endpoints for creating, updating, and deleting objects, the API server enhances the core functionality with a comprehensive set of API machinery.
This includes API discovery, versioning, defaulting, validation, authentication, authorization, and extensibility [@studyproject].
The most important mechanism in Kubernetes API machinery for this thesis are: watch requests, label selectors, optimistic locking, admission webhooks and owner references.

Watch requests are a specialized form of list requests, distinguishable by the inclusion of the `watch=true` query parameter.
As for list requests, watch requests target all or a filtered set of objects of a single API resource.
Clients start a long-running watch request to subscribe to change events of the cluster's state.
Watch events are categorized as `ADDED`, `MODIFIED`, or `DELETED`, denoting different types of changes to the watched resource.
Each watch event contains the new state of the respective object.
This allows clients to build up a local cache of objects, from which they can read instead of contacting the API server. [@k8sdocs]

Under the hood, the Kubernetes API server leverages the watch feature of etcd [@etcddocs].
The API server watches a resource only once in etcd and maintains a short history of revisions within its internal watch cache.
Client watch requests are multiplexed onto a single watch connection to etcd through this cache.
Watch requests can request change events starting from a specific revision in the kept history by setting the `resourceVersion` query parameter accordingly.
Typically, clients start the process with an initial list request, followed by a watch request with the `resourceVersion` parameter set to the value returned in the list response.

When the watch connection is interrupted, clients can resume change notifications by initiating a new watch request and specifying the last observed `resourceVersion`.
This mechanism ensures continuity in monitoring the cluster state, allowing clients to pick up where they left off.
As Kubernetes is a distributed system, delays and timeouts of watch requests can occur at any time.
Thus, clients must always expect that the state observed via watch requests is slightly out-of-date. [@k8sdesign]

Standard get and list requests utilize quorum read operations from etcd by default.
However, when the `resourceVersion` parameter is set, the API server responds based on its internal watch cache without directly querying etcd.
This can be used to retrieve a specific recent revision of objects, or the latest revision of objects as observed by the API servers watch connection to etcd. [@k8sdocs]

Label selectors can be added to list and watch requests for filtering API objects based on key-value pairs in their `metadata.labels`.
Note that the API server always retrieves the complete list of objects from etcd or events from its watch cache.
It subsequently filters the objects or events based on the specified label criteria and transmits the filtered list to the client.
This approach reduces the transferred data size, the effort for encoding and decoding in API server and client, and the needed memory on the client-side.
However, it does neither reduce the transferred data size between etcd and API server nor the effort for processing objects and events in the API server.
\todo{watch events with label selectors on label changes}

Additionally, field selectors offer another option for filtering objects, based on specific field values.
However, this mechanism is exclusive to built-in resources and resources served by extension API servers [@studyproject].
Notably, only fields pre-defined by the API server can be used in selectors, eliminating the possibility of ad-hoc field queries.
Internally, the API server indexes the pre-defined fields in its watch cache to reduce processing and selection effort for watch requests.
Because of this, the application of field selectors is confined to very specific cases, limiting their utility in a broader context.

The Kubernetes API server resolves conflicts between concurrent updates through optimistic locking [@harder1984observations].
This mechanism is built upon etcd's multi-version concurrency control architecture [@etcddocs].
A key component in this approach is the `metadata.resourceVersion` field embedded in all objects, representing the specific revision of an object in the cluster.
Clients performing update or patch requests transmit the `resourceVersion` associated with their intended changes.
The API server, in turn, compares this version with the current `resourceVersion` of the object stored in etcd.
Conflict errors are triggered if the versions do not align, resulting in the denial of the requested changes.
This concurrency control mechanism ensures data consistency and integrity, enabling to handle simultaneous updates from multiple clients without active locking. [@k8sdocs]

The API server has internal admission plugins that perform dynamic validation and mutations to requests after API validation and defaulting.
Apart from admission plugins for built-in resources, the admission control logic can be augmented during runtime by the use of webhooks.
These webhooks are applicable to both built-in and custom resources and are registered through `ValidatingWebhookConfiguration` and `MutatingWebhookConfiguration` objects.
A webhook configuration defines which server should be invoked for specific requests and allows selection based on the requested resource, the operation type, as well as namespace and object labels.
When a relevant request is made, the API server dispatches an `AdmissionReview` object including the requested object and relevant request metadata to the designated webhook server.
After processing the `AdmissionReview` object, the webhook server responds with a validation result, and in the case of mutating webhooks, may include optional patches to be applied to the object.
The API server considers the returns validation result and optionally applies the returned patches to the object before storing the updated object in etcd. [@k8sdocs]

All Kubernetes API objects can reference owning objects for establishing relationships between objects.
Controllers can mark objects owned by other objects by setting the `metadata.ownerReferences` field accordingly.
The garbage collector in the Kubernetes controller manager ensures that owned objects are deleted when all its owners have been deleted.
An API object can have multiple owner references but only one of them may set the `controller` field to `true` (controller reference).
This mechanism is used to resolve conflicts where multiple objects select an overlapping set of owned objects.
For this, controllers adopt owned objects by setting the respective controller reference first before acting on them.
Typically, API objects have only one owner reference which also the controller reference. [@k8s]

## Controller Machinery

As described in the previous section, Kubernetes facilitates declarative configuration management.
When clients declare the desired state of an API object, the API server accepts the change and stores it in etcd, but it does not perform the necessary changes to fulfill the desired state.
When a new object is created or deleted, or the specification of an existing object is changed, the responsible controller needs to pick up the change to drive the actual state to match the desired state.
This process is referred to as reconciliation.
Although controllers use watch events to get notified about changes, the system is asynchronous and only eventually consistent [@brewer2000towards; @vogels2008eventually].

Controllers can reconcile arbitrary API resources: built-in resources as well as extended resources registered via `CustomResourceDefinitions` or served by extension API servers.
This makes controllers a powerful mechanism for orchestrating applications and infrastructure according to the user's needs.
The Kubernetes components include controllers for implementing the core API resources, but additional controllers can be installed in the cluster as desired.
Controllers working with extended API resources for automating application-specific operations are commonly referred to as operators. [@k8sdocs]

At the core, controllers watch and manipulate the cluster's state using a standard Kubernetes client.
All operations on API objects are performed via the usual endpoints served by the API server.
As such, controllers are stateless components, as all state is persisted externally.
If a controller is restarted or crashes, it can pick up earlier work by reading the current state from the API server again.

The core components of Kubernetes controllers are: watch cache, event handlers, work queue, and worker routines.
A controller's cache is responsible for monitoring the object type on the API server, notifying the controller of changes to the objects, and maintaining the objects in memory as an indexed store.
To achieve this, a reflector is initiated, which lists and watches the specified object type, emitting delta events added to a queue.
Subsequently, an informer reads events from the queue, updating the store with changed objects.
The store, a flat key-value store with additional indices, enhances the performance of frequently used namespaced queries by controllers or queries with field selectors.
Controllers can utilize caches for multiple object types, and typically, these caches are shared among all controllers within a single binary to optimize CPU and memory usage.
Additionally, caches can be configured to use filtered list and watch requests to reduce overhead for controllers not interested in certain objects. [@studyproject]

![Building blocks of a controller [@samplecontroller]](../assets/controller-components.jpg)

\todo{Replace with custom diagram}

The watch cache (the informer) also dispatch watch events to event handlers registered by controllers.
Event handlers typically filter relevant changes based on the updated object, minimizing unnecessary reconciliation work.
If necessary, event handlers enqueue the object's key (`namespace/name`) to the work queue.
Event handlers may also perform mappings between watched objects and objects the controller is responsible for.
For example, the `Job` controller also watches `Pods` and enqueues the owning `Job` when the corresponding `Pod` finishes its work.
On startup of a controller, it receives `ADDED` events for all existing objects.
To prevent inconsistencies due to watch events missed during a previous downtime, controllers should reconcile all objects on startup. [@studyproject]

The controller's work queue lines up keys of objects requiring reconciliation, decoupling event handling and reconciliation.
The work queue ensures that each object key is processed by a single worker at a time and deduplicates keys added multiple times.
If a key of an object that is currently being reconciled is added to the queue again, it will only be reconciled once the ongoing work has finished.
The queue also implements retries with exponential backoff and rate limiting for failed items.

Worker routines execute the controller's business logic (reconciliation), picking a single key from the work queue at a time.
After picking a key from the queue and marking it as being worked on, workers retrieve the full object from the watch cache and perform reconciliation as required based on the state read from the cache.
Notably, controllers should not be purely event-driven.
Instead, controllers are designed to be edge-triggered but level-driven.
In other words, controllers must always act on the entire observed state of the cluster and not only based on an observed change.
Change notifications are only an optimization for immediately triggering reconciliations when required. [@studyproject; @k8sdesign; @hausenblas2019programming]

Kubernetes controllers can be implemented in any programming language that can interact with the API server via standard HTTP requests.
Many libraries and frameworks are available that implement Kubernetes clients and reusable building blocks for controllers as described above.
The following list includes popular controller libraries that are actively maintained at the time of writing: [@k8sdocs]

- **client-go** is the official Kubernetes client in Go that is also used by Kubernetes core components themselves. It provides great flexibility but requires a deep understand of controller concepts and a lot of boilerplate code. [@clientgo]
- **controller-runtime** offers useful abstractions on top of the core implementations in client-go that makes it easier to implement controllers in Go. This library is the foundation for higher-level generative tooling like Kubebuilder and Operator SDK. [@controllerruntime; @kubebuilderbook; @operatorsdk]
- **Java Operator SDK** implements similar abstractions as controller-runtime for controllers written in Java. [@javaoperatorsdk]
- **kube-rs** offers similar abstractions and tooling as client-go, controller-runtime, and Kubebuilder for controllers written in Rust. [@kubers]

There are also other frameworks available for implementing Kubernetes controllers that deviate conceptually from the typical controller mechanisms described above.
For example:

- **Metacontroller** is a controller implemented in Go that allows specifying controllers declaratively. It runs the common part of custom controllers and calls webhooks that implement the business logic of the custom controller. The webhook servers can be implemented in any programming language. [@metacontroller]
- **shell-operator** is a controller implemented in Go that allows running shell scripts for handling watch events. [@shelloperator]
- **kopf** is a framework for building controllers in python designed around modelling domain knowledge. In contrast to the typical controller structure, it is implemented in an event-driven manner and directly handles watch events instead of enqueueing objects for reconciliation in worker routines. It also stores the state handled by the controller and the state of the controller itself in the API object. [@kopf]

## Scalability of Controllers

- what already makes Kubernetes controllers scalable
  - watch requests
  - no polling, change notifications
  - controllers store all necessary state locally
  - don't contact API server for every reconciliation
  - can immediately react on changes
  - system is event-triggered, level-driven
- define how scalability of controllers can be measured / SLIs
  - sig-scalability definition for Kubernetes scalability: <https://github.com/kubernetes/community/blob/master/sig-scalability/slos/slos.md#how-we-define-scalability>
  - scalability thresholds: <https://github.com/kubernetes/community/blob/master/sig-scalability/configs-and-limits/thresholds.md>
  - sig-scalability tests
  - see <https://github.com/kubernetes/community/blob/master/contributors/devel/README.md#sig-scalability>
  - define SLOs: e.g., p99 queue time

## Leader Election

- why it is needed
  - prevent concurrent reconciliations of a single object
  - reconciliations are not coordinated between multiple instances
  - can lead to conflicting actions
- how it is realized
  - fulfills requirement to prevent concurrent reconciliations of a single object in multiple controllers
  - but on the global level
  - wraps entire process, only executes controller when lock is acquired, terminates when lost
- multiple instances
  - only a single active leader at a time
  - active-passive HA setup [@ahluwalia2006high]
  - fast fail-overs
  - NOT horizontal scaling [@bondi2000characteristics; @jogalekar2000evaluating]

## Scalability Limitations

- core mechanisms of controllers cause the heavy resource usage
  - watch events: CPU for decoding, network transfer
  - watch cache: memory
- no horizontal scalability, no distribution of work, no active-active setups
- due to global leader election, concurrent reconciliations are prevented on a global level
- rate of reconciliations, amount of objects, etc. limited to machine size and network bandwidth
- other perspective: fulfilling SLOs requires scaling controllers vertically when rate of reconciliations, amount of objects, etc. increase
- cannot increase throughput/capacity by adding more instances
- more ideas
  - makes precise vertical right-sizing more difficult, as resource consumption depends on leadership
  - big singleton controller loads only one API server, sharded setup better distributes load across API server instances -> not true for all cases: depends on control plane setup, HTTP2 usage
  - see background in <https://kubevela.io/docs/platform-engineers/system-operation/controller-sharding/>

## Sharding

- essential components?
  - ref <https://github.com/kubernetes/kubernetes/issues/1064#issuecomment-57700433>
  - ref Slicer [@slicer16]
  - ref study project, chapter 2.7 [@studyproject]
- why sharding enables horizontal scalability
