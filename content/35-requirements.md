# Requirements Analysis {#sec:requirements}

In this thesis, sharding mechanisms leveraged by distributed databases are applied to Kubernetes controllers to resolve the described limitations.
As described in [@sec:kubernetes-scalability], the core property of a scalable system is that its load capacity increases when resources are added to the system.
When considering horizontal scalability, adding instances to the system must result in an increased load capacity of the overall system.

To make Kubernetes controllers horizontally scalability, the limitations described in [@sec:scalability-limitations] need to be resolved.
At the core, the restriction to have only a single active instance at any given time must be removed.
In other words, the traditional leader election setup that elects a leader on the global level must be replaced.
Only if reconciliation work can be distributed across multiple controller instances, the system can be scaled out horizontally.
For this, another mechanism is needed to prevent concurrent reconciliations that doesn't include global locking.

This thesis builds on the requirements posted in the previous study project (req. 1–5) [@studyproject].
While the basic requirements are already fulfilled by the presented work, the evaluation revealed significant drawbacks and limitations that need to be resolved for ultimately making controllers horizontally scalable ([@sec:related-study-project]).
The set of requirements is extended in this thesis to address the identified limitations accordingly.

\subsection*{\requirement\label{req:membership}Membership and Failure Detection}

As the foundation, the system needs to populate information about the set of controller instances.
In order to distribute object ownership across instances, there must be a mechanism for discovering available members of the sharded setup (controller ring).
Instance failures need to be detected for automatically restoring the system's functionality.

As controllers are deployed in highly-dynamic environments, the sharding mechanism must expect that instances are restarted, added, or removed frequently and can fail at any time.
Furthermore, instances will typically be replaced in quick succession during rolling updates.
Hence, voluntary disruptions should be handled specifically to achieve fast rebalancing during scale-down and rolling updates.
[@studyproject]

\subsection*{\requirement\label{req:partitioning}Partitioning}

The sharding mechanism must provide a partitioning algorithm for determining ownership of a given object based on information about the set of available controller instances.
It must map every sharded API object to exactly one instance.
Additionally, the partitioning algorithm needs to provide a balanced distribution even with a small number of instances (e.g., less than 5).

A partition key is needed that can be extracted from all API resources.
As controllers commonly watch controlled objects to trigger reconciliation of the owning object on relevant changes to owned objects, the partitioning algorithm must support assigning related objects to the same instance.
For this, all controlled objects must map to the same partition key as their owners.
[@studyproject]

\subsection*{\requirement\label{req:coordination}Coordination and Object Assignment}

The sharding mechanism must provide some form of coordination between individual controller instances and assign API objects to the instances based on the partitioning results.
Individual controller instances need to know which objects are assigned to them in order to perform the necessary reconciliations.
However, individual instances don't need to be aware of all object assignments.
The object assignment needs to be transparent and must not change any existing API semantics.

As described in [@sec:controller-machinery], the resource consumption of Kubernetes controllers significantly depends on the controllers' caches and the underlying watch connections.
The sharding mechanism can only make controllers horizontally scalable if the instances' caches and watch connections are filtered to only transport and store the API objects that are assigned to the respective instances.
Object assignments must be stored persistently so that instances can retrieve the assignment information after restarts.

Furthermore, there must not be a single point of failure or bottleneck for reconciliations.
This means, the sharding mechanism must not add additional points of failure on the critical path of API requests during reconciliations themselves, which would limit the mechanism's scalability again.
During normal operations, reconciliations should not be blocked for a longer period.
[@studyproject]

\subsection*{\requirement\label{req:concurrency}Preventing Concurrency}

Even if object ownership is distributed across multiple controller instances, the controllers must not perform concurrent reconciliations of a single object in different instances.
Only a single instance is allowed to perform mutations on a given object at any given time.
The sharding mechanism must assign all API objects to a single instance and ensure that only a single instance performs reconciliations at any given time.
[@studyproject]

\subsection*{\requirement\label{req:scale-out}Incremental Scale-Out}

The sharding mechanism must provide incremental scale-out properties.
For this, the load capacity of the system must increase almost linearly with the number of added controller instances.
[@studyproject]

\subsection*{\requirement\label{req:reusable}Reusable Implementation}

As controllers can be implemented in arbitrary programming languages and use different frameworks ([@sec:controller-machinery]), the sharding mechanism must be independent of the controller framework and programming language.
The design should allow a generic implementation so that the sharding mechanism can be applied to any controller.

Note that it is not possible to design and implement every aspect of the sharding mechanism in a generic and reusable way.
Where the mechanism requires compliance of the controller instances, e.g., for announcing themselves to the system, some parts need to be reimplemented in every programming language and framework.
However, the core logic of the sharding mechanism should be implemented externally in a reusable way.
The necessary logic that needs to be reimplemented in the controllers themselves should be limited in scope and simple to implement.

\subsection*{\requirement\label{req:constant}Constant Overhead}

A sharding mechanism always incurs a certain overhead for management, coordination, etc. in comparison to a non-distributed setup.
However, the inherent overhead of the sharding mechanism must not increase proportionally with the controller's load.
Otherwise, the sharding components would face the original scalability limitations themselves ([@sec:related-study-project]).
I.e., the sharding overhead must be almost constant and independent of the number of objects and the object churn rate.
Only if this requirement is fulfilled, adding more controller instances achieves horizontal scalability.

\subsection*{\requirement\label{req:ecosystem}Only Use API and Controller Machinery}

The sharding mechanism should not leave the ecosystem of API and controller machinery.
It should only use the mechanisms provided by the Kubernetes API ([@sec:apimachinery]) and match the core concepts of Kubernetes controllers ([@sec:controller-machinery]).

For example, the sharding mechanism must not require external components or infrastructure like an event queue or message broker.
Such dependencies add to the operational complexity of the system and decreases comprehensibility.
This hinders adoption of the mechanism because it makes it harder reuse in arbitrary controllers.
