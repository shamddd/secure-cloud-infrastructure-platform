# Deployment and rollback runbook

## Preconditions

- reviewed Terraform plan and approved cost/quota impact;
- remote state bucket with versioning, access logging, retention, and restricted IAM;
- scanned application image in Artifact Registry, referenced by digest;
- externally managed runtime Secret and TLS certificate;
- environment-specific ingress and NetworkPolicy values;
- database backup/PITR health confirmed;
- change window, owner, success metrics, and rollback authority identified.

## Deploy infrastructure

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
# Replace all examples and configure backend.tf from backend.tf.example.
terraform init -backend-config=backend.tf
terraform fmt -check -recursive
terraform validate
terraform plan -out=scip.tfplan
terraform show scip.tfplan
```

Apply only after peer review. The included Terraform has not been applied by this repository and no
cloud resources are claimed to exist.

## Deploy application

```bash
helm upgrade --install scip infrastructure/helm/scip \
  --namespace scip --create-namespace \
  --values values.production.yaml \
  --set image.repository=REGION-docker.pkg.dev/PROJECT/REPOSITORY/scip \
  --set image.digest=sha256:IMAGE_DIGEST \
  --atomic --timeout 10m
```

The migration Job runs as a Helm pre-install/pre-upgrade hook. Use expand-and-contract schema changes
so the previous and next application versions can overlap. After deploy, verify Job completion,
ready replicas, liveness/readiness, authorization smoke tests, error rate, latency, traces, and audit
event writes.

## Rollback

Application rollback is `helm rollback scip REVISION --atomic --timeout 10m` using the prior image
digest. Do not reverse a schema migration unless its down migration has been tested and data-loss
impact approved. Prefer rolling the application back while retaining backward-compatible expanded
schema, then contract in a later change.

Terraform rollback is a new reviewed plan, not a state-file edit. Deletion protection intentionally
prevents accidental removal of GKE and Cloud SQL. For a failed infrastructure change, restore the
previous configuration, generate a plan, and review every destructive action before apply.

## Incident evidence

Record deployment revision, image digest, migration revision, Terraform plan/apply identifier,
request IDs, alert timeline, and sanitized logs. Never copy tokens, credentials, customer data, or
private endpoints into the incident ticket.
