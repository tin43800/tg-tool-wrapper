---
name: telegram-deployer
description: Package any Python tool/function as a Telegram bot and deploy it via Docker. Use when the user says "部署到 telegram", "打包成 telegram bot", "wrap as telegram bot", "把這個工具丟上 telegram", or any phrasing about exposing a local Python script/function through a Telegram interface. Detects the OS, verifies Docker, scaffolds a project from templates, and starts the bot as a background container.
---

# telegram-deployer

把一個本地 Python 工具（函式或 CLI 腳本）打包成 Telegram bot，並用 Docker 在使用者機器上跑起來。

底層使用 [`tg-tool-wrapper`](https://github.com/tin43800/tg-tool-wrapper) 套件作為 bot 框架。

## When to invoke

The user expresses intent to expose a Python tool through Telegram. Examples:
- 「幫我把 `parse_salary.py` 部署到 telegram」
- 「我想把這個 OCR 工具做成 telegram bot」
- "Wrap this script as a telegram bot"
- 「打包成 telegram bot 並啟動」

If the user mentions a specific file path, treat it as the target tool. Otherwise ask which tool to wrap.

## Workflow

Follow these steps **in order**. Do not skip the environment check or secret-collection steps.

### Step 1 — Confirm intent and collect requirements

Ask the user (one message, batched):

1. **Target tool**: Path to the Python file containing the function/logic to expose (e.g. `D:/Claude/tools_salary/parse_salary.py`)
2. **Input type**: What does it accept?
   - `photo` — user sends an image, bot processes it (e.g. OCR)
   - `document` — user sends a file
   - `text` — user sends a text command
   - `command` — only respond to `/somecommand` style invocations
3. **Bot display name**: short identifier used for output dir + docker service name (e.g. `salary-bot`). Lowercase, hyphens OK.
4. **Output directory**: where to scaffold. Default: `./telegram-bots/<bot-name>/`

If the user already pointed at a file, read it first with `Read` and propose sensible defaults so they only have to confirm.

### Step 2 — Verify environment

Run these in parallel via Bash:

```bash
docker --version
docker compose version
python --version
```

Detect OS via `uname -s` (or `$env:OS` on Windows). If Docker is missing or daemon not running:

- **macOS / Windows**: tell user to install Docker Desktop from <https://www.docker.com/products/docker-desktop> and start it
- **Linux**: `curl -fsSL https://get.docker.com | sh && sudo systemctl start docker`

**Halt and do not proceed** until Docker is available.

### Step 3 — Inspect the target tool

`Read` the target file. Identify:

- The main callable function (look for one taking image path / text / file path that matches the chosen input type)
- Required imports
- Environment variables it reads (`os.environ[...]` / `os.getenv(...)`)
- External files it needs (credentials, configs)

Present a summary to the user:
> "I'll wrap `parse_salary_image()` from `gemini_ocr.py`. It needs these env vars: `GEMINI_API_KEY`, `SHEET_ID`, … and these companion files: `auth.py`, `credentials.json`. Confirm?"

### Step 4 — Collect secrets

Ask for, in one batched question:

1. **Telegram bot token** (from @BotFather)
2. **All env vars** the tool needs (read from existing `.env` if present in target dir — use `Read` to load it, then ask user to confirm/edit values)
3. **Companion files** that should be copied into the Docker image (e.g. Google credentials JSON)

⚠️ Never log or echo the token back. Just confirm "got it".

### Step 5 — Scaffold the project

Templates live next to this `SKILL.md` in `templates/`. Render each template by substituting placeholders, then write to the output directory.

Placeholders (Python `str.format` style with double braces escaped):
- `{{BOT_NAME}}` — bot display name from Step 1
- `{{HANDLER_TYPE}}` — one of: `photo` / `document` / `text` / `command`
- `{{USER_MODULE}}` — Python module name of the user's tool (filename without `.py`)
- `{{USER_FUNCTION}}` — function name to call
- `{{COMMAND_NAME}}` — only if HANDLER_TYPE is `command`
- `{{EXTRA_DEPS}}` — newline-separated pip dependencies extracted from user's tool

Files to write into output dir:

| Template | Output path | Notes |
|---|---|---|
| `templates/bot.py.template` | `bot.py` | Entry point — imports user's function + wraps with tg-tool-wrapper |
| `templates/Dockerfile.template` | `Dockerfile` | Python 3.12-slim base |
| `templates/docker-compose.yml.template` | `docker-compose.yml` | Single service, named volume for `telegram_owner.json` |
| `templates/requirements.txt.template` | `requirements.txt` | `tg-tool-wrapper` + user's deps |
| `templates/.env.example.template` | `.env.example` | Placeholder values |
| `templates/.dockerignore` | `.dockerignore` | Copy as-is |

Also:
- Copy user's tool file(s) into output dir's `app/` subfolder
- Copy companion files (credentials etc) the user listed in Step 4
- Write the actual `.env` (with real secrets) — show user the file path and remind them to keep it out of git

### Step 6 — Show plan, request approval

Print a tree of generated files and the docker command that will run:

```
telegram-bots/salary-bot/
├── Dockerfile
├── docker-compose.yml
├── bot.py
├── requirements.txt
├── .env                  (gitignored, contains your token)
├── .env.example
├── .dockerignore
└── app/
    ├── parse_salary.py   (your tool, copied in)
    ├── gemini_ocr.py
    ├── auth.py
    └── credentials.json  (copied per your selection)

Will run: docker compose up -d --build
```

**Wait for user to say "go" or equivalent before Step 7.**

### Step 7 — Build and start

```bash
cd <output-dir>
docker compose up -d --build
```

Stream a brief log tail (`docker compose logs --tail 20`) to confirm it started without error.

### Step 8 — Verify and instruct

1. Ping the bot via HTTP to confirm the token works:
   ```bash
   curl -s "https://api.telegram.org/bot<TOKEN>/getMe"
   ```
   (Read token from `.env`, never echo it.)

2. If response has `"ok": true`, tell the user:
   > "✅ Bot is live as @<bot_username>. Open Telegram, search for that username, send `/start`. You'll be auto-registered as owner. Send a {{input_type}} to test."

3. Show how to manage the container:
   - `docker compose logs -f` — tail logs
   - `docker compose down` — stop
   - `docker compose up -d` — restart
   - Delete `telegram_owner.json` (in the named volume `<bot-name>_owner`) to reset owner

## Important notes

- **Owner lock is automatic** — the first user to message the bot becomes the only allowed user. If the user wants explicit owner ID, pass `OWNER_ID` env var (the generated `bot.py` will respect it if set).
- **Don't commit `.env`** — it's in `.gitignore` of the generated project.
- **`tg-tool-wrapper` install**: requirements.txt pins it from GitHub. If the user has it locally, they can swap to `pip install -e <local-path>` in the Dockerfile during dev.
- **Truststore is already integrated** via `tg-tool-wrapper` — Avast / Zscaler / corporate SSL interception works without extra setup.
- **Cross-platform paths**: use forward slashes in docker-compose volume bindings. Use `pathlib.Path` in `bot.py`.

## Failure modes

- **Docker daemon not running**: halt at Step 2 with platform-specific start command.
- **Port conflict**: not applicable (bot uses long-polling outbound, no inbound port).
- **Bad token**: Step 8's `getMe` returns `"ok": false` — show user the response, ask them to regenerate via @BotFather.
- **Function signature mismatch**: if user's function doesn't fit handler signature, propose adapter code rather than failing — wrap in a lambda or small adapter function inside `bot.py`.
