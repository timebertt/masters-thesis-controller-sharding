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
\todo{more details?}

As described in [@sec:controller-scalability], the scale of controller setups can be described in two dimensions: the number of API objects and the churn rate of API objects.
The webhosting-operator's main resource are `Website` objects, which control `Deployment`, `ConfigMap`, `Service`, and `Ingress` objects.
Accordingly, increasing the load on the webhosting-operator involves creating many `Website` objects and triggering `Website` reconciliations.
Additionally, changing the `Theme` referenced by a `Website`, also triggers a `Website` reconciliation.
Hence, the object churn rate of the webhosting-operator can also be increased by mutating the referenced `Themes`.

Load test experiments are conducted using the experiment tool developed as part of the study project [@studyproject].
It runs different experiment scenarios which continuously create and delete `Website` objects and trigger reconciliations for them.
With this, it can be used for increasing the scale of the example operator setup according to the described load dimensions.
During load tests, the webservers configured by `Website` objects are not actually run.
Running thousands of individual webservers would require an immense amount of compute resources although it is not required the managing controller itself.
Hence, the website's `Deployment` is configured with `spec.replicas=0`.
With this, the usual reconciliation flow of `Websites` is not changed, as the controller still waits for the `Available` condition of `Deployments` to be true, but no compute power is required for actually running the webservers.

\todo[inline]{described resources, configuration}
<!--
- precisely describe experiment setup
  - worker pools
  - sharder:
    - requests, limits
    - on which worker pool
    - configuration: concurrent workers
  - webhosting-operator
    - requests, limits
    - on which worker pool
    - configuration: concurrent workers
  - scale/compute resources of control plane
  - observe that the system is not limited:
    - etcd: CPU throttling, disk IOPS, WAL sync, DB sync
    - API server: CPU throttling, max inflight requests
    - webhosting-operator: CPU throttling, max active workers, ...
  - kube-controller-manager API rate limits
-->

## Measurements

To determine the controller's performance, several measurements are taken during load test experiments.
For this, the monitoring setup's Prometheus instance [@prometheusdocs] is used to collect and store metrics from the controller instances themselves, but also from kubelet's cadvisor endpoint [@k8sdocs; @cadvisor] and other exporters like kube-state-metrics [@kubestatemetrics].
After performing the load tests, the relevant metrics are retrieved from the Prometheus HTTP API using the measure tool [@studyproject] for later analysis and visualization.
The tool fetches raw time series data and stores the result matrices in CSV-formatted files.

For the measurements to be meaningful, the Kubernetes cluster SLOs themselves as described in [@sec:kubernetes-scalability] must be satisfied.
I.e., it must be ensured that the cluster itself where the controllers are running on is performing well.
While the latency of API requests (SLI 1 and 2) are relevant for the experiment setup, pod startup latency (SLI 3) is irrelevant as the load tests don't trigger pod startups.

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

```yaml
queries:
# SLO 1
- name: latency-mutating
  query: |
    histogram_quantile(0.99,
      sum by (resource, verb, le) (rate(
        apiserver_request_duration_seconds_bucket{
          cluster="shoot--timebertt--sharding",
          verb!~"GET|LIST|WATCH",
          subresource!~"log|exec|portforward|attach|proxy"
        }[$__range]
      ))
    ) <= 1
# SLO 2 - resource scope
- name: latency-read-resource
  query: |
    histogram_quantile(0.99,
      sum by (resource, scope, le) (rate(
        apiserver_request_duration_seconds_bucket{
          cluster="shoot--timebertt--sharding",
          verb=~"GET|LIST", scope="resource",
          subresource!~"log|exec|portforward|attach|proxy"
        }[$__range]
      ))
    ) <= 1
# SLO 2 - namespace and cluster scope
- name: latency-read-namespace-cluster
  query: |
    histogram_quantile(0.99,
      sum by (resource, scope, le) (rate(
        apiserver_request_duration_seconds_bucket{
          cluster="shoot--timebertt--sharding",
          verb=~"GET|LIST", scope=~"namespace|cluster",
          subresource!~"log|exec|portforward|attach|proxy"
        }[$__range]
      ))
    ) <= 30
```

: Queries for verifying control plane SLOs {#lst:k8s-slo-queries}

\todo{Update with final configuration}

- ref load dimensions in fundamentals, [@sec:controller-scalability]
  - show queries for load dimensions
  - number of objects:
    - `count(kube_website_info)`?
  - churn rate of objects:
    - websites:
      - `sum(rate(controller_runtime_reconcile_total{job="experiment", controller=~"website-.+", result!="error"}))`
    - themes:
      - `sum(rate(controller_runtime_reconcile_total{job="experiment", controller=~"theme-.+", result!="error"})) * count(kube_website_info) / count(kube_theme_info)`
      - estimate – website reconciliations caused by theme mutations cannot be measured exactly
      - could be measured by adding `Website.status.observedGenerationTheme` and corresponding metric: `sum(rate(kube_website_observed_generation_status))`
      - drop `Theme` reconciliations instead?
- ref SLIs defined in fundamentals, [@sec:controller-scalability]
  - measure over experiment time instead of cluster-day
  - SLI 1: p99 queue duration <= 1s
    - `histogram_quantile(0.99, sum(rate(workqueue_queue_duration_seconds_bucket{job="webhosting-operator"}[$__range])) by (name, le))`
  - SLI 2: p99 website reconciliation latency <= 30s
    - record time from creation/update to observed watch event of ready status in `experiment`
    - `histogram_quantile(0.99, sum(rate(experiment_website_reconciliation_duration_seconds_bucket{job="webhosting-operator"}[$__range])) by (name, le))`
    - hard to include `Theme` triggers, drop `Theme` reconciliations instead?
    - measurement stricter: include controlled objects (e.g., depends on kube-controller-manager: Deployment `Ready` condition)
    - includes sharding assignment latency
    - experiment is external observer that has the same usual client expectations independent of whether objects are sharded or not
- explain methodology
  - using multiple resources configurations and finding the maximum load capacity each is difficult and costly
  - adding resources difficult for some resources, e.g., network bandwidth
  - restraining resources difficult, e.g., memory -> would crash
- instead, run load tests with varying load, ensure the SLOs are met, and observe the required resource usage
  - higher resource usage means added resources
  - resource usage measurements allow deducing how many resources must be added to the system to sustain the generated load
  - similar to k8s scalability tests
- measure resource consumption of webhosting-operator and sharder using cadvisor and go runtime metrics
  - CPU: `sum(rate(container_cpu_usage_seconds_total{namespace=~"sharding-system|webhosting-system", container=~"sharder|manager"}[2m])) by (namespace, pod)`
  - memory: `sum(go_memory_classes_total_bytes{namespace=~"sharding-system|webhosting-system"} - go_memory_classes_heap_released_bytes{namespace=~"sharding-system|webhosting-system"} - go_memory_classes_heap_unused_bytes{namespace=~"sharding-system|webhosting-system"} - go_memory_classes_heap_free_bytes{namespace=~"sharding-system|webhosting-system"}) by (namespace, pod)`
    - better estimation of actual memory usage than `container_memory_rss`
    - Go runtime allocates more heap memory than actually needed, might not release garbage collected heap memory to OS immediately
    - query subtracts all released, unused, and free memory from the total memory held by the process
  - network traffic
    - receive: `sum(irate(container_network_receive_bytes_total{namespace=~"sharding-system|webhosting-system", pod=~"sharder-.+|webhosting-operator-.+"}[2m])) by (namespace, pod)`
    - transmit: `sum(irate(container_network_transmit_bytes_total{namespace=~"sharding-system|webhosting-system", pod=~"sharder-.+|webhosting-operator-.+"}[2m])) by (namespace, pod)`

## Experiments

### Basic Load

- increase load until a pre-defined limit
- measure resource usage, ensure SLOs are met
- run with singleton, internal sharder, external sharder
- show distribution of work/resource usage proportional to number of objects
- show that overhead of sharder doesn't increase with number of objects any more (req. \ref{req:constant})

### Scale Out

- show that more replicas bring more performance, allow increasing the load while keeping SLOs (req. \ref{req:scale-out})
- this is what proves that controllers are horizontally scalable now!
- limit instances: CPU, memory, concurrent workers
- run basic scenario against external sharder setup with 1, 2, 3 replicas
- measure the maximum load under which SLOs are still satisfied
- show that more replicas bring higher maximum load
- show that overhead of sharding is constant, independent of number of objects (load) (req. \ref{req:constant})

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
