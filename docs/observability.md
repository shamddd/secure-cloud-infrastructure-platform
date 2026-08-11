# Observability

## Signals

- JSON application logs: request ID, HTTP method/path, duration, event name, environment
- Prometheus metrics: request count and request-latency histogram by method/path/status
- OpenTelemetry traces: FastAPI and SQLAlchemy spans exported through OTLP/HTTP
- health: process liveness and database-backed readiness

Request and response bodies, authorization headers, passwords, service secrets, signing keys, and
database URLs are deliberately excluded from logs and metrics.

## Local stack

Compose provisions Prometheus, a preconfigured Grafana datasource/dashboard, and an OpenTelemetry
Collector with the debug exporter. Debug trace output is suitable only for local development; route
production traces to an approved backend.

## Starter alert policy

Create environment-specific alerts for:

- readiness unavailable for more than five minutes;
- elevated 5xx rate over a rolling window;
- p95 latency regression against an established baseline;
- sustained database connection or query errors;
- unexpected 401/403 surge;
- missing scrape targets or collector export failures;
- HPA saturation at maximum replicas;
- failed migration Job or unavailable PodDisruptionBudget.

No numeric SLO is asserted in this repository because representative production traffic has not been
measured. Establish a baseline with load tests and stakeholder error-budget requirements before
setting targets.

## Troubleshooting path

1. Confirm `/health/live`; a failure indicates the process or networking is unavailable.
2. Confirm `/health/ready`; a live-but-not-ready API usually indicates database connectivity.
3. Trace one sanitized `X-Request-ID` through API logs.
4. Compare status/latency metrics with OTel spans for the same interval.
5. Inspect the migration Job and PostgreSQL health before restarting application replicas.
