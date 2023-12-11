# Motivation

- clarify relevance, need in community
  - issues in many projects asking for sharding
    - istio: <https://github.com/istio/istio/issues/22208>
    - velero: <https://github.com/vmware-tanzu/velero/issues/487>
    - controller-runtime: <https://github.com/kubernetes-sigs/controller-runtime/issues/2576>
    - Operator SDK: <https://github.com/operator-framework/operator-sdk/issues/1540>
    - Metacontroller: <https://github.com/GoogleCloudPlatform/metacontroller/issues/190>
- large-scale Kubernetes-based and controller-based deployments
- core Kubernetes components scale well
- sig-scalability cares about scalability of core components, but core components only
- but external components like custom controllers are not included in scalability considerations/guarantees
- custom controllers need to scale
- custom controllers/operators typically facilitate heavier reconciliation processes compared to core controllers [@kubevela]
- some projects with large-scale deployments have already implemented sharding on their own
- highly specific to individual projects, cannot be reused
- there is no common design or implementation, that can be applied to any arbitrary controller
