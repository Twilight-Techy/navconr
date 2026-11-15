# Authentication

## Access tokens

Access tokens expire after 15 minutes. Clients send them in the Authorization header.

## Refresh tokens

Refresh tokens expire after 30 days. Rotation replaces the previous refresh token on every successful refresh.

For emergency invalidation, see [session revocation](operations.md#revocation).

## Failed sign-in

After five consecutive failed sign-in attempts, the account is locked for ten minutes.
