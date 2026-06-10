# Governance

## Overview

Full-Stack AI Agent Template is maintained by [Vstorm](https://vstorm.co), a Poland-based AI engineering consultancy.

## Decision Making

This project follows a **Benevolent Dictator** governance model:

- **Project Lead**: Kacper Wlodarczyk ([@sebastiondev](https://github.com/sebastiondev)) makes final decisions on project direction, feature inclusion, and releases.
- **Community Input**: Feature requests, bug reports, and discussions happen via [GitHub Issues](https://github.com/vstorm-co/full-stack-ai-agent-template/issues) and Pull Requests. All input is considered.
- **Pull Requests**: Reviewed by the project lead or designated maintainers. All PRs require at least one approving review before merge.

## Roles and Responsibilities

### Project Lead

**Current**: Kacper Wlodarczyk ([@sebastiondev](https://github.com/sebastiondev))

- Set project roadmap and long-term direction
- Approve or reject new features and architectural changes
- Cut releases and publish to PyPI
- Respond to security vulnerability reports (per [SECURITY.md](SECURITY.md))
- Grant or revoke maintainer access
- Final authority on all merge decisions

### Maintainer

**Current**: Vstorm team

- Review and merge Pull Requests (at least one approval required)
- Triage issues: label, assign, close duplicates
- Ensure CI passes before merging
- Maintain documentation accuracy
- Monitor and respond to community discussions

### Contributor

**Current**: Anyone (with [DCO](DCO) sign-off)

- Submit Pull Requests with bug fixes, features, or documentation improvements
- Report bugs and request features via GitHub Issues
- Participate in discussions and code reviews
- Follow the project's coding standards and testing requirements

## Contributions

All contributions require [Developer Certificate of Origin (DCO)](DCO) sign-off. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Releases

Releases follow [Semantic Versioning](https://semver.org/). The project lead decides release timing and content.

## Bus Factor and Continuity Plan

The project maintains a **bus factor of 2**. At least two people have the access and knowledge required to manage every critical aspect of the project (GitHub org ownership, PyPI publishing, DNS, CI/CD secrets).

The project is designed to continue with minimal interruption if any single contributor becomes unavailable:

- **GitHub Organization**: The repository is owned by the [vstorm-co](https://github.com/vstorm-co) GitHub organization. Multiple team members have **Owner** access, ensuring no single point of failure for repository management, issue triage, and PR merges.
- **PyPI**: The `fastapi-fullstack` package on PyPI has multiple maintainers with publish rights, allowing releases to continue independently.
- **DNS / Domain**: The `vstorm.co` domain is registered under the organization, not a personal account.
- **CI/CD**: GitHub Actions secrets are managed at the organization level. Any organization Owner can update or rotate them.
- **Forks**: As an MIT-licensed project, the community can fork and continue development at any time without legal barriers.

In the event that the Project Lead becomes permanently unavailable, the remaining organization Owners will appoint a new lead within one week.

## Security

Security vulnerabilities should be reported per [SECURITY.md](SECURITY.md). Critical issues are prioritized above all other work.
