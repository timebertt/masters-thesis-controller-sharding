# Horizontally Scalable Kubernetes Controllers

Read the full paper [here](https://github.com/timebertt/masters-thesis-controller-sharding/releases/tag/v1.0)!

## About

This is my master's thesis for my master's studies in Computer Science at the [DHBW Center for Advanced Studies](https://www.cas.dhbw.de/) (CAS).

You can find the implementation that was done as part of this thesis in the [kubernetes-controller-sharding](https://github.com/timebertt/kubernetes-controller-sharding) repository.

You can find the previous thesis (study project) on this topic in the [thesis-controller-sharding](https://github.com/timebertt/thesis-controller-sharding) repository.

## Abstract

In Kubernetes, custom controllers are pivotal in managing diverse workloads and infrastructure through the operator pattern.
Large-scale Kubernetes and controller-based deployments have become commonplace with the proliferation of open-source projects leveraging this pattern for building applications, services, and platforms.
While the Kubernetes core components are guaranteed to scale efficiently up to certain thresholds, those guarantees neglect the scalability of external components like custom controllers.

Typically, Kubernetes controllers prevent uncoordinated and conflicting actions of concurrent reconciliations by using a leader election mechanism to determine a single active controller instance.
This mechanism limits scalability options for controllers to vertical scaling because reconciliation work cannot be distributed across multiple controller instances.
While some projects have introduced sharding mechanisms to address the need for horizontal scalability, these solutions are often project-specific and lack reusability.

This thesis bridges this gap by proposing an approach to achieve horizontal scalability in Kubernetes controllers based on existing API and controller machinery.
The design builds upon proven mechanisms from distributed databases to distribute the responsibility for API objects across a ring of controller instances, removing the scalability limitations inherent in traditional leader election setups.
Key features include dynamic membership and failure detection for automatic failovers and rebalancing, a consistent hashing algorithm for ensuring a balanced distribution of API objects, label-based coordination for transparent object assignments without client interaction, and a dedicated handover protocol for preventing concurrent reconciliations.

This thesis presents a reusable implementation that allows for easy integration of the mechanism into arbitrary controllers including built-in controllers, opening the potential for adoption and collaboration within the open-source community.
Systematic evaluation using load test experiments demonstrates that all identified requirements are met.
The mechanism showcases minimal overhead compared to singleton controller setups and an almost linear increase of the controller's load capacity with every added controller instance.
This work contributes to advancing the scalability and efficiency of Kubernetes controllers, offering promising prospects for the future development and usage of Kubernetes and controller-based applications and platforms.
