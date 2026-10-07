# Sewa Setu — Old Age Pension Portal

Handover copy. Vendor maintenance contract ended 31/01/2026.

## Running

```
docker compose up --build
```

- Portal: http://localhost:8000
- SMS gateway console (simulated telecom): http://localhost:8000/__gateway/ —
  "sent" OTPs appear here once delivered. The gateway runs on the internal
  network and is served through the portal, so only one port is exposed.
- Database: Postgres, loaded from `seed/seed.sql` on first boot
- Operations and deployment notes: see `OPERATIONS.md`

## Verification

Run the focused regression tests inside the built application image:

```
docker compose exec app python -m unittest discover -s /app/tests
```

Production server logs (Jan–Jun 2026) are provided in `logs/`.

Listen to `dc-briefing.mp3` first (the DC's briefing), then read `BRIEF.md`.
