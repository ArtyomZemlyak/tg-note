# CI/CD Pipeline

This document describes the continuous integration and deployment pipelines for the tg-note project.

## GitHub Actions Workflows

### Publish to PyPI

The project uses GitHub Actions to automatically publish releases to PyPI using Trusted Publishing (OIDC authentication).

**Workflow file**: `.github/workflows/publish-to-pypi.yml`

**Triggers**:

- When a new release is published on GitHub
- Manual workflow dispatch

**What it does**:

1. Checks out the repository
2. Sets up Python 3.11
3. Installs Poetry and project dependencies
4. Builds the distribution packages
5. Publishes to PyPI using trusted publishing (no API tokens required)

**Environment**: `pypi`

For detailed setup instructions, see [PyPI Trusted Publisher Setup](pypi-trusted-publisher-setup.md).

## Setting Up CI/CD

### PyPI Publishing

To enable automatic publishing to PyPI:

1. Configure a trusted publisher on PyPI (see [setup guide](pypi-trusted-publisher-setup.md))
2. Create a `pypi` environment in GitHub repository settings
3. (Optional) Add protection rules to the environment

### Creating a Release

To trigger a new PyPI release:

1. **Via GitHub UI**:
   - Go to Releases → Draft a new release
   - Create a new tag (e.g., `v0.1.0`)
   - Publish the release

2. **Via Git CLI**:

   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

3. **Via GitHub CLI**:

   ```bash
   gh release create v0.1.0 --title "Release v0.1.0" --notes "Release notes here"
   ```

The workflow will automatically build and publish the package to PyPI.

## Future Improvements

Potential additions to the CI/CD pipeline:

- Automated testing on pull requests
- Code quality checks (linting, type checking)
- Documentation deployment
- Docker image building and publishing
- Automated changelog generation
