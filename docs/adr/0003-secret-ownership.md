# ADR 0003: Keep secret material outside Terraform and Helm values

- Status: accepted
- Date: 2026-08-11

## Context

Terraform plans/state and Helm release values are durable, broadly copied artifacts. Generating or
passing credentials through them creates unnecessary plaintext persistence.

## Decision

Terraform creates only empty Secret Manager containers. Helm accepts the name of a pre-existing
Kubernetes Secret. An external approved secret-delivery system owns secret versions and rotation.

## Consequences

Plans and release values do not intentionally contain runtime credentials. Deployment has an explicit
external prerequisite, and secret-controller health/permissions must be operated separately.
