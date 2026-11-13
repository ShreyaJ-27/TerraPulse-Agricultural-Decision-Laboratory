# TerraPulse integration preview

The integration branch uses the existing TerraPulse Vercel project on Hobby and the
`integration-terrapulse-full-20261113` database branch in the TerraPulse-Integration Neon Free project.
The Vite app and FastAPI function share an origin on Vercel. Local development can point Vite at a separate
API with `VITE_API_BASE_URL`. Set `CORS_ORIGINS` to a JSON array of exact origins when using separate hosts.

Set `DATABASE_URL` in the Vercel dashboard as a sensitive Preview variable scoped to
`integration/terrapulse-full-20261113`. Use the integration database branch and the
`terrapulse` database with SSL required. Use its direct connection for migrations and its pooled
connection for the deployed API. Apply migrations with `python -m alembic upgrade head` and compare
the live schema with `python -m alembic check`. Use a disposable integration database for the
opt-in `TERRAPULSE_RUN_DB_TESTS=1` test, which exercises real PostgreSQL with a fake Telegram transport.

The deployed API requires an unguessable browser workspace key for private farm routes and
stores its digest. Clearing the browser’s site data removes access to that workspace. The
browser-local workspace at `/offline` retains existing local plans. The connected workspace
stores its farm and plot data in PostgreSQL.

## Telegram worker

Verify the bot identity and that the pilot recipient has agreed to receive messages. Store
`TELEGRAM_BOT_TOKEN` in the worker environment. Set `TELEGRAM_BOT_USERNAME` and
`TERRAPULSE_TELEGRAM_ENABLED=1` in the API environment only when linking is available.
Set `TERRAPULSE_TELEGRAM_ENABLED=1` in the worker environment before running it with `--live`.
The bot token is needed by the worker only.

On an existing computer that stays online during the pilot, use Windows Task Scheduler or
the system service manager to run one copy of the polling worker at startup and restart it
on failure. Use the same integration database as the API. The command is
`python -m app.services.farmer_alerts.cli --live --interval 600`. A scheduled
`--once --live` run on the same computer is also supported. Each cycle polls for consent and
subscription updates, evaluates due events and delivers eligible outbox rows. For a local dry run,
use `python -m app.services.farmer_alerts.cli --once` with the integration database.
Dry runs evaluate events and can populate the outbox, with no Telegram polling or sends.

Vercel Hobby cron targets production and each job runs at most once per day with hourly
precision. GitHub Actions schedules run from the default branch. The preview has no cloud
scheduler, and a self-hosted worker can only run while its computer is online.

After the consenting recipient presses Start, add a plot with an eligible recorded planting
date and run the worker outside quiet hours. Verify `telegram_deliveries.status = 'sent'` and
its `telegram_message_id` for that test subscription. Use `/stop` to unsubscribe.
