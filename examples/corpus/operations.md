# Operations

## Revocation

Revoke a session by deleting its Redis session key. Access-token validation checks that session key on every request.

## Recovery

Backups run every six hours. Restore the latest verified backup before replaying the write-ahead log.

## Deployment

Deploy to a canary instance first. Promote it after the health checks pass for ten minutes.
