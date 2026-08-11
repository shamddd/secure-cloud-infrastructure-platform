# Contributing

## Development setup

Install Python 3.12+ and `uv`, then run:

```bash
make install
make check
```

Use a short-lived branch and keep changes bounded. Do not commit `.env`, state files, generated cloud
credentials, tokens, private endpoints, or personal/customer data.

## Change requirements

- Add or update tests for behavior and authorization boundaries.
- Preserve strict typing, deterministic validation, and fail-closed production configuration.
- Use an Alembic migration for schema changes; prefer expand-and-contract compatibility.
- Update the threat model, ADRs, API table, and runbooks when a trust boundary changes.
- Pin application images by digest and GitHub Actions by full commit SHA.
- State deployment signals and rollback for operational changes.

Commit messages should be imperative and focused, for example `feat: render hardened workload
manifests`. Pull requests must explain behavior, security/operational impact, validation, rollout, and
rollback.

## Code review

Reviewers should verify authorization at the route and service boundary, transactional audit
coverage, secret/logging behavior, migration compatibility, resource limits, and failure handling.
Infrastructure changes require both generated-plan review and validation in the target organization;
static validation alone does not prove deployability or cost safety.

By participating, you agree to follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
