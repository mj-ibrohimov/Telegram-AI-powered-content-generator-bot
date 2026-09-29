# German Learning Telegram Content Bot

A human-in-the-loop Telegram bot that generates educational German-learning content on a schedule, sends every draft privately to the channel owner for review, and only publishes to the channel after explicit approval. The AI never publishes anything on its own.

## What it does

- Generates a German-learning post several times a day (default: 08:00, 12:00, 16:00, 20:00, 22:00, Asia/Tashkent).
- Sends every draft to the configured admin(s) in a private chat with three buttons: **Approve & Publish**, **Improve**, **Discard & Regenerate**.
- Publishes to the channel only when an admin presses Approve.
- Lets the admin rewrite a draft with a free-text instruction ("make it shorter", "add a quiz", etc.).
- Keeps a full history of drafts, revisions, and publications in the database.
- Avoids repeating recent topics/vocabulary via category rotation + duplicate detection (exact match + TF-IDF similarity).
- Rotates through content categories (daily phrases, vocabulary, grammar, workplace German, mistakes, quizzes, culture, news, media recommendations, challenges, migration/life-in-Germany, and occasional soft marketing for the owner's German classes).

## Architecture

```
app/
├── bot/            # aiogram handlers, keyboards, FSM states, auth middleware
├── ai/             # LLM provider abstraction (OpenAI-compatible) + prompts
├── content/         # category strategy, generator, validator, duplicate detector
├── database/        # SQLAlchemy models + repositories
├── scheduler/        # APScheduler cron jobs with idempotency
├── news/            # optional news retrieval abstraction
├── services/         # draft / publication / improvement orchestration
├── config.py         # pydantic-settings configuration
└── main.py            # wiring + health check server
```

State machine for every draft:

```
GENERATED -> WAITING_APPROVAL -> (approve -> PUBLISHED)
                               -> (discard -> DISCARDED, new draft generated)
                               -> (improve -> IMPROVING -> new revision -> WAITING_APPROVAL)
```

### Generation pipeline

Every scheduled or manual generation goes through this pipeline before a draft ever reaches the owner:

```
Content Strategy (pick category)
    -> AI Generation (generate_post)
    -> Mechanical Validation (length, balanced HTML)
    -> AI Quality Review (grammar, naturalness, translation accuracy,
       meaning preservation, CEFR fit, usefulness, category adherence,
       factual accuracy -- structured JSON judge, separate LLM call)
         -> if only minor issues: accept
         -> if major issues: targeted fix (improve_post with the specific
            problem as instruction, not a full restart), then re-review
            -- up to 2 rounds
         -> if still failing: full regeneration (next outer attempt)
    -> Duplicate Detection (exact + TF-IDF similarity)
    -> Draft saved, sent to owner for approval
```

The AI quality review is a required gate: if the review call itself fails (timeout, malformed output), that generation attempt is treated as failed and retried like any other failure -- it never silently skips validation. Bounded by `MAX_GENERATION_ATTEMPTS` as before, so a persistently broken model still fails loudly with `/generate` guidance rather than looping forever. The Telegram approval workflow, scheduler, database schema, and deployment setup are unchanged by this -- the quality review happens entirely inside `ContentGenerator`, before anything is shown to the owner. The AI still never publishes anything.

## 1. Create the Telegram bot (BotFather)

1. Open Telegram and start a chat with **@BotFather**.
2. Send `/newbot` and follow the prompts to choose a name and username.
3. BotFather gives you a token like `123456789:AAH...` — copy it into `TELEGRAM_BOT_TOKEN` in `.env`. Never commit this token or put it in source code.

## 2. Add the bot to your channel

1. Open your Telegram channel → **Administrators** → **Add Admin**.
2. Add your bot.
3. Grant at minimum:
   - **Post Messages** (required)
   - **Edit Messages** (recommended, used if you later add message editing)
   - **Delete Messages** (optional, for manual moderation)
4. You do not need to grant "Add new admins" or other sensitive permissions.

## 3. Find your channel ID

Easiest ways:
- If the channel is public, use its `@username` directly as `TELEGRAM_CHANNEL_ID` (e.g. `@my_german_channel`).
- If it's private, forward a message from the channel to **@userinfobot** or **@JsonDumpBot**, or temporarily add `@RawDataBot` to the channel — the numeric ID looks like `-1001234567890`.

## 4. Find your own Telegram user ID (to become admin)

Message **@userinfobot** — it replies with your numeric Telegram user ID. Put it in `ADMIN_TELEGRAM_IDS`. Multiple admins are comma-separated:

```env
ADMIN_TELEGRAM_IDS=111111111,222222222
```

## 5. Configure `.env`

```bash
cp .env.example .env
```

Fill in at least:

```env
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHANNEL_ID=@your_channel_or_-100...
ADMIN_TELEGRAM_IDS=your_telegram_user_id
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/german_bot
LLM_PROVIDER=codecraft
LLM_API_KEY=your-codecraftapi-key
LLM_MODEL=gpt-4o-mini
```

If `TELEGRAM_CHANNEL_ID` is a numeric ID or the channel is private, also set `TELEGRAM_CHANNEL_LINK` to a public/invite link (e.g. `https://t.me/+AbCdEf12345`) — this is what gets appended as a clickable footer on every published post. For an `@username` channel it's derived automatically and can be left blank.

`.env` is gitignored — never commit real credentials.

### LLM provider: codecraftapi.com + optional OpenAI backup

The bot supports two independent LLM slots:

- **Primary** (`LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`) — what's used for every generation by default.
- **Fallback** (`LLM_FALLBACK_ENABLED`, `LLM_FALLBACK_PROVIDER`, `LLM_FALLBACK_API_KEY`, `LLM_FALLBACK_MODEL`, `LLM_FALLBACK_BASE_URL`) — only used automatically if the primary call fails (e.g. rate limit, outage). Disabled by default.

To use codecraftapi.com as primary and keep your original OpenAI key as a safety net:

```env
LLM_PROVIDER=codecraft
LLM_API_KEY=your-codecraftapi-key
LLM_MODEL=gpt-4o-mini          # confirm this is a real model on your account — see note below
LLM_BASE_URL=                  # optional, defaults to https://codecraftapi.com/v1

LLM_FALLBACK_ENABLED=true
LLM_FALLBACK_PROVIDER=openai
LLM_FALLBACK_API_KEY=your-openai-key
LLM_FALLBACK_MODEL=gpt-4o-mini
```

**⚠️ Model name not verified.** codecraftapi.com's own docs (`/docs/chat-completions`) only show `claude-opus-4.8` as an example model ID — `gpt-4o-mini` is not confirmed to be one of their available models. Their `/models` catalog page (33 models) requires JavaScript to render, so it couldn't be checked automatically. **Before going live**, check `https://codecraftapi.com/models` (or `GET https://codecraftapi.com/v1/models` with your API key) and set `LLM_MODEL` to the exact string they list — otherwise every generation will fail with a model-not-found error from their API.

codecraftapi.com's chat completions API is otherwise a drop-in match for OpenAI's format (confirmed from their docs: same request/response JSON, `Authorization: Bearer <key>` auth, `/chat/completions` path), so no extra code was needed beyond pointing the base URL at it. One difference: codecraftapi.com does not offer an image-generation endpoint (only image *input*/vision), so `/rasm` will fail with a clear message if `LLM_PROVIDER=codecraft` and no fallback is enabled — enable the OpenAI fallback above (or temporarily switch `LLM_PROVIDER=openai`) to use `/rasm`.

## 6. Run locally (without Docker)

Requires Python 3.12+.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For local development without Postgres, use SQLite:

```env
DATABASE_URL=sqlite+aiosqlite:///./german_bot.db
```

Apply migrations:

```bash
alembic upgrade head
```

Run the bot:

```bash
python -m app.main
```

## 7. Run PostgreSQL locally (optional, for closer-to-prod testing)

```bash
docker run -d --name german-bot-postgres \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=german_bot \
  -p 5432:5432 postgres:16-alpine
```

Then set `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/german_bot` in `.env` and run `alembic upgrade head`.

## 8. Run with Docker Compose (recommended for deployment)

```bash
docker compose up -d --build
```

This starts both `postgres` and `bot` containers. The bot runs `alembic`-managed schema via `init_db()` on startup (tables are created automatically for convenience; for production schema changes, run `docker compose exec bot alembic upgrade head`).

Health check: `curl http://localhost:8080/health`

## 9. How scheduling works

- Uses APScheduler `CronTrigger` with explicit timezone (`TIMEZONE`, default `Asia/Tashkent`) — never server local time.
- `POST_TIMES` (default `08:00,12:00,16:00,20:00,22:00`) configures generation times.
- Each scheduled slot has an idempotency key `YYYY-MM-DD_HH:MM` stored in `scheduler_runs`. If the app restarts after a slot was already successfully processed, it will not regenerate for that slot.

## 10. Test generation manually

The bot's UI and all commands are in Uzbek. Typing `/` in the chat with the bot shows the full command menu (registered via `setMyCommands`). Inside Telegram, message your bot (as an authorized admin):

```
/yarat
/yarat workplace
/yarat A2 grammar
/yarat quiz
```

The bot generates a draft immediately and sends it with the approval buttons.

You can also skip categories entirely and just describe what you want:

```
/erkin
```
then reply with any free-text prompt, e.g. "Berlindagi jamoat transporti haqida A2 darajasida post yoz" — the bot generates a post from that exact instruction using the same approve/improve/discard flow.

To generate a standalone AI image (not attached to a post):

```
/rasm
```
then reply with an image description, e.g. "Oktoberfest bayrami, chizilgan uslubda".

## 11. Deploy to a cloud server

1. Provision a small VM (1 vCPU / 1GB RAM is enough) with Docker installed.
2. Copy the repository and `.env` (with real secrets) to the server — never commit `.env`.
3. Run:
   ```bash
   docker compose up -d --build
   ```
4. Point your process monitor / uptime checker at `GET /health` on port 8080.
5. To update: `git pull && docker compose up -d --build`.

## 12. Troubleshooting

| Symptom | Likely cause |
|---|---|
| Bot doesn't respond at all | Wrong `TELEGRAM_BOT_TOKEN`, or bot process crashed — check logs |
| "Unauthorized" replies to everything | Your Telegram user ID isn't in `ADMIN_TELEGRAM_IDS` |
| Publish fails with Telegram API error | Bot isn't an admin of the channel, or lacks "Post Messages" permission |
| Draft never arrives at scheduled time | Check `TIMEZONE`/`POST_TIMES`, check `scheduler_runs` table for `FAILED` status and `error_message` |
| "To'g'ri post yarata olmadim" (couldn't generate) | LLM API key invalid/rate-limited, or content kept failing validation/duplicate checks — check logs, try `/yarat` manually |
| Same topics repeating | Lower `DUPLICATE_SIMILARITY_THRESHOLD`, or review `content_history` table |

## Running tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## Example generated post

```
📝 NEW GERMAN LEARNING POST

Scheduled slot: 20:00
Category: Workplace German
CEFR level: Mixed

━━━━━━━━━━━━━━━━━━

💼 Deutsch im Büro

"Ich wollte kurz nachfragen..."

Meaning: I just wanted to ask/follow up...

Useful when writing a polite professional message to a colleague or manager.

Beispiel:
"Ich wollte kurz nachfragen, ob Sie meine E-Mail erhalten haben."

━━━━━━━━━━━━━━━━━━

Status: Waiting for approval
```

## Extensibility

The codebase is structured so the following can be added later without rewrites: subscriber analytics, best-performing-content tracking, automatic category weight optimization, image generation, vocabulary cards, audio/pronunciation, lead generation, and CRM integration. None of these are implemented — only the architecture (provider abstractions, repository pattern, service layer) supports adding them cleanly.
