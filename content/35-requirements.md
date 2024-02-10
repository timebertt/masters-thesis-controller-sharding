# Requirements Analysis {#sec:requirements}

This thesis applies sharding mechanisms leveraged by distributed databases to Kubernetes controllers to resolve the described limitations.
As described in [@sec:kubernetes-scalability], the core property of a scalable system is that its load capacity increases when resources are added to the system.
When considering horizontal scalability, adding instances to the system must result in an increased load capacity of the overall system.

To make Kubernetes controllers horizontally scalable, the limitations described in [@sec:scalability-limitations] must be resolved.
At the core, the restriction to have only a single active instance at any given time must be removed.
In other words, the traditional leader election setup that elects a global leader must be replaced.
If reconciliation work can be distributed across multiple controller instances, the system can be scaled horizontally.
Another mechanism is needed to prevent concurrent reconciliations that does not include global locking.

This thesis builds on the requirements posted in the previous study project (req. 1–5) [@studyproject].
While the presented work already fulfills the basic requirements, the evaluation revealed significant drawbacks and limitations that this thesis needs to resolve to make controllers horizontally scalable ([@sec:related-study-project]).
The set of requirements is extended in this thesis to address the identified limitations accordingly.

\subsection*{\req{membership}Membership and Failure Detection}

As the foundation, the sharding mechanism needs to populate information about the set of controller instances.
In order to distribute object ownership across instances, there must be a mechanism for discovering available members of the sharded setup (controller ring).
Instance failures need to be detected to restore the system's functionality automatically.

As controllers are deployed in highly dynamic environments, the sharding mechanism must expect that instances are restarted, added, or removed frequently and can fail at any time.
Furthermore, instances will typically be replaced in quick succession during rolling updates.
Hence, the sharding mechanism should handle voluntary disruptions explicitly to achieve fast rebalancing during scale-down and rolling updates.
[@studyproject]

\subsection*{\req{partitioning}Partitioning}

The sharding mechanism must provide a partitioning algorithm for determining ownership of a given object based on information about the set of available controller instances.
It must map every sharded API object to exactly one instance.
Additionally, the partitioning algorithm must provide a balanced distribution even with a small number of instances (e.g., less than 5).

A partition key is needed that can be extracted from all API resources.
As controllers commonly watch controlled objects to trigger reconciliation of the owning object on relevant changes to owned objects, the partitioning algorithm must support assigning related objects to the same instance.
I.e., all controlled objects must map to the same partition key as their owners.
[@studyproject]

\subsection*{\req{coordination}Coordination and Object Assignment}

Based on the partitioning results, the sharding mechanism must provide some form of coordination between individual controller instances and assign API objects to the instances.
Individual controller instances need to know which objects are assigned to them to perform the necessary reconciliations.
However, individual instances do not need to be aware of all object assignments.
The object assignment must be transparent and not change any existing API semantics.

As described in [@sec:controller-machinery], the resource consumption of Kubernetes controllers significantly depends on the controllers' caches and the underlying watch connections.
The sharding mechanism can only make controllers horizontally scalable if the instances' caches and watch connections are filtered to transport and store only the API objects assigned to the respective instances.
Object assignments must be stored so that instances can retrieve the assignment information after restarts.

Furthermore, there must not be a single point of failure or bottleneck for reconciliations.
Essentially, the sharding mechanism must not add additional points of failure on the critical path of API requests during reconciliations, which would limit the mechanism's scalability again.
During normal operations, reconciliations should not be blocked for a longer period.
[@studyproject]

\subsection*{\req{concurrency}Preventing Concurrency}

Even if object ownership is distributed across multiple controller instances, the controllers must not perform concurrent reconciliations of a single object in different instances.
Only a single instance may perform mutations on a given object at any time.
The sharding mechanism must assign all API objects to a single instance and ensure that only one instance performs reconciliations at any given time.
[@studyproject]

\subsection*{\req{scale-out}Incremental Scale-Out}

The sharding mechanism must provide incremental scale-out properties.
For this, the system's load capacity must increase almost linearly with the number of added controller instances.
[@studyproject]

\subsection*{\req{reusable}Reusable Implementation}

As controllers are implemented in arbitrary programming languages and use different frameworks ([@sec:controller-machinery]), the sharding mechanism must be independent of the controller framework and programming language.
The design should allow a generic implementation to apply the sharding mechanism to any controller.

Note that it is impossible to implement every aspect of the sharding mechanism in a generic and reusable way.
Where the mechanism requires compliance of the controller instances, e.g., for announcing themselves to the system, some parts must be reimplemented in every programming language and framework.
However, the core logic of the sharding mechanism should be implemented externally in a reusable way.
The necessary logic that needs to be reimplemented in the controllers themselves should be limited in scope and simple to implement.

\subsection*{\req{constant}Constant Overhead}

A sharding mechanism always incurs an unavoidable overhead for tasks like instance management and coordination compared to a non-distributed setup.
However, the inherent overhead of the sharding mechanism must not increase proportionally with the controller's load.
Otherwise, the sharding components would face the original scalability limitations ([@sec:related-study-project]).
I.e., the sharding overhead must be almost constant and independent of the number of objects and the object churn rate.
Adding more controller instances achieves horizontal scalability only if the design fulfills this requirement.

\subsection*{\req{ecosystem}Only Use API and Controller Machinery}

The sharding mechanism should stay in the ecosystem of API and controller machinery.
It should only use the mechanisms provided by the Kubernetes API ([@sec:apimachinery]) and match the core concepts of Kubernetes controllers ([@sec:controller-machinery]).

For example, the sharding mechanism must not require external components or infrastructure like an event queue or message broker.
Such dependencies add to the operational complexity of the system and decrease comprehensibility.
This hinders the adoption of the mechanism because it makes it harder to reuse in arbitrary controllers.
