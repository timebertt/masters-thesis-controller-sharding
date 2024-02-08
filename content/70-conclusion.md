# Conclusion and Future Work {#sec:conclusion}

This thesis presented a design and implementation for making Kubernetes controllers horizontally scalable.
It contributes to enabling more Kubernetes and controller-based deployments at even larger scale.
The identified demand in the Kubernetes community for providing scaling options for operators is addressed in a broader scope than in related work.
In contrast to existing concepts and implementations, this thesis provides a reusable design and implementation that can be applied to any Kubernetes controller for removing the scalability limitations imposed by traditional leader election setups.
It proves that well-established sharding mechanisms from distributed databases address essential requirements of building horizontally scalable controller systems.

The key properties of the presented work are:

- Controller instances (shards) announce themselves to the sharder via individual heartbeat resources.
The sharder determines the availability of shards and detects failures based on this membership information to perform automatic fail-overs and rebalancing as soon as the set of available shards changes.
This makes the mechanism suitable for use in highly dynamic environments (req. \ref{req:membership}).
- A consistent hashing algorithm is used for achieving a balanced distribution of API objects for all ring sizes.
The partitioning mechanism takes object ownership into account, so that controlled objects are assigned to the same shard as their owner (req. \ref{req:partitioning}).
- Coordination is achieved by using label-based object assignments.
Assignments are performed by the sharder transparently and automatically using a mutating webhook and controller.
Adding corresponding label selectors in the shards distributes the reconciliation work and watch caches' footprint across shards.
None of the existing API semantics are changed and clients don't need to be aware of the sharded architecture (req. \ref{req:coordination}).
- Concurrent reconciliations in multiple controller instances are prevented by following a dedicated handover protocol.
It ensures that a single instance is responsible for each object at any given time without locking reconciliations on a global level (req. \ref{req:concurrency}).
- The load capacity of the overall system is increased almost linearly with every added controller instance as shown in [@sec:eval-scale-out] (req. \ref{req:scale-out}).
- The core logic of the sharding mechanism is implemented in the dedicated sharder component which can be installed easily into any cluster.
Sharded controllers can be developed in any programming language and only a few aspects need to be realized for enabling controller sharding.
Reusable example implementations of the shard components in Go are presented in [@sec:impl-shard] and can be added for other programming languages as well (req. \ref{req:reusable}).
- The sharding mechanism incurs an overhead in comparison to a singleton controller setup.
However, the overhead is constant and independent of the controller's load as shown in [@sec:eval-comparison] (req. \ref{req:constant}).
- The sharding mechanism relies only on existing Kubernetes API and controller machinery.
It doesn't require managing external components or infrastructure other than controllers, keeping the added complexity low (req. \ref{req:ecosystem}).

To conclude, the systematic evaluation has shown that all identified requirements listed in chapter [-@sec:requirements] are fulfilled by the presented design and implementation.
As the mechanism is simple to apply to existing controllers, it opens opportunities for adoption of the presented work as well as discussion and collaboration in the open-source community.
Because the implementation does not depend on using a specific Kubernetes version, further development is simplified.

As future work on horizontally scalable Kubernetes controllers, the design and implementation from this thesis should be further evaluated through the use in productive controllers.
For this, feedback from the community on the presented development needs to be collected.
If certain use cases cannot adopt the presented work, new requirements shall be collected and explored.
For example, it might become necessary to consider other relationships between objects in the partitioning algorithm, e.g., multiple levels of ownership.

Additionally, the sharding mechanism might be applied to advanced use cases that are not strictly related to horizontal scalability.
For example, distributing reconciliation work across multiple instances opens up the possibility to run different controller versions for a subset of objects.
This in turn could be orchestrated for validating new controller versions in the style of a canary rollout [@kubevela; @adams2015practice; @schermann2018].

If sufficient interest in sharding Kubernetes controllers arises, it could be considered to built the sharding mechanism into the core Kubernetes components.
Users would benefit from a more tightly integrated experience without the need to manage the dedicated sharding components.
Furthermore, object assignments could be performed in an in-tree admission plugin in the API server which eliminates the latency added by network operations for webhook calls.

\todo[inline]{further experiments if not done in evaluation}

- rolling updates
- chaos testing
- autoscaling
