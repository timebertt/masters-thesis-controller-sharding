#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset

cd "$(dirname "$0")"

echo "=== external ==="
start="2024-02-05T18:15:52Z"
end="2024-02-05T18:30:52Z"

(
set -x;
measure --start="$start" --end="$end" ./apiserver-slos.yaml -o ./external --output-prefix apiserver-slo- --prometheus-url http://localhost:8080/api/prom;
measure --start="$start" --end="$end" ./controller-load.yaml -o ./external --output-prefix controller-load-;
measure --start="$start" --end="$end" ./controller-slos.yaml -o ./external --output-prefix controller-slos-;
measure --start="$start" --end="$end" ./resource-usage.yaml -o ./external --output-prefix resource-usage-;
)

echo "=== internal ==="
start="2024-02-05T18:35:44Z"
end="2024-02-05T18:50:44Z"

(
set -x;
measure --start="$start" --end="$end" ./apiserver-slos.yaml -o ./internal --output-prefix apiserver-slo- --prometheus-url http://localhost:8080/api/prom;
measure --start="$start" --end="$end" ./controller-load.yaml -o ./internal --output-prefix controller-load-;
measure --start="$start" --end="$end" ./controller-slos.yaml -o ./internal --output-prefix controller-slos-;
measure --start="$start" --end="$end" ./resource-usage.yaml -o ./internal --output-prefix resource-usage-;
)

echo "=== singleton ==="
start="2024-02-05T18:54:07Z"
end="2024-02-05T19:09:07Z"

(
set -x;
measure --start="$start" --end="$end" ./apiserver-slos.yaml -o ./singleton --output-prefix apiserver-slo- --prometheus-url http://localhost:8080/api/prom;
measure --start="$start" --end="$end" ./controller-load.yaml -o ./singleton --output-prefix controller-load-;
measure --start="$start" --end="$end" ./controller-slos.yaml -o ./singleton --output-prefix controller-slos-;
measure --start="$start" --end="$end" ./resource-usage.yaml -o ./singleton --output-prefix resource-usage-;
)
