#!/usr/bin/env sh
set -eu

if [ ! -f .env ]; then
  echo "Missing .env. Run 'make env' first." >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required for the demo." >&2
  exit 1
fi

set -a
. ./.env
set +a

docker compose up --build -d
docker compose run --rm api scip-bootstrap-admin >/dev/null 2>&1 || true

echo "Waiting for the API to become ready..."
attempt=0
until curl --fail --silent http://127.0.0.1:8000/health/ready >/dev/null; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    echo "API did not become ready; inspect 'docker compose logs api'." >&2
    exit 1
  fi
  sleep 2
done

token=$(
  curl --fail --silent \
    -X POST http://127.0.0.1:8000/v1/auth/token \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode "username=$SCIP_BOOTSTRAP_ADMIN_USERNAME" \
    --data-urlencode "password=$SCIP_BOOTSTRAP_ADMIN_PASSWORD" \
  | jq -r .access_token
)

image="registry.example.test/payments@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
created=$(
  curl --fail --silent \
    -X POST http://127.0.0.1:8000/v1/workloads \
    -H "Authorization: Bearer $token" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"payments-api\",\"image\":\"$image\",\"replicas\":2}"
)

echo "Created desired workload specification:"
echo "$created" | jq '{id,name,image,replicas,version,status}'

workload_id=$(echo "$created" | jq -r .id)
scaled=$(
  curl --fail --silent \
    -X PATCH "http://127.0.0.1:8000/v1/workloads/$workload_id/scale" \
    -H "Authorization: Bearer $token" \
    -H 'Content-Type: application/json' \
    -d '{"replicas":4,"expected_version":1}'
)

echo "Scaled with optimistic concurrency:"
echo "$scaled" | jq '{name,replicas,version}'

echo "Rendered hardened Kubernetes resources:"
curl --fail --silent \
  "http://127.0.0.1:8000/v1/workloads/$workload_id/manifest" \
  -H "Authorization: Bearer $token" \
| jq '{version: .metadata.annotations["scip.dev/workload-version"], resources: [.items[].kind]}'

echo "Recent audit events:"
curl --fail --silent \
  http://127.0.0.1:8000/v1/audit-events?limit=5 \
  -H "Authorization: Bearer $token" \
| jq '[.[] | {action,resource_type,resource_id,actor}]'

echo "API: http://127.0.0.1:8000/docs"
echo "Prometheus: http://127.0.0.1:9090"
echo "Grafana: http://127.0.0.1:3000"
