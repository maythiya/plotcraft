# Run with Docker

1. Copy `.env.example` to `.env` and edit secrets.

2. From the `web/` directory run:

```bash
docker compose up --build
```

This starts a MySQL service and the Django web service bound to port 8000.

Notes:
- Ensure `manage.py` is present at the project root so the container can run migrations.
- Adjust `DB_HOST` in `.env` to `db` (the compose service name) if needed.
