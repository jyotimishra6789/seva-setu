# Sewa Setu operations

## Configuration

Set `SEWASETU_SECRET_KEY` and `SEWASETU_ADMIN_PASSWORD` in the deployment
environment, along with `SEWASETU_DB_PASSWORD`. Do not put these values in
`app/config/app.ini` or commit a `.env` file. The application deadline is
interpreted in `Asia/Kolkata`, not in the container's timezone.

The document upload limit is 5 MB. The active-mobile uniqueness constraint is
enforced by the database, so keep the partial unique index from `schema.sql`
applied during migrations.

For an existing database, run the schema migration before enabling the new
password-hash migration:

```sql
ALTER TABLE portal_users ALTER COLUMN password_hash TYPE TEXT;
```

## Deemed approval

The scheduler runs `app/scripts/deemed_approval.py` at 02:00 each day. It reads
the same `app/config/app.ini` file as the web process and marks untouched
pending applications older than the configured SLA as `DEEMED_APPROVED`.

Check `/var/log/sewasetu/cron.log` and the database query below after deployment:

```sql
SELECT status, count(*) FROM applications GROUP BY status;
```

The `applications_status_submitted_idx` index supports both the nightly job and
the pending dashboard. Existing records are not deleted by corrections or
withdrawals; withdrawn rows remain available for audit.

The web process uses a bounded PostgreSQL connection pool. Set
`SEWASETU_DB_POOL_MAX` if the deployment has a different database connection
budget; keep the total across web workers and scheduled jobs below PostgreSQL's
`max_connections`.

## Citizen support

Citizens can log in to the status portal, correct a pending application, or
withdraw it before staff decision. A correction does not reset `submitted_at`
and therefore does not reset the statutory processing clock.

The SMS gateway console is intentionally not exposed through the public portal.
