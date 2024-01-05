# Requirements Analysis

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
\subsection*{\requirement\label{req:partitioning}Partitioning}
\subsection*{\requirement\label{req:coordination}Coordination and Object Assignment}
\subsection*{\requirement\label{req:concurrency}Preventing Concurrency}
\subsection*{\requirement\label{req:scale-out}Incremental Scale-Out}

Extended requirements:

\subsection*{\requirement\label{req:generalization}Generic, Reusable implementation}

- controllers can be implemented in any programming language, using any framework
- hence, sharding implementation should also be independent from controller framework and programming language
- some parts will still need to be implemented in every controller framework (e.g., shard leases, selecting the objects)
- core logic should be implemented in reusable way
- necessary logic in every controller/framework should be limited in scope and simple to implement

\subsection*{\requirement\label{req:constant}Constant Overhead}

- sharding always comes with overhead for management, coordination, etc.
- overhead must not increase proportionally to the number of sharded objects
- otherwise, sharding components would face similar scalability limitations, problem not solved
- hence, overhead must be constant, i.e., independent from number of objects
- only then, adding more replicas brings horizontal scalability

\subsection*{\requirement\label{req:controller}Controller Ecosystem}

- don't leave the "controller ecosystem" / API machinery
- e.g., introduce external dependencies/infrastructure like event queue or message broker
- brings additional operational complexity, decreases comprehensibility, makes it harder to reason about
- conflicts with req. 6: external dependencies make it harder to reuse in arbitrary controllers
