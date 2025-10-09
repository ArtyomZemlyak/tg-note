# PyPI Trusted Publisher Setup

This guide explains how to configure PyPI Trusted Publishing for the `tg-note` package.

## What is Trusted Publishing?

Trusted Publishing is a secure authentication method that allows GitHub Actions to publish packages to PyPI without using API tokens. It uses OpenID Connect (OIDC) to verify the identity of the publisher.

## Prerequisites

1. A PyPI account with permissions to manage the `tg-note` package
2. The package must either already exist on PyPI or you need permission to register it

## Configuration Steps

### Step 1: Access PyPI Trusted Publisher Settings

1. Go to [PyPI](https://pypi.org/) and log in
2. Navigate to your account settings
3. Go to "Publishing" section

### Step 2: Add a New Trusted Publisher

Choose one of these options:

#### Option A: For an Existing Package

1. Go to your package page: <https://pypi.org/manage/project/tg-note/settings/>
2. Scroll to "Publishing" section
3. Click "Add a new publisher"

#### Option B: For a New Package (Pending Publisher)

1. Go to: <https://pypi.org/manage/account/publishing/>
2. Click "Add a pending publisher"
3. This allows you to configure the trusted publisher before the first release

### Step 3: Configure the Publisher

Fill in the following details **exactly** as shown:

| Field | Value |
|-------|-------|
| **PyPI Project Name** | `tg-note` |
| **Owner** | `ArtyomZemlyak` |
| **Repository name** | `tg-note` |
| **Workflow name** | `publish-to-pypi.yml` |
| **Environment name** | `pypi` |

### Step 4: Verify Configuration

After adding the publisher, verify the configuration matches these claims:

```yaml
repository: ArtyomZemlyak/tg-note
workflow_ref: ArtyomZemlyak/tg-note/.github/workflows/publish-to-pypi.yml@refs/tags/v*
environment: pypi
```

### Step 5: Create GitHub Environment

1. Go to your GitHub repository: <https://github.com/ArtyomZemlyak/tg-note>
2. Navigate to Settings → Environments
3. Click "New environment"
4. Name it `pypi`
5. (Optional) Add protection rules:
   - Require reviewers before deployment
   - Restrict to specific branches (e.g., only tags matching `v*`)

## Testing the Configuration

### Create a Test Release

```bash
# Create and push a new tag
git tag v0.0.2
git push origin v0.0.2
```

Or create a release through the GitHub UI:

1. Go to Releases
2. Click "Draft a new release"
3. Create a new tag (e.g., `v0.0.2`)
4. Publish the release

The workflow will automatically trigger and publish to PyPI using trusted publishing.

## Troubleshooting

### Error: "invalid-publisher: valid token, but no corresponding publisher"

This means the configuration on PyPI doesn't match the claims being sent. Verify:

1. **Package name** matches exactly: `tg-note`
2. **Repository** is correct: `ArtyomZemlyak/tg-note`
3. **Workflow file** path is exact: `publish-to-pypi.yml` (not `.github/workflows/publish-to-pypi.yml`)
4. **Environment name** matches: `pypi`
5. The trusted publisher is active (not expired or disabled)

### Error: "environment-not-found"

Create the `pypi` environment in your GitHub repository settings.

### Error: "workflow-not-found"

Ensure the workflow file exists at `.github/workflows/publish-to-pypi.yml` in your repository.

## Security Best Practices

1. **Use environments**: Always specify an environment for publishing workflows
2. **Add protection rules**: Require reviews for deployments to the `pypi` environment
3. **Limit workflow permissions**: The workflow only requests `id-token: write` permission
4. **Monitor releases**: Regularly check your PyPI package for unexpected uploads

## Manual Workflow Trigger

You can also manually trigger the workflow:

```bash
# Through GitHub CLI
gh workflow run publish-to-pypi.yml

# Or through the GitHub UI
# Go to Actions → Publish to PyPI → Run workflow
```

## References

- [PyPI Trusted Publishers Documentation](https://docs.pypi.org/trusted-publishers/)
- [PyPI Trusted Publishers Troubleshooting](https://docs.pypi.org/trusted-publishers/troubleshooting/)
- [GitHub Actions OIDC Documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
