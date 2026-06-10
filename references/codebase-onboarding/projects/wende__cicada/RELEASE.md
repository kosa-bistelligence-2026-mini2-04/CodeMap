# Release Process

This document describes how releases are automated for the Cicada project.

## Automated Release Workflow

The project uses GitHub Actions to automatically publish releases to PyPI when version tags are pushed.

### How It Works

1. **Push a version tag** (e.g., `v0.1.5`):
   ```bash
   git tag v0.1.5
   git push origin v0.1.5
   ```

2. **Automatic workflow triggers**:
   - Tests run on TestPyPI first
   - If successful, package is published to real PyPI
   - If TestPyPI fails, real PyPI publish is skipped

3. **GitHub Release** is created automatically with release notes

### Workflow Jobs

1. **test-publish**: Builds, tests, and publishes to TestPyPI
   - Runs full test suite
   - Builds the package
   - Publishes to TestPyPI
   - Verifies installation from TestPyPI

2. **publish**: Publishes to real PyPI (only if test-publish succeeds)
   - Builds the package
   - Publishes to PyPI
   - Verifies installation from PyPI

## Required GitHub Secrets

You must configure these secrets in your GitHub repository settings:

### 1. PYPI_API_TOKEN

Create a PyPI API token:
1. Go to https://pypi.org/manage/account/token/
2. Click "Add API token"
3. Name: `cicada-github-actions`
4. Scope: Select "Project: cicada-mcp" (or entire account)
5. Copy the token (starts with `pypi-`)
6. Add to GitHub secrets as `PYPI_API_TOKEN`

### 2. TEST_PYPI_API_TOKEN

Create a TestPyPI API token:
1. Go to https://test.pypi.org/manage/account/token/
2. Click "Add API token"
3. Name: `cicada-github-actions-test`
4. Scope: Select "Project: cicada-mcp" (or entire account)
5. Copy the token (starts with `pypi-`)
6. Add to GitHub secrets as `TEST_PYPI_API_TOKEN`

### Adding Secrets to GitHub

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add both tokens as described above

## Manual Release (Alternative)

You can also manually trigger a release:

1. Go to **Actions** → **Publish to PyPI**
2. Click **Run workflow**
3. Choose options:
   - **test_only**: Only publish to TestPyPI (skip real PyPI)
4. Click **Run workflow**

## Pre-Release Checklist

Before creating a release tag:

- [ ] Update version in `pyproject.toml`
- [ ] Update version references in `README.md` if needed
- [ ] Run tests locally: `uv run pytest`
- [ ] Update `CHANGELOG.md` (if exists)
- [ ] Commit all changes
- [ ] Push to remote

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):
- **Major** (v1.0.0): Breaking changes
- **Minor** (v0.1.0): New features, backwards compatible
- **Patch** (v0.0.1): Bug fixes

## Troubleshooting

### TestPyPI publish fails
- Check that `TEST_PYPI_API_TOKEN` is set correctly
- Verify you haven't already published this version to TestPyPI
- TestPyPI tokens expire - regenerate if needed

### PyPI publish fails
- Check that `PYPI_API_TOKEN` is set correctly
- Verify version number is unique (not already published)
- Check PyPI for any service issues

### Tests fail in workflow
- Run tests locally first: `uv run pytest`
- Check workflow logs for specific errors
- Ensure all dependencies are in `pyproject.toml`

## Monorepo Package Publishing

This project uses a monorepo structure with multiple packages:

1. **cicada-mcp** - Main package (depends on cicada-mcp-core)
2. **cicada-mcp-core** - Core utilities (zero external dependencies)
3. **cicada-scip** - SCIP indexing support (depends on cicada-mcp-core)

### Publishing Behavior

The workflow publishes packages in dependency order:
1. First: `cicada-mcp-core`
2. Second: `cicada-mcp`

#### cicada-mcp-core Error Handling

The publish workflow has **intelligent error handling** for `cicada-mcp-core`:

| Scenario | Result |
|----------|--------|
| Publish succeeds | ✅ Continue to next package |
| Version already exists on PyPI | ⚠️ Continue (expected when core hasn't changed) |
| Authentication failure | ❌ **Build fails** |
| Network error | ❌ **Build fails** |
| Build/packaging error | ❌ **Build fails** |

This ensures that:
- **Real errors are not masked** - Authentication, network, or build issues will fail the release
- **Idempotent releases work** - Re-releasing the same version without bumping core is allowed
- **Only "already exists" errors are tolerated** - Detected via output patterns: `already exists`, `FileExistsError`, `400 Bad Request`

### When to Bump cicada-mcp-core Version

Bump `cicada-mcp-core` version in `packages/cicada-mcp-core/pyproject.toml` when:
- Core utilities change
- Base indexer changes
- Formatter interface changes
- Hash utilities change

Keep `cicada-mcp-core` version unchanged when:
- Only main `cicada-mcp` code changes
- Only `cicada-scip` changes
- Documentation changes

## Related Files

- `.github/workflows/publish-pypi.yml` - Main release workflow
- `pyproject.toml` - Package configuration and version
- `packages/cicada-mcp-core/pyproject.toml` - Core package version
- `CLAUDE.md` - Project guidelines including release process
