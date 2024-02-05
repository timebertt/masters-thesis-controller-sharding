#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset

cd "$(dirname "$0")"

echo "=== scale-5 ==="
start="2024-02-05T15:06:55Z"
end="2024-02-05T15:21:55Z"

(
set -x;
measure --start="$start" --end="$end" ./apiserver-slos.yaml -o ./scale-5 --output-prefix apiserver-slo- --prometheus-url http://localhost:8080/api/prom;
measure --start="$start" --end="$end" ./controller-load.yaml -o ./scale-5 --output-prefix controller-load-;
measure --start="$start" --end="$end" ./controller-slos.yaml -o ./scale-5 --output-prefix controller-slos-;
measure --start="$start" --end="$end" ./resource-usage.yaml -o ./scale-5 --output-prefix resource-usage-;
)

echo "=== scale-4 ==="
start="2024-02-05T15:47:12Z"
end="2024-02-05T16:02:12Z"

(
set -x;
measure --start="$start" --end="$end" ./apiserver-slos.yaml -o ./scale-4 --output-prefix apiserver-slo- --prometheus-url http://localhost:8080/api/prom;
measure --start="$start" --end="$end" ./controller-load.yaml -o ./scale-4 --output-prefix controller-load-;
measure --start="$start" --end="$end" ./controller-slos.yaml -o ./scale-4 --output-prefix controller-slos-;
measure --start="$start" --end="$end" ./resource-usage.yaml -o ./scale-4 --output-prefix resource-usage-;
)

echo "=== scale-3 ==="
start="2024-02-05T14:35:53Z"
end="2024-02-05T14:50:53Z"

(
set -x;
measure --start="$start" --end="$end" ./apiserver-slos.yaml -o ./scale-3 --output-prefix apiserver-slo- --prometheus-url http://localhost:8080/api/prom;
measure --start="$start" --end="$end" ./controller-load.yaml -o ./scale-3 --output-prefix controller-load-;
measure --start="$start" --end="$end" ./controller-slos.yaml -o ./scale-3 --output-prefix controller-slos-;
measure --start="$start" --end="$end" ./resource-usage.yaml -o ./scale-3 --output-prefix resource-usage-;
)

echo "=== scale-2 ==="
start="2024-02-05T16:07:21Z"
end="2024-02-05T16:22:21Z"

(
set -x;
measure --start="$start" --end="$end" ./apiserver-slos.yaml -o ./scale-2 --output-prefix apiserver-slo- --prometheus-url http://localhost:8080/api/prom;
measure --start="$start" --end="$end" ./controller-load.yaml -o ./scale-2 --output-prefix controller-load-;
measure --start="$start" --end="$end" ./controller-slos.yaml -o ./scale-2 --output-prefix controller-slos-;
measure --start="$start" --end="$end" ./resource-usage.yaml -o ./scale-2 --output-prefix resource-usage-;
)

echo "=== scale-1 ==="
start="2024-02-05T15:27:03Z"
end="2024-02-05T15:42:03Z"

(
set -x;
measure --start="$start" --end="$end" ./apiserver-slos.yaml -o ./scale-1 --output-prefix apiserver-slo- --prometheus-url http://localhost:8080/api/prom;
measure --start="$start" --end="$end" ./controller-load.yaml -o ./scale-1 --output-prefix controller-load-;
measure --start="$start" --end="$end" ./controller-slos.yaml -o ./scale-1 --output-prefix controller-slos-;
measure --start="$start" --end="$end" ./resource-usage.yaml -o ./scale-1 --output-prefix resource-usage-;
)
