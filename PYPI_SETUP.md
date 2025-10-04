# Quick Fix for PyPI Trusted Publisher Error

## The Problem

The error occurs because PyPI doesn't have a trusted publisher configured that matches the claims from GitHub Actions.

## The Solution

### 1. Update GitHub Actions Workflow ✅ DONE

The workflow has been updated to include an environment named `pypi`.

### 2. Configure PyPI Trusted Publisher

You need to configure a trusted publisher on PyPI with these **exact** values:

| Field | Value |
|-------|-------|
| **PyPI Project Name** | `tg-note` |
| **Owner** | `ArtyomZemlyak` |
| **Repository name** | `tg-note` |
| **Workflow name** | `publish-to-pypi.yml` |
| **Environment name** | `pypi` |

#### Steps:

1. **For a new package** (first time publishing):
   - Go to: https://pypi.org/manage/account/publishing/
   - Click "Add a pending publisher"
   - Fill in the values above

2. **For an existing package**:
   - Go to: https://pypi.org/manage/project/tg-note/settings/
   - Scroll to "Publishing" section
   - Click "Add a new publisher"
   - Fill in the values above

### 3. Create GitHub Environment

1. Go to: https://github.com/ArtyomZemlyak/tg-note/settings/environments
2. Click "New environment"
3. Name it: `pypi`
4. (Optional) Add protection rules for security

### 4. Test the Configuration

After completing steps 2 and 3, you can test by:

```bash
# Delete and recreate the tag
git tag -d v0.0.1
git push origin :refs/tags/v0.0.1
git tag v0.0.1
git push origin v0.0.1
```

Or create a new release through GitHub UI.

## Why This Happened

The original workflow didn't specify an environment, which is a best practice for PyPI publishing. The environment provides:
- Better security through GitHub environment protection rules
- Clear separation of deployment concerns
- Audit trail for deployments

## More Information

See the comprehensive guide at: `docs_site/deployment/pypi-trusted-publisher-setup.md`
