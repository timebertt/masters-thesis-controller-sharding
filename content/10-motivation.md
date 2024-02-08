# Motivation

In Kubernetes, users and other clients manage objects in a declarative manner, that is by specifying the desired state instead of issuing imperative commands.
All clients interact with the system through the API server which stores the system's state in etcd.
Controllers continuously watch the cluster state and reconcile changes to the desired state with the actual state and report the observed state.
While etcd and the API server facilitate storage of and interaction with the system's state, controllers are the components that actually implement the APIs' semantics and drive the cluster state.
With this, controller play an essential role in Kubernetes.
[@k8sdocs]

Kubernetes bundles controllers responsible for the built-in API resources in the control plane components.
However, users can extend the Kubernetes API with custom resources and deploy corresponding controllers implementing the new API semantics.
This pattern is commonly referred to as the operator pattern.
It is a powerful mechanism for declaratively managing workload, infrastructure, and more – anything that can be managed in an automated way.
[@operatorhub]

The Kubernetes community has extensively picked up the operator pattern and many open-source projects in various categories are based on it, e.g.:

- database: MariaDB operator [@mariadboperator], PostgreSQL operator [@postgresoperatorzalando; @postgresoperatorcrunchy], K8ssandra [@k8ssandra], MongoDB operator [@mongodboperator]
- streaming & messaging: strimzi-kafka-operator [@strimzi], Koperator [@koperator]
- storage and backup: Rook [@rook], Velero [@velero]
- machine learning: Kubeflow [@kubeflow]
- networking: Knative [@knative], Istio [@istio]
- infrastructure and application management: Crossplane [@crossplane], Argo CD [@argocd], Flux [@flux], KubeVela [@kubevela]
- cluster management: Gardener [@gardenerdocs], Cluster API [@clusterapi]
- cloud infrastructure: Yaook [@yaook], IronCore [@ironcore]

With these projects gaining popularity, large-scale Kubernetes and controller-based deployments are becoming more common.
The Kubernetes community recognizes this demand and ensures that the Kubernetes core components scale well.
For this, the special interest group sig-scalability defines scalability thresholds (e.g., 5,000 nodes) and verifies that Kubernetes performs well within the recommended thresholds by frequently running automated performance and scalability tests.
However, sig-scalability is only responsible for ensuring high scalability of the Kubernetes core components.
[@k8scommunity]

External components like custom controllers or operators are not included in the scalability considerations and guarantees.
Still, the used custom controllers need to be scalable as well for these large-scale deployments to work reliably.
In comparison to Kubernetes core controllers, custom controllers typically facilitate heavier reconciliation processes, which increases the demand for a scalable architecture.
[@kubevela]

Typically, Kubernetes controllers use a leader election mechanism to determine a single active controller instance.
When deploying multiple instances of the same controller, there will only be one active instance at any given time, other instances will be on standby.
This is done to prevent multiple controller instances from performing uncoordinated and conflicting actions on a single object concurrently.
Such an active-passive setup [@ahluwalia2006high] minimizes downtime and facilitates fast fail-overs.
However, it does not scale controller horizontally.
On the contrary, the traditional leader election setup limits the scaling options to the vertical direction.
I.e., controllers can only be scaled by adding more resources to a single instance, but not by adding more instances, as reconciliation work cannot be distributed across multiple instances.
This restriction imposes scalability limitations for Kubernetes controllers.
E.g., the maximum number of objects and the maximum object churn rate, is limited by the machine size that the active controller runs on and the network bandwidth it can use.
[@bondi2000characteristics]

To address the demand for facilitating large-scale deployments, several of the mentioned open-source projects feature sharding mechanisms that distribute reconciliation work across multiple controller instances [@argocddocs; @kubevela].
However, the mechanisms are highly specific to the individual projects and cannot be reused in other controllers.
Many of the sharding implementations are not fully matured and face similar challenges, e.g., the mechanism requires clients to be sharding-aware and manually assign API objects to shards, or the implementation doesn't facilitate automatic fail-over and rebalancing [@flux].
Furthermore, sharding mechanisms are considered for achieving a higher scalability in many other projects as well[^sharding-issues].
The problem is that there is no common design or implementation that can be applied to arbitrary controllers for scaling them horizontally.
There is no reusable implementation that the entire controller ecosystem can benefit from.

[^sharding-issues]: Istio: <https://github.com/istio/istio/issues/22208>, \newline
Velero: <https://github.com/vmware-tanzu/velero/issues/487>, \newline
controller-runtime: <https://github.com/kubernetes-sigs/controller-runtime/issues/2576>, \newline
Operator SDK: <https://github.com/operator-framework/operator-sdk/issues/1540>, \newline
Metacontroller: <https://github.com/GoogleCloudPlatform/metacontroller/issues/190>

This thesis builds on a previous study project [@studyproject] and presents a design and implementation for making Kubernetes controllers horizontally scalable.
The design applies proven mechanisms from the field of distributed databases to the problem of Kubernetes controller to overcome the limitation of having only a single active controller instance.
By distributing the responsibility for API objects across a ring of controller instances, concurrent reconciliations are not prevented on a global level but on a per-object level.
<!-- Membership and failure detection mechanisms are employed to facilitate automatic fail-overs and rebalancing.
The sharding mechanism is transparent to clients which do not need to be aware of the sharded architecture as no existing API semantics are changed. -->
A reusable implementation of the design is presented, that can be applied to any Kubernetes controller.
For this, the sharding components can be installed into any Kubernetes cluster.
Existing controllers only need to be modified slightly to comply with the sharding mechanism.

First, this thesis describes all relevant fundamentals in detail (chapter [-@sec:fundamentals]).
This includes the most important aspects of Kubernetes API and controller machinery ([@sec:apimachinery; @sec:controller-machinery]) as well as leader election principles ([@sec:leader-election]).
Next, a general definition for the scalability of a distributed system as defined in common literature is presented and how the scalability of Kubernetes is defined and measured ([@sec:kubernetes-scalability]).
[@Sec:controller-scalability] outlines how the scale and performance of a controller setup can be measured.
Based on this, [@sec:scalability-limitations] analyzes the current scalability limitations of Kubernetes controllers in detail.

Afterward, this thesis examines existing efforts related to sharding in Kubernetes controllers (chapter [-@sec:related-work]).
Primarily, it assesses the strengths and drawbacks of the design presented in the previous study project ([@sec:related-study-project]).
Derived from this, chapter [-@sec:requirements] lists precise requirements that need to be fulfilled for removing the identified scalability limitations and for making Kubernetes controller horizontally scalable.
In accordance with this, an evolved design is developed step by step in chapter [-@sec:design].
It is based on the design presented in the study project but addresses all additional requirements from the previous chapter.

The implementation of the presented design is described in chapter [-@sec:implementation].
In addition to explaining how the external sharding components are implemented ([@sec:impl-clusterring; @sec:impl-sharder]), the chapter gives instructions for implementing the shard components in existing controllers ([@sec:impl-shard]).
An example setup is presented that combines all implemented components to a fully functioning sharded controller setup ([@sec:impl-setup]).
Next, the implementation is evaluated in systematic load test experiments (chapter [-@sec:evaluation]).
After precisely describing the experiment setup ([@sec:experiment-setup]) and how measurements are performed ([@sec:measurements]), different experiment scenarios are executed ([@sec:experiments]), and their results are discussed ([@sec:discussion]).
Finally, a conclusion of the presented work is drawn and future work is layed out (chapter [-@sec:conclusion]).
