# Work Log

This document records the implementation work completed for Posting Bot. Add new entries at the top of the dated log so that the most recent work remains easy to find.

## Project Summary

Posting Bot is a Telegram bot that uses the Gemini API to create and revise Korean Markdown articles. After the user approves a draft, the bot publishes it to the `_posts/` directory of a GitHub-hosted Jekyll/Chirpy blog.

## 2026-09-27 — Initial Implementation and Docker Deployment

### Application workflow

- Implemented a Telegram bot using `python-telegram-bot` and long polling.
- Added `/start`, `/suggest`, `/write`, `/revise`, `/publish`, and `/cancel` commands.
- Restricted command handling to the Telegram user configured by `ALLOWED_TELEGRAM_USER_ID`.
- Stored the active draft, title, categories, and tags in Telegram `user_data`.
- Kept the existing draft when generation, revision, or publishing fails.
- Moved blocking Gemini and GitHub HTTP requests to worker threads with `asyncio.to_thread`, preventing them from blocking Telegram's async event loop.

### Gemini integration

- Integrated the Gemini `generateContent` REST API with `httpx`.
- Added prompts for Korean topic suggestions, article creation, and feedback-based revision.
- Defined a structured model response containing a generated title, up to two categories, up to five tags, and a Markdown body.
- Added response parsing with fallback values for malformed or incomplete model output.
- Added a configurable `GEMINI_MODEL`, defaulting to `gemini-2.5-flash`.
- Limited Telegram previews to avoid exceeding message-size limits.

### GitHub and Jekyll publishing

- Integrated the GitHub Contents API using a fine-grained personal access token.
- Generated Chirpy-compatible Jekyll front matter with layout, title, date, categories, and tags.
- Used the `Asia/Seoul` timezone for post timestamps.
- Published posts under `_posts/YYYY-MM-DD-HHMMSS.md`.
- Base64-encoded post content as required by the GitHub Contents API.
- Returned the created GitHub file URL to the Telegram user after publishing.

### Configuration and secret handling

- Added `.env.example` documenting all required configuration variables.
- Added `.gitignore` rules for `.env`, virtual environments, Python cache files, and legacy secret files.
- Added `.dockerignore` rules so secrets, Git metadata, development files, and documentation are excluded from the Docker build context.
- Configured Compose to inject `.env` entries as runtime environment variables. The `.env` file itself is not copied into the image.

Required variables:

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Authenticates Gemini API requests |
| `TELEGRAM_BOT_TOKEN` | Authenticates the Telegram bot |
| `GITHUB_TOKEN` | Authorizes GitHub Contents API writes |
| `GITHUB_REPOSITORY` | Selects the destination repository as `owner/repository` |
| `GEMINI_MODEL` | Selects the Gemini model |
| `ALLOWED_TELEGRAM_USER_ID` | Restricts bot access to one Telegram user |

### Containerization

- Added a `python:3.12-slim` Docker image definition.
- Installed pinned Python dependencies from `requirements.txt`.
- Configured unbuffered Python output and disabled `.pyc` generation.
- Created and used an unprivileged `postingbot` system user inside the container.
- Added Docker Compose configuration with `.env` injection, an init process, and the `unless-stopped` restart policy.
- Used a multi-architecture upstream base image, allowing native builds on AMD64 Ubuntu without source changes. Cross-building from another architecture can use `docker buildx build --platform linux/amd64`.

### Documentation

- Added setup instructions for a local Python virtual environment.
- Added Docker Compose build, run, log, and shutdown commands.
- Documented the Telegram command workflow and generated Jekyll front matter.

### Verification

- Successfully built the `postingbot:local` image with Docker Compose.
- Successfully started the `postingbot-postingbot-1` container.
- Confirmed the container remained running with zero restarts during the check.
- Confirmed that all six configuration variables were present inside the container without printing their values.
- Observed no startup errors in the initial container logs.

### Known limitations

- Draft state is stored only in process memory and is lost when the bot restarts.
- Access is limited to a single configured Telegram user.
- Publishing always targets the repository's default branch through the GitHub Contents API.
- There are currently no automated tests, health check, persistent datastore, or CI pipeline.
- External API failures are reported with user-friendly Telegram messages, while detailed errors are written to container output.

## Files Introduced

| File | Responsibility |
| --- | --- |
| `bot.py` | Telegram commands, Gemini generation, draft state, and GitHub publishing |
| `requirements.txt` | Pinned Python runtime dependencies |
| `.env.example` | Configuration template without real secrets |
| `.gitignore` | Local secret and generated-file exclusions |
| `.dockerignore` | Docker build-context exclusions |
| `Dockerfile` | Production container image definition |
| `compose.yaml` | Local/server container orchestration and environment injection |
| `README.md` | Setup, operation, and usage instructions |

