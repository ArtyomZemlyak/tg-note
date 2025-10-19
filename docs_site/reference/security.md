# Security Best Practices

This section outlines security practices for running tg-note in production.

## Secrets and Credentials

- Store tokens encrypted at rest; do not commit secrets to git
- Restrict file permissions for keys in `./data` (use mode `600`)
- Prefer per-user tokens over global tokens; scope minimally

## Network and Services

- Limit exposed ports; run services behind a reverse proxy
- Keep dependencies up to date; patch regularly

## Data Protection

- Back up the encryption key at `./data/.credentials_key` securely
- Rotate credentials on compromise or staff changes

## Incident Response

- Revoke leaked tokens immediately
- Audit logs for suspicious git operations

## Related

- [Git Credentials Management](../user-guide/git-credentials.md)
- [Troubleshooting](troubleshooting.md)
