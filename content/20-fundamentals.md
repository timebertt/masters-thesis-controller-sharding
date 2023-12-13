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
Hence, they are described in more detail.

- watch requests
- label selectors
- optimistic locking
- admission webhooks
- ownerReferences and garbage collection

## Controller Machinery

- controllers drive the actual state to match the desired state (reconciliations)
- asynchronous, eventually consistent [@brewer2000towards; @vogels2008eventually]
- watch objects to get notified about changes
- can reconcile any API resources: built-in and extended
- controller building blocks?
- important aspects
  - queue deduplicates keys, prevents concurrent reconciliations in multiple worker routines
  - watch controlled & owned objects
  - need to enqueue all objects on startup (might have missed relevant events)
- can be implemented in any programming language (<https://kubernetes.io/docs/concepts/extend-kubernetes/operator/#writing-operator>)
- only list actively maintained projects
- frameworks/libraries implementing these mechanisms:
  - client-go (Go): <https://github.com/kubernetes/client-go>
  - controller-runtime (Go): <https://github.com/kubernetes-sigs/controller-runtime>
  - Java Operator SDK: <https://javaoperatorsdk.io/>
  - kube-rs (Rust): <https://kube.rs/>
  - KubeOps (.NET): <https://buehler.github.io/dotnet-operator-sdk/>
- other frameworks implementing conceptually different mechanisms:
  - Metacontroller: <https://metacontroller.github.io/metacontroller>
    - core controller implemented in Go
    - calls webhooks for business logic (can be implemented in any language)
  - shell-operator: <https://flant.github.io/shell-operator/>
    - core controller implemented in Go
    - calls scripts for business logic
  - kopf (Python): <https://kopf.readthedocs.io/>
    - designed around modelling domain knowledge
    - event-driven: primarily handles watch events
    - stores handled state in annotation
    - stores controller state in status/annotation
    - leader election via `{Cluster,}KopfPeering` custom resources

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
