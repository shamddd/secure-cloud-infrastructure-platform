# ADR 0001: Separate desired state from cluster mutation

- Status: accepted
- Date: 2026-08-11

## Context

An internet-reachable control plane that also holds Kubernetes mutation credentials creates a large
blast radius. The portfolio scope needs to demonstrate secure workload admission and deployment
artifacts without inventing an unverified production reconciliation system.

## Decision

Persist validated desired state and render deterministic hardened manifests. Delegate policy review,
signing, and cluster apply to an external GitOps/release boundary. Do not mount a Kubernetes service-
account token into the API.

## Consequences

Compromise of the API cannot directly modify the cluster. Delivery is not fully automated inside this
repository, and the external GitOps system becomes a critical dependency requiring its own controls.
