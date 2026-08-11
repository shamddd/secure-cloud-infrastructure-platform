# Security operations

## Secret handling

Local development uses `scripts/init-env.sh`, which generates `.env` with restrictive permissions.
Production secrets must enter Kubernetes through an approved secret controller backed by Secret
Manager. Never commit `.env`, secret versions, service-account JSON, certificate private keys, or
Terraform state.

The Helm chart expects these keys in the configured runtime Secret:

- `SCIP_DATABASE_URL`
- `SCIP_JWT_SIGNING_KEY`

Restrict Secret reads to the API workload. The API service account itself does not need a mounted
Kubernetes token. Redact environment dumps from support bundles.

## JWT key rotation

The current reference uses one HS256 key and a configured key ID. Rotation is a planned operational
limitation, not an automated feature. To rotate safely today:

1. shorten the token TTL if operationally acceptable;
2. replace the Secret value and increment `SCIP_JWT_KEY_ID` during a controlled rollout;
3. expect tokens signed by the old key to fail immediately;
4. monitor authentication failures and roll back both values together if required.

A production extension should use asymmetric keys and accept both old and new public keys for an
overlap window.

## Exposure controls

Terminate TLS at the ingress with a managed certificate and redirect HTTP to HTTPS. Keep `/metrics`
reachable only from the monitoring namespace or authenticated telemetry proxy. Disable OpenAPI docs
in production. Configure the ingress for request-size limits, per-identity/IP rate limiting, timeouts,
and an allowlist where appropriate.

## Dependency and image response

Dependabot proposes updates weekly. CI runs source, dependency, secret, and infrastructure scans.
For a critical finding: confirm affected reachability, patch/upgrade the lock file or base image,
rerun the full gate, produce a new image digest, deploy canary-first, and record the decision if the
finding is accepted temporarily.

See [SECURITY.md](../SECURITY.md) for private vulnerability reporting.
