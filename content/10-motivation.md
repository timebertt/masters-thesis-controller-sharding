# Motivation

- clarify relevance, need in community
- large-scale Kubernetes-based and controller-based deployments
- core Kubernetes components scale well
- sig-scalability cares about scalability of core components, but core components only
- but external components like custom controllers are not included in scalability considerations/guarantees
- custom controllers need to scale
- custom controllers/operators typically facilitate heavier reconciliation processes compared to core controllers [@kubevela]
- some projects with large-scale deployments have already implemented sharding on their own
- highly specific to individual projects, cannot be reused
- there is no common design or implementation, that can be applied to any arbitrary controller
