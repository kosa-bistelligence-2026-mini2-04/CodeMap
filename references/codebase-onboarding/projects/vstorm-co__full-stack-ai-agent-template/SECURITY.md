# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.2.x (latest) | ✅ |
| < 0.2.0 | ❌ |

Only the latest minor release receives security fixes. We recommend always using the latest version.

## Reporting a Vulnerability

**Please do not report security vulnerabilities via public GitHub Issues.**

To report a vulnerability, email the maintainers at:

**security@vstorm.co**

Include in your report:
- Description of the vulnerability
- Steps to reproduce (CLI invocation or generated project behavior)
- Affected versions
- Potential impact
- Any suggested fix (optional)

## Response Timeline

| Stage | Target |
|-------|--------|
| Acknowledgement | Within 48 hours |
| Initial assessment | Within 5 business days |
| Fix or mitigation | Within 30 days for critical/high |
| Public disclosure | After fix is released |

We follow coordinated disclosure — we ask that you give us time to release a fix before public disclosure.

## Scope

In scope:
- Vulnerabilities in the CLI generator itself (`fastapi-fullstack` package)
- Security issues in the generated project template code (auth, JWT handling, SSRF, etc.)
- Unsafe defaults in generated project configuration
- Path traversal or template injection via cookiecutter inputs

Out of scope:
- Vulnerabilities in third-party dependencies (report to the respective project)
- Security issues introduced by users after project generation
- Issues requiring physical access to the machine

## Security Requirements — What You Can and Cannot Expect

### What the generated project provides

Generated projects ship with the following security controls enabled by default:

| Control | Implementation | OWASP |
|---------|---------------|-------|
| **Authentication** | JWT access + refresh tokens, bcrypt password hashing, API key auth | A07:2021 |
| **Authorization** | Role-based access control (RBAC) with `RoleChecker` dependency | A01:2021 |
| **SQL Injection prevention** | SQLAlchemy ORM with parameterized queries (no raw SQL) | A03:2021 |
| **XSS prevention** | HTML sanitization utilities, Pydantic input validation | A03:2021 |
| **SSRF protection** | `validate_webhook_url()` blocks private/reserved/loopback IPs, DNS rebinding checks | A10:2021 |
| **CORS** | Explicit origin allowlists, `*` blocked in production | A05:2021 |
| **CSRF protection** | HTTP-only cookies for tokens, SameSite cookie attributes | A01:2021 |
| **Input validation** | All API inputs validated via Pydantic v2 strict schemas | A03:2021 |
| **Secret management** | `.env`-based configuration, `.gitignore` excludes secrets | A02:2021 |
| **Dependency scanning** | `pip-audit` in CI scans for known CVEs on every build | A06:2021 |
| **Path traversal prevention** | `sanitize_filename()` and `validate_safe_path()` utilities | A01:2021 |
| **Encrypted token storage** | Channel bot tokens encrypted at rest with Fernet (AES-128-CBC) | A02:2021 |
| **Constant-time comparison** | `secrets.compare_digest()` for API key verification | A02:2021 |
| **Webhook signature verification** | HMAC-SHA256 for Telegram and Slack webhook endpoints | A08:2021 |

### What is NOT provided (user responsibility)

- **Network security** — Firewalls, VPNs, TLS termination are your responsibility. The template includes Traefik with Let's Encrypt for HTTPS, but you must configure DNS and deployment.
- **Infrastructure hardening** — OS patching, container image scanning, Kubernetes network policies are out of scope.
- **Data encryption at rest** — Database-level encryption (TDE) is not configured by default. Enable it at the database layer.
- **Rate limiting tuning** — Default rate limits are generous for development. Tune for production workloads.
- **LLM output safety** — The template does not filter or sanitize LLM outputs. Implement content moderation if user-facing.
- **Secrets rotation** — JWT secret keys and encryption keys are generated once. Implement rotation for production.
- **Audit logging** — Request-level logging is included, but compliance audit trails (SOC2, HIPAA) require additional implementation.
- **Penetration testing** — Generated code follows security best practices but has not been formally pen-tested. Test before production deployment.

### CLI generator security

- `pip-audit` in CI — scans for known CVEs on every build
- `ty` type checking — catches type-related issues at build time
- Ruff linting — enforces safe coding patterns
- 100% test coverage — all template combinations tested

## Acknowledgements

We thank all security researchers who responsibly disclose vulnerabilities to us. Confirmed reporters will be credited in the release notes unless they prefer to remain anonymous.
