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

The Kubernetes community has extensively picked up the operator pattern and many popular open-source projects in various categories are based on it, e.g.:

- database: MariaDB operator [@mariadboperator], PostgreSQL operator [@postgresoperatorzalando; @postgresoperatorcrunchy], K8ssandra [@k8ssandra], MongoDB operator [@mongodboperator]
- streaming & messaging: strimzi-kafka-operator [@strimzi], Koperator [@koperator]
- storage and backup: Rook [@rook], Velero [@velero]
- machine learning: Kubeflow [@kubeflow]
- networking: Knative [@knative], Istio [@istio]
- infrastructure and application management: Crossplane [@crossplane], Argo CD [@argocd], Flux [@flux], KubeVela [@kubevela]
- cluster management: Gardener [@gardenerdocs], Cluster API [@clusterapi]
- cloud infrastructure: Yaook [@yaook]

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

[^sharding-issues]: <https://github.com/istio/istio/issues/22208>, <https://github.com/vmware-tanzu/velero/issues/487>, <https://github.com/kubernetes-sigs/controller-runtime/issues/2576>, <https://github.com/operator-framework/operator-sdk/issues/1540>, <https://github.com/GoogleCloudPlatform/metacontroller/issues/190>

This thesis builds on a previous study project [@studyproject] and presents a reusable design and implementation for making Kubernetes controllers horizontally scalable.
