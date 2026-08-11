# GCP Terraform stack

This stack defines a hardened GCP target architecture. It has been formatted and
validated statically, but it has not been applied to a Google Cloud project.

It creates:

- a custom VPC, private GKE nodes, Cloud NAT, and explicit control-plane
  authorized networks;
- VPC-native GKE with Dataplane V2, Workload Identity Federation, Shielded
  Nodes, managed Prometheus, and Binary Authorization enforcement;
- a separately managed autoscaling node pool with a least-privilege node
  service account;
- private Cloud SQL for PostgreSQL with encrypted-only connections, regional
  availability, backups, point-in-time recovery, and IAM database
  authentication enabled;
- Artifact Registry and empty Secret Manager containers for runtime secrets.

The stack deliberately does not create secret versions or database passwords.
Populate secrets through an approved secret-delivery workflow so plaintext does
not enter Terraform configuration or plans. Remote Terraform state still
contains sensitive infrastructure metadata; use a restricted, versioned GCS
bucket with retention and audit logging.

## Validate

```bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```

## Plan

```bash
cp terraform.tfvars.example terraform.tfvars
# Replace every example value, especially the authorized operator CIDR.
terraform init -backend-config=backend.tf
terraform plan -out=scip.tfplan
```

Review the plan, organization policies, regional quotas, and cost estimate before
any approved apply. No cloud resources are created by this repository alone.
