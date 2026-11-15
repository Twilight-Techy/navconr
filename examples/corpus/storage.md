# Storage

## Connection pool

The PostgreSQL connection pool has a maximum of 20 connections per worker.

## Transactions

Use serializable transactions for balance transfers. Retry serialization failures at most three times.

## Cache

Cache entries expire after 120 seconds. A successful write invalidates the corresponding cache key.
