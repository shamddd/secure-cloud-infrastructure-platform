# ADR 0002: Combine ordered roles with attenuated scopes

- Status: accepted
- Date: 2026-08-11

## Context

Roles are understandable for operators but are often too broad for automation. Free-form scopes can
be narrow but make governance harder and can accidentally exceed a subject's assigned role.

## Decision

Each route requires a minimum ordered role and explicit scopes. Every role defines a maximum scope
set. Service-account scopes may be narrowed, and token decoding rejects a claimed scope outside that
maximum.

## Consequences

Human authorization remains legible while automation receives least privilege. Adding a capability
requires coordinated role mapping, route authorization, schema, test, and documentation changes.
