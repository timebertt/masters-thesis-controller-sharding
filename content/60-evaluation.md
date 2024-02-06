# Evaluation {#sec:evaluation}

This chapter evaluates the presented design (chapter [-@sec:design]) and implementation (chapter [-@sec:implementation]) by conducting systematic load test experiments.
The components are observed by a monitoring setup to perform measurements that are eventually discussed.

## Experiment Setup

The development and testing setup described in [@sec:impl-setup] serves as a basis for the experiment setup used for evaluation.
Most notably, the evaluation uses the sharding system components and monitoring setup based on kube-prometheus [@prometheusoperatordocs].
In addition, it also deploys the webhosting-operator as an example sharded controller.
The webhosting-operator was developed in the context of the previous study project and supports enabling the sharding mechanism based on the internal sharder design ([@sec:related-study-project]) [@studyproject].
To evaluate the new external sharder mechanism presented in this thesis, the webhosting-operator is adapted to comply with the contract for `ClusterRings` similar to [@sec:impl-shard].
With this, the webhosting-operator can be deployed in three different configurations: singleton (sharding disabled), internal sharder (design from study project), external sharder (design from this thesis).
This allows comparing all three setups using load test experiments.

As described in [@sec:controller-scalability], the scale of controller setups can be described in two dimensions: the number of API objects and the churn rate of API objects.
The webhosting-operator's main resource are `Website` objects, which control `Deployment`, `ConfigMap`, `Service`, and `Ingress` objects.
Accordingly, increasing the load on the webhosting-operator involves creating many `Website` objects and triggering `Website` reconciliations.
Additionally, changing the `Theme` referenced by a `Website`, also triggers a `Website` reconciliation.
Hence, the object churn rate of the webhosting-operator also depends on the churn rate of the referenced `Themes`.

Load test experiments are conducted using new and refined scenarios for the experiment tool that was developed as part of the study project [@studyproject].
The experiment scenarios continuously create, update, and delete `Website` objects to trigger reconciliations.
With this, it can be used for increasing the scale of the example operator setup according to the described load dimensions.
During load tests, the webservers configured by `Website` objects are not actually run.
Running thousands of individual webservers would require an immense amount of compute resources although it is not required by the managing controller itself.
Hence, the website's `Deployments` are configured with `spec.replicas=0`.
With this, the usual reconciliation flow of `Websites` is not changed, as the controller still waits for the `Available` condition of `Deployments` to be true, but no compute power is required for actually running the webservers.

The experiments are performed on a cluster managed by a custom Gardener [@gardenerdocs] installation on STACKIT [@stackitdocs].
The evaluation cluster features multiple worker pools as shown in [@tbl:worker-pools] for better isolation of the observed components (`sharding` worker pool), the observing components (`system` worker pool), and the experiment tool generating the load (`experiment` worker pool).
All worker pools run virtual machines of the `g1a.8d` flavor[^flavors], which has 8 vCPUs and 32 GB memory.
A flavor without CPU overcommitment is chosen for more stability and better reproducibility of the experiments, because they cannot be affected by steal time [@stackitdocs].

| worker pool | flavor | hosted components | count |
|-----------------|--------|------------------------------------------|--------|
| system (default) | g1a.8d | cluster system, monitoring   | 2   |
| sharding         | g1a.8d | sharder, webhosting-operator | 2–3 |
| experiment       | g1a.8d | experiment tool              | 1   |

: Worker pools of the evaluation cluster {#tbl:worker-pools}

[^flavors]: <https://docs.stackit.cloud/stackit/en/virtual-machine-flavors-75137231.html>

For Kubernetes clusters managed by Gardener ("shoot" clusters), the control plane components are hosted in another cluster ("seed" cluster) [@gardenerdocs].
The seed cluster that hosts the control plane components of the evaluation cluster is modified to run machine flavors without CPU overcommitment (`c1a.8d`).
Additionally, the main control plane components (etcd, kube-apiserver, kube-controller-manager) of the evaluation cluster run on dedicated worker pool using the `s1a.16d` flavor.
The control plane runs a single etcd instance, 4 kube-apiserver instances, and a single kube-controller-manager instance.
To ensure a stable and reproducible evaluation environment, autoscaling of the main control plane components is disabled.
Instead, all three components are assigned static resource requests and limits: etcd and kube-apiserver use 12 CPUs and 12 GiB memory, kube-controller-manager uses 6 CPU and 6 GiB memory.
Requests and limits are set to the same values to guarantee the requested resources [@k8sdocs].
As the `Deployment` and `ReplicaSet` controllers need to perform a high rate of reconciliations when generating load for the webhosting-operator, the client-side rate limits of kube-controller-manager are increased to 2000 requests per second with bursts of up to 2200 requests per second.
Both the `Deployment` and `ReplicaSet` controllers are configured to run 50 concurrent workers.

Similar to the control plane components, the observed components (sharder and webhosting-operator) are configured with static and equal resource requests and limits.
The sharder `Deployment` is configured to run 2 replicas for a higher availability of the sharder webhook.
Both replicas are guaranteed 200m CPUs and 128 MiB memory.
The active sharder instance runs 5 concurrent workers for the `clusterring`, `shardlease`, and `sharder` controllers respectively.
Depending on the experiment scenario and controller setup, different numbers of replicas of the webhosting-operator with different number of concurrent workers are deployed.
Each instance is guaranteed 2 CPUs and 1 GiB memory.

In addition to configuring the container resource limits, the Go runtime's `GOMAXPROCS` setting in the control plane components and observed components is configured.
The `GOMAXPROCS` setting configures how many operating system threads the Go runtime spawns for executing user-level goroutines [@godocs].
By default, the setting equals the number of logical CPU cores of the machine, which is the total number of CPU cores of the hosting Node in Kubernetes Pods.
Accordingly, the Go runtime spawns more operating system threads than the number of cores allocated via cgroup limits [@tsoukalos2021mastering].
Hence, when too many goroutines are busy, the application tries to consume more CPU cycles than the kernel scheduler allows, which results in CPU throttling.
As the Go scheduler is not aware of the kernel scheduler and vice-versa, the Go scheduler might evict running goroutines after being throttled by the kernel, leading to starvation of individual goroutines.
This results in high tail latencies for operations handled by goroutines.
Also, it increases the ratio of CPU cycles consumed by the scheduler to CPU cycles available for goroutines, which in turn decreases the throughput of the application.
[@holland2023tuning; @automaxprocs]

To prevent these effects from falsifying performance measurements of this evaluation, `GOMAXPROCS` is configured to match the CPU quota allocated for each container of the control plane and observed components.
For the control plane components, `GOMAXPROCS` is configured via environment variables.
In the sharder, webhosting-operator, and experiment tool, the automaxprocs library is used to automatically configure the setting based on the container's CPU quota (`max(1, floor(cpuquota))`) [@automaxprocs].

When Kubernetes clients using client-go connect to the API server, they perform a TLS handshake with one of the API server instances.
Afterward, all requests of the client are sent over the established TLS connection via multiple HTTP2 streams.
With this, all API requests of a client are sent to a single API server instance[^http2issue].
In high load situations, clients that perform a high rate of API requests like kube-controller-manager or the experiment tool, can quickly overload the API server instance they connected to.
To prevent this problem from limiting load tests of this evaluation, all components are configured to disable HTTP2.
With this, HTTP requests are sent over a pool of multiple layer 4 connections (TLS) instead of a single layer 4 connection with multiple HTTP2 streams.
This doesn't ensure an equal distribution of load across API server instances, but prevents overloading individual instances during conducted experiments.

[^http2issue]: <https://github.com/gardener/gardener/issues/8810>

To ensure a clean evaluation environment, the experiment tool restarts all observed components and waits for them to be healthy before starting the load tests.
For the measurements to be meaningful, all cluster component and all controllers are monitoring during the experiments to ensure that the system is not limited due to CPU throttling, etcd disk performance, server-side or controller-side concurrency limits, or client-side rate limits.

## Measurements

To determine the controller's performance, several measurements are taken during load test experiments.
For this, the monitoring setup's Prometheus instance [@prometheusdocs] is used to collect and store metrics from the controller instances themselves, but also from kubelet's cadvisor endpoint [@k8sdocs; @cadvisor] and other exporters like kube-state-metrics [@kubestatemetrics].
After performing the load tests, the relevant metrics are retrieved from the Prometheus HTTP API using the measure tool [@studyproject] for later analysis and visualization.
The tool fetches raw time series data and stores the result matrices in CSV-formatted files.
Additionally, the tool is extended to support instant queries for calculating percentiles over a configured time range.
This is used to verify that configured SLOs are met during a load test experiment.

For the measurements to be meaningful, the Kubernetes cluster SLOs themselves as described in [@sec:kubernetes-scalability] must be satisfied.
I.e., it must be ensured that the cluster itself where the controllers are running on is performing well.
While the latency of API requests (SLI 1 and 2) are relevant for the experiment setup, pod startup latency (SLI 3) is irrelevant as the load tests don't trigger pod startups.

```yaml
queries:
- name: latency-mutating # SLO 1
  type: instant
  slo: 1
  query: |
    histogram_quantile(0.99, sum by (resource, verb, le) (rate(
      apiserver_request_duration_seconds_bucket{
        cluster="shoot--timebertt--sharding",
        verb!~"GET|LIST|WATCH",
        subresource!~"log|exec|portforward|attach|proxy"
      }[$__range]
    ))) > 0
- name: latency-read-resource # SLO 2 - resource scope
  type: instant
  slo: 1
  query: |
    histogram_quantile(0.99, sum by (resource, scope, le) (rate(
      apiserver_request_duration_seconds_bucket{
        cluster="shoot--timebertt--sharding",
        verb=~"GET|LIST", scope="resource",
        subresource!~"log|exec|portforward|attach|proxy"
      }[$__range]
    ))) > 0
- name: latency-read-namespace-cluster # SLO 2 - namespace and cluster scope
  type: instant
  slo: 30
  query: |
    histogram_quantile(0.99, sum by (resource, scope, le) (rate(
      apiserver_request_duration_seconds_bucket{
        cluster="shoot--timebertt--sharding",
        verb=~"GET|LIST", scope=~"namespace|cluster",
        subresource!~"log|exec|portforward|attach|proxy"
      }[$__range]
    ))) > 0
```

: Queries for verifying control plane SLOs {#lst:k8s-slo-queries}

In the context of this evaluation, both API request latency SLIs are defined even stricter.
The official SLIs exclude custom resources but they are explicitly included in measurements of this evaluation.
This is done because the webhosting-operator's main resources are extended resources.
Furthermore, the latency for mutating API calls is measured including webhook call latency, as the sharder webhook is an integral element of the evaluated sharding design.
For considering the setup as performing well, the request latency increase caused by the sharder webhook should be reasonably low.
Without taking these aspects into account, the measurements would not be meaningful for the concrete experiment setup.
Including extended resources and webhook call latency in the SLIs will yield worse performance measurements.
Hence, the cluster is considered to perform well if the stricter measurements still satisfy the official SLOs.

The central store for control plane metrics is consulted for verifying that both SLOs are met using the queries shown in [@lst:k8s-slo-queries].
The queries are similar to the queries used in Kubernetes performance tests[^perftests-queries] for the same purpose [@perftests].
The `$__range` placeholder is substituted by the corresponding experiment's duration.
I.e., SLIs are not measured per cluster-day but only over the duration of the load test.

[^perftests-queries]: <https://github.com/kubernetes/perf-tests/blob/release-1.29/clusterloader2/pkg/measurement/common/slos/api_responsiveness_prometheus.go>

Next, the load on the evaluated controller setup needs to be recorded during experiments to determine the load capacity of a setup using a given resource configuration and to allow comparing results of different scenarios.
For this, both load dimensions of controllers defined in [@sec:controller-scalability] need to be measured for the tested controller.
Applied to the webhosting-opperator, the number of objects that are watched and reconciled by the controller (dimension 1) is the number of `Website` objects in the cluster.
This can be measured using the `kube_website_info` metric exposed for every `Website` object by the operator.
On the other hand, the churn rate of API objects (dimension 2) for the webhosting-operator is the rate at which `Website` objects are created, updated, and deleted.
In experiments, `Website` reconciliations are triggered by mutating the `spec.theme` field.
The experiment tool is based on controller-runtime and individual actions in scenarios are performed by reconciliations of different controllers.
Hence, this load dimension can be measured using the reconciliation-related metrics exposed by controller-runtime.
[@Lst:load-queries] shows the precise queries for measuring the described load dimensions during experiments.

```yaml
queries:
- name: website-count # dimension 1
  query: |
    sum(kube_website_info)
- name: website-churn # dimension 2
  query: |
    sum(rate(
      controller_runtime_reconcile_total{
        job="experiment", result!="error",
        controller=~"website-(generator|deleter|mutator)"
      }[1m]
    )) by (controller)
```

: Queries for measuring controller load {#lst:load-queries}

To ensure the controller setup is performing well under the generated load, the SLIs for controllers defined in [@sec:controller-scalability] are measured as well.
The time that object keys are enqueued for reconciliation (SLI 1) is directly derived from the queue-related metrics exposed by controller-runtime.
For SLI 2, the time until changes to the desired state of `Websites` are reconciled and ready is measured by the experiment tool.

An object's generation is automatically increased by the API server for its creation and for every specification change.
For all object generations, the tool stores the time when it triggered the change.
It then waits for a watch event that updates the `status.observedGeneration` field accordingly and for the `status.phase` field to be `Ready`.
The tool stores the time when the respective watch event was received and asynchronously records the time it took the controller to observe the new generation and for the `Website` to become ready in a histogram metric (`experiment_website_reconciliation_duration_seconds`).
To verify that the tool's measurements are not falsified by the time it takes to receive the watch event, the `Website` controller records the timestamp when a new generation of a `Website` got ready in the `status.lastTransitionTime` field.
The tool records the duration between the `lastTransitionTime` and the time when the watch event was received and processed by the event handler in another histogram metric.
The experiment's measurements are only meaningful if the watch event latency is reasonably low.

In this scenario, the tool acts as a client of the `Website` API, i.e., an observer of the system's user experience.
As the reconciliation latency observed by the client includes the time until the corresponding watch event is received, it is important to include this time in the measurements for reflecting the actual user experience.
For secondary reconciliation triggers, e.g., changing the referenced `Theme`, its difficult to measure how long it takes the controller to observe the external change and reconcile `Websites` accordingly.
Thus, `Theme` mutations are not performed during load test experiments for more accurate measurements.

```yaml
queries:
- name: latency-queue # SLO 1
  type: instant
  slo: 1
  query: |
    histogram_quantile(0.99, sum by (le) (rate(
        workqueue_queue_duration_seconds_bucket{
          job="webhosting-operator", name="website"
        }[$__range]
    )))
- name: latency-reconciliation # SLO 2
  type: instant
  slo: 5
  query: |
    histogram_quantile(0.99, sum by (le) (rate(
        experiment_website_reconciliation_duration_seconds_bucket{
          job="experiment"
        }[$__range]
    )))
```

: Queries for verifying controller SLOs {#lst:controller-slo-queries}

[@Lst:controller-slo-queries] shows the queries used to verify that the described controller SLOs are satisfied.
Similar to verifying the control plane's SLOs, the measurements are taken over the duration of the load test instead of per cluster-day.
Note that the measurement for SLI 2 is stricter than the definition in [@sec:controller-scalability].
Originally, the reconciliation latency SLI excluded reconciliation time of controlled objects, as they are out of scope of the measured controller's responsibility.
In the load tests however, the reconciliation time of controlled objects – namely, `Deployments` – is short, because no replicas are actually deployed.
The `Deployment` controller just needs to observe the object and set the `Available` condition to true.
Hence, the measurement used for verifying SLO 2 includes the reconciliation time `Deployments` of `Websites` for simplicity.
Furthermore, the user's performance expectations are the same regardless of whether the controller is sharded or not.
Therefore, the measurement includes the sharding assignment latency related to the sharder's webhook or the sharder's controller respectively.

```yaml
queries:
- name: cpu # observed by cadvisor
  query: |
    sum by (namespace, pod) (rate(
      container_cpu_usage_seconds_total{
        pod=~"sharder-.+|webhosting-operator-.+",
        container=~"sharder|manager"
      }[1m]
    ))
- name: memory # observed by go runtime
  query: |
    sum by (namespace, pod) (
      go_memory_classes_total_bytes{pod=~"sharder-.+|webhosting-operator-.+"}
      - go_memory_classes_heap_released_bytes{
        pod=~"sharder-.+|webhosting-operator-.+"
      }
      - go_memory_classes_heap_unused_bytes{
        pod=~"sharder-.+|webhosting-operator-.+"
      }
      - go_memory_classes_heap_free_bytes{
        pod=~"sharder-.+|webhosting-operator-.+"
      }
    )
- name: network_receive # observed by cadvisor
  query: |
    sum by (namespace, pod) (rate(
      container_network_receive_bytes_total{
        pod=~"sharder-.+|webhosting-operator-.+"
      }[1m]
    ))
- name: network_transmit # observed by cadvisor
  query: |
    sum by (namespace, pod) (rate(
      container_network_transmit_bytes_total{
        pod=~"sharder-.+|webhosting-operator-.+"
      }[1m]
    ))
```

: Queries for measuring controller resource usage {#lst:resource-usage-queries}

In addition to measuring load and performance of the controllers, the resource consumption of the sharding components and the webhosting-operator are recorded as shown in [@lst:resource-usage-queries].
Similar to the experiments in the study project [@studyproject], the CPU and network usage are measured based on the kubelet's cadvisor metrics [@k8sdocs; @prometheusdocs].
Note that the measured network transfer includes regular scraping operations.
Prometheus is configured to scrape metrics from sharder and webhosting-operator every 10 seconds.
Parca is configured to scrape profiling data from sharder and webhosting-operator every 2 seconds.

The memory usage on the other hand is determined based on metrics exposed by the Go runtime.
This gives a better estimation of the actual memory requirements of the controller than the kernel's resident size set (RSS) record of the process, due to how Go facilitates memory management.
E.g., the Go runtime doesn't immediately release heap memory freed by garbage collection back to the operating system.
Hence, the process can hold more memory of the system than actually needed by the program, also due to the runtime's batch-based memory allocation.
The query used in this evaluation subtracts all released, unused, and free memory from the total amount of memory allocated by the process.

\todo[inline]{describe experiments dashboard, run-id handling}

## Experiments

Based on the described experiment setup, multiple experiment are performed.
The different scenarios, their goals, and their results are described in the following sections.
All scenarios are implemented and executed using the experiment tool.

### Comparison

The first experiment scenario generates a basic amount of load to compare the different controller setups.
It evaluates how the setups perform under load, ensures that the defined SLOs are satisfied, and measures the components' resource consumption.
The resource usage allows deducing how many resources must be added to the system for it to sustain the generated amount of load.
In other words, this scenario doesn't determine the load capacity of different setups and resource configurations, but instead determines how many resources are needed for the generated amount of load.
Most importantly, it observes how load and resource consumption are distributed across multiple instances.

In the `basic` scenario, the experiment tool creates, deletes, and updates `Website` objects for 15 minutes.
For this, it runs 3 controllers:

- The `website-generator` creates 12 random `Websites` per second.
- The `website-deleter` deletes 2 random `Websites` per second.
- The `website-mutator` updates the spec of each `Website` every minute.

With this, the generated load is slowly increased over a period of 15 minutes.
The number of objects (dimension 1) grows to roughly 9,000, while the churn rate grows to roughly 160 changes per second ([@fig:basic-load]).

![Generated load in basic scenario](../results/basic/load.pdf){#fig:basic-load}

The experiment scenario is executed for all three controller setups: the singleton controller, the internal sharder setup, and the external sharder setup.
For all three setups, measurements are performed as described above and the defined SLOs are verified.
Additional checks are performed to ensure the system is not limited anywhere and is generally performing well, e.g., that all created `Website` objects eventually get ready.
If all of these prerequisites are fulfilled, the resulting resource usage of the webhosting-operator and sharder are recorded to deduce how much resources are needed for sustaining the generated load ([@fig:basic-cpu; @fig:basic-memory; @fig:basic-network]).

By default the webhosting-operator runs 15 concurrent workers for the `website` controller.
If the webhosting-operator is deployed as a singleton controller, it runs 50 workers for the `website` controller to allow comparing experiment runs of sharded and non-sharded setups with the same load.
If the internal sharder is enabled, the leader instance runs 5 workers for the `shardlease` controller, and 10 workers for the `sharder` controllers respectively.

![CPU usage by pod in basic scenario](../results/basic/cpu.pdf){#fig:basic-cpu}

![Memory usage by pod in basic scenario](../results/basic/memory.pdf){#fig:basic-memory}

![Network usage by pod in basic scenario](../results/basic/network.pdf){#fig:basic-network}

The results show that the resource usage is well distributed across the shards in the external sharder setup.
Each shard roughly consumes a third of the resources consumed by the singleton controller.
The results also show that performing sharding for controllers comes with a resource overhead.
However, the external sharder's overhead is constant and doesn't increase with the controller's load in contrast to the internal sharder's overhead.
With this, the external sharder setup fulfills req. \ref{req:constant}, while the internal sharder setup does not.

### Horizontal Scalability

The second experiment evaluates the horizontal scalability of the external sharder design and implementation.
As described in [@sec:kubernetes-scalability], measuring the scalability of a system involves determining the maximum load capacity of different resource configurations.
The system is said to be scalable, if the load capacity can be increased by adding more resources.
If resources are added in the form of additional instances without adding resources to individual instances, the system is said to be horizontally scalable.

In the `scale-out` scenario, the experiment tool generates load with a high churn rate over 15 minutes.
It generates a total number of `Websites` similar to the `basic` scenario, but performs a higher rate of `Website` mutations:

- The `website-generator` creates 10 random `Websites` per second.
- The `website-mutator` updates the spec of each `Website` twice per minute.

With this, the number of objects (dimension 1) grows up to roughly 9,000, and the churn rate grows up to roughly 300 changes per second ([@fig:scale-out-load]).

![Generated load in scale out scenario](../results/scale-out/load.pdf){#fig:scale-out-load}

The scenario is executed for the external sharder setup with 1 to 5 webhosting-operator instances, which each run 5 concurrent workers for the `Website` controller.
To determine the maximum load capacity for which the SLOs are still satisfied, the SLIs are calculated for every 15 seconds instead of once for the entire time window.
For this, the SLO queries shown in [@lst:controller-slo-queries] are changed to range queries that consider all observations from the start of the experiment (cumulative percentiles) as shown in [@lst:controller-sli-queries-cumulative].

```yaml
queries:
- name: latency-queue # SLI 1
  query: |
    histogram_quantile(0.99, sum by (le) (
      workqueue_queue_duration_seconds_bucket{
        job="webhosting-operator", name="website"
      }
    ))
- name: latency-reconciliation # SLI 2
  query: |
    histogram_quantile(0.99, sum by (le) (
      experiment_website_reconciliation_duration_seconds_bucket{
        job="experiment"
      }
    ))
```

: Queries for calculating cumulative controller SLIs {#lst:controller-sli-queries-cumulative}

Usually, the `histogram_quantile` query function is used in combination with a `rate` function applied to number of observations per histogram bucket with upper bounds as specified in the `le` label.
This calculates a per-second increase of observations per bucket averaged across the range duration.
For this experiment, no range vector or `rate` function is used, but only the total number of observations.
This results in a time series that shows the 99th percentile of latency observations from the start of the experiment up until the value's time.
Note that the calculation using the `histogram_quantile` function is an estimate of the actual quantile based on histogram buckets and linear interpolation.
This causes the calculated SLIs to quickly grow when more observations start falling into the next higher histogram bucket.
For example, when buckets with upper bounds of 1 and 10 are used, the estimated 99th percentile quickly grows from less than 1 to less than 10, although the actual percentile might grow slower.
[@prometheusdocs]

For this evaluation however, the buckets' upper bounds are aligned with the SLOs.
This means, that for every SLI there is a bucket with the upper bound set to the corresponding SLO.
As interpolation is only applied between the bucket boundaries, the estimated SLI is guaranteed to grow above the SLO when the actual SLI also grows above the SLO and vice-versa.

After the experiment, the control plane SLOs are verified and the measurements are retrieved from Prometheus.
For each instance count, the last timestamp where the measured SLIs still satisfied the defined SLOs is determined ([@fig:scale-out-slos]).
This timestamp is then used to lookup values for both load dimensions.
The resulting value represents the maximum load capacity of each controller setup ([@fig:scale-out-capacity]).
Note that the load capacity values cannot be interpreted as absolute values but only in relation to other values of the same load test.

![Cumulative controller SLOs per instance count](../results/scale-out/slos.pdf){#fig:scale-out-slos}

![Load capacity increase with added instances](../results/scale-out/capacity.pdf){#fig:scale-out-capacity}

The results show that adding more controller instances bring more performance and increase the maximum load capacity of the system.
The load capacity grows almost linearly with the number of added instances, so that the setup fulfills req. \ref{req:scale-out}.
With this, applying the external sharding design makes Kubernetes controller horizontally scalable.

### Rolling Updates

- rolling updates of controller
- evaluate coordination on object movements
- show that SLOs are still met

### Chaos Testing

- randomly kill instances/leader
- similar to [knative chaosduck](https://github.com/knative/pkg/blob/main/leaderelection/chaosduck/main.go#L17)
- show that SLOs are still met

### Autoscaling

- similar to scale out scenario
- horizontal autoscaling of controller according to load
  - HPA on queue duration (SLI 1)
- evaluate coordination on object movements

## Discussion

- external sharder setup doesn't need much more resources to sustain the same load
- however, responsibility is distributed -> more instances can be added to increase the load capacity
