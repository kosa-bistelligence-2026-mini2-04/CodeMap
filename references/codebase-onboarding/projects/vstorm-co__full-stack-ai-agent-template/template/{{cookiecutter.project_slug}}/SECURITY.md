# Security

## Reporting a vulnerability

Email: **{{ cookiecutter.author_email }}** (or open a private security advisory on the repo). Please include:

- Affected version / commit
- Steps to reproduce
- Impact assessment (data exposure / privilege escalation / DoS / …)

We aim to acknowledge within 48h and ship a fix within 7 days for high-severity issues.

---

## Security model

### Authentication

{%- if cookiecutter.use_jwt %}
- **JWT (`HS256`)** signed with `SECRET_KEY`. Access token TTL = `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30 min). Refresh token TTL = `REFRESH_TOKEN_EXPIRE_MINUTES` (default 7 days).
- **Password hashing:** bcrypt via `passlib`. Plain passwords never persisted.
{%- if cookiecutter.enable_oauth_google %}
- **OAuth 2.0 (Google)** — auth-code flow. Token validated server-side, internal user record looked up/created by email.
{%- endif %}
{%- if cookiecutter.enable_session_management %}
- **Session management** — DB-backed sessions with revocation. Each refresh-token issuance creates a session row; `/sessions` endpoint lets users see + revoke devices.
{%- else %}
- **Stateless JWT** — no DB session table. Logout is client-side (drop tokens). For server-side revocation, regenerate with `--session-management`.
{%- endif %}
{%- endif %}
{%- if cookiecutter.use_api_key %}
- **Admin API key** — static `settings.API_KEY` matched via `X-API-Key` header for service-to-service calls. Constant-time compared with `secrets.compare_digest()`.
{%- endif %}

### Authorization

- **Role-based** via `RoleChecker` dep (`UserRole.USER` / `UserRole.ADMIN`).
{%- if cookiecutter.enable_admin_panel %}
- **Admin pages** require `role=admin`. Sensitive ops (impersonate user, system-health) gated separately.
{%- endif %}
{%- if cookiecutter.enable_teams %}
- **Workspace scope** — every authenticated request resolves an `ActiveOrg` (default = personal org). Resources scoped by `organization_id` foreign key.
- **Org roles:** `OWNER` / `ADMIN` / `MEMBER`. Owner can transfer ownership + delete org.
{%- endif %}

### Transport / network

- **CORS** — origin list from `settings.CORS_ORIGINS`. Restrict to your domains in production.
- **HTTPS** — enforce via reverse proxy (Nginx / Traefik / ALB). Strict-Transport-Security header set in middleware when `ENVIRONMENT=production`.
- **CSP** — frontend sets `frame-ancestors 'none'` by default to prevent click-jacking.{% if cookiecutter.use_frontend %} See `frontend/next.config.ts` headers block.{% endif %}

### Data

- **Secrets** — read from environment via `pydantic-settings`. Never committed. See `.env.example` + `ENV_VARS.md`.
{%- if cookiecutter.enable_admin_features_audit_log %}
- **Audit log** — admin-mutating actions (user updates, deletes, impersonations, role changes) recorded in `app_admin_audit_log` table with actor + IP + payload snapshot.
{%- endif %}
{%- if cookiecutter.enable_billing %}
- **Stripe webhooks** — signature verified via `stripe.Webhook.construct_event(secret=STRIPE_WEBHOOK_SECRET)`. Idempotency table prevents replay.
{%- endif %}
{%- if cookiecutter.enable_rag %}
- **RAG documents** — file uploads scoped per-org. No public read endpoint; all retrieval happens server-side during chat.
{%- endif %}

### Hardening checklist for production

- [ ] Rotate `SECRET_KEY` and `API_KEY` from generated defaults.
- [ ] Set `DEBUG=false` and `ENVIRONMENT=production`.
- [ ] Restrict `CORS_ORIGINS` to your domain(s).
{%- if cookiecutter.enable_rate_limiting %}
- [ ] Tune `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_PERIOD` in `.env`.
{%- endif %}
{%- if cookiecutter.enable_prometheus %}
- [ ] Set `PROMETHEUS_AUTH_TOKEN` if `/metrics` is exposed on a public endpoint.
{%- endif %}
{%- if cookiecutter.enable_sentry %}
- [ ] Set `SENTRY_DSN` to ship errors. Verify PII scrubbing rules in `core/sentry.py`.
{%- endif %}
- [ ] Enforce HTTPS at the proxy layer.
- [ ] Run `pip-audit` / `bun audit` in CI for dependency vulnerabilities.
- [ ] Configure database backups + restore test schedule.
{%- if cookiecutter.enable_billing %}
- [ ] Subscribe Stripe webhook to all relevant events; verify endpoint via Stripe CLI.
{%- endif %}

## Known limitations

- **No 2FA / MFA** out of the box. Plan to add TOTP via `pyotp` — see `notes/thingstofix.md` §A.13.
- **No SAML / OIDC** beyond Google OAuth. Enterprise SSO needs custom IdP integration.
- **No automatic PII redaction** in logs — be careful what you log.
{%- if cookiecutter.use_jwt and not cookiecutter.enable_session_management %}
- **No server-side session revocation** — JWTs valid until expiry. Compromised tokens require `SECRET_KEY` rotation (invalidates ALL sessions). Enable `--session-management` for selective revocation.
{%- endif %}
