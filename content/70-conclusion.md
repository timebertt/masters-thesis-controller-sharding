# Conclusion and Future Work {#sec:conclusion}

This thesis presented a design and implementation for making Kubernetes controllers horizontally scalable.
It enables more Kubernetes and controller-based deployments at an even larger scale.
The identified demand in the Kubernetes community for providing scaling options for operators is addressed in a broader scope than in related work.
In contrast to existing concepts and implementations, this thesis provides a reusable design and implementation that can be applied to any Kubernetes controller to remove the scalability limitations imposed by traditional leader election setups.
It proves that well-established sharding mechanisms from distributed databases address essential requirements of building horizontally scalable controller systems.

The key properties of the presented work are:

- Controller instances (shards) announce themselves to the sharder via individual heartbeat resources.
The sharder determines the availability of shards and detects failures based on this membership information to perform automatic failovers and rebalancing as soon as the set of available shards changes.
This makes the mechanism suitable for highly dynamic environments (\refreq{membership}).
- A consistent hashing algorithm achieves a balanced distribution of API objects for all ring sizes while minimizing movements on shard changes.
The partitioning mechanism considers object ownership so that controlled objects are assigned to the same shard as their owner (\refreq{partitioning}).
- Coordination is achieved by using label-based object assignments.
Assignments are performed by the sharder transparently and automatically using a mutating webhook and controller.
Adding corresponding label selectors in the shards distributes the reconciliation work and watch caches' footprint across shards.
None of the existing API semantics are changed, and clients need not be aware of the sharded architecture (\refreq{coordination}).
- Following a dedicated handover protocol prevents concurrent reconciliations in multiple controller instances.
It ensures that a single instance is responsible for each object at any given time without locking reconciliations on a global level (\refreq{concurrency}).
- The load capacity of the overall system is increased almost linearly with every added controller instance, as shown in [@sec:eval-scale-out] (\refreq{scale-out}).
- The core logic of the sharding mechanism is implemented in the dedicated sharder component, which can be installed easily into any cluster.
Sharded controllers can be developed in any programming language, and only a few aspects need to be realized to enable controller sharding.
Reusable example implementations of the shard components in Go are presented in [@sec:impl-shard] and can be added for other programming languages as well (\refreq{reusable}).
- The sharding mechanism incurs an overhead compared to a singleton controller setup.
However, the overhead is constant and independent of the controller's load, as shown in [@sec:eval-comparison] (\refreq{constant}).
- The sharding mechanism relies only on existing Kubernetes API and controller machinery.
It does not require managing external components or infrastructure other than controllers, keeping the added complexity low (\refreq{ecosystem}).

To conclude, the systematic evaluation has shown that all identified requirements listed in chapter [-@sec:requirements] are fulfilled by the presented design and implementation.
As the mechanism can be easily applied to existing controllers, it opens opportunities for adopting the presented work, discussion, and collaboration in the open-source community.
Further development is simplified because the implementation does not depend on a specific Kubernetes version.

As future work on horizontally scalable Kubernetes controllers, the design and implementation from this thesis should be further evaluated through usage in real-world controllers.
The implementation's performance during rolling updates, automatic scaling, chaos engineering experiments [@chaos2016], and more scenarios should be investigated and enhanced if necessary.
For this, feedback from the community on the presented development needs to be collected.
New requirements shall be collected and explored if certain use cases cannot adopt the presented work.
For example, it might become necessary to consider other relationships between objects in the partitioning algorithm, e.g., multiple ownership levels.

Additionally, the sharding mechanism might be applied to advanced use cases that are not strictly related to horizontal scalability.
For example, distributing reconciliation work across multiple instances allows running different controller versions for a subset of objects.
This, in turn, could be orchestrated for validating new controller versions in the style of a canary rollout [@kubevela; @adams2015practice; @schermann2018].

If sufficient interest in sharding Kubernetes controllers arises, it could be considered to build the sharding mechanism into the core Kubernetes components.
Users would benefit from a more tightly integrated experience without managing the dedicated sharding components.
Furthermore, object assignments could be performed in an in-tree admission plugin in the API server, which eliminates the latency added by network operations for webhook calls.
