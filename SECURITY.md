# Security policy

## Supported versions

This pre-1.0 reference implementation supports only the current `main` branch. Security fixes are not
backported unless a maintained release line is announced.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's private vulnerability
reporting feature for this repository. If that feature is unavailable, contact the repository owner
through the private contact method on their GitHub profile and ask for a secure reporting channel;
do not include exploit details in the first message.

Include the affected revision, impact, prerequisites, a minimal safe reproduction, and suggested
remediation. Remove credentials, tokens, customer data, private endpoints, and cloud identifiers.

The maintainer should acknowledge a valid report within five business days, coordinate a fix and
disclosure timeline based on severity, and credit the reporter if requested. This is a best-effort
open-source policy, not a commercial SLA or bug-bounty commitment.

## Scope

Authentication/authorization bypass, secret exposure, injection, unsafe workload generation,
container/CI/IaC supply-chain flaws, and insecure default deployment behavior are in scope. Findings
that require a deliberately insecure local configuration or unsupported third-party environment may
still be useful but will be triaged separately.
