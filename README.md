# Daily Quiz Shorts 🧠

Posts **two** general-knowledge quiz Shorts to YouTube every day (7:47 AM & 7:47 PM IST), fully automatic.
See **PLAN.md** for the 21-day bilingual (English + Hindi) content calendar and the growth checklist.

- 1080x1920 vertical Short, ~31 seconds
- Question + 4 options animate in, 25-second countdown ring, ticking in the last 5 seconds
- **Answer revealed at 0:25** with a chime, the correct option turns green, then a "Did you know?" fact
- Original background music generated in code (no copyright claims). Drop your own
  royalty-free `.mp3` files into `assets/music/` to use those instead.
- 371 questions written and checked — over a year of daily posts. Edit `questions.json` anytime.
- `schedule.json`: 42 hand-written bilingual questions for 28 Oct – 17 Nov 2026, tied to festivals and national days. After that it falls back to `questions.json`.
- **Every Sunday 8:47 PM IST:** a ~10-minute, 40-question "Weekly GK Challenge" (16:9) with chapters and a custom thumbnail — builds watch hours, the second monetisation path.
- Runs on GitHub Actions at **7:47 AM and 7:47 PM IST**. Your laptop can stay off.

## One-time setup (~20 minutes)

### 1. Put this folder in a GitHub repo
```bash
cd quiz-shorts
git init && git add . && git commit -m "Daily quiz shorts"
gh repo create quiz-shorts --private --source . --push
```

### 2. Create Google API credentials
1. Go to https://console.cloud.google.com → create a project (e.g. `quiz-shorts`).
2. **APIs & Services → Library** → enable **YouTube Data API v3**.
3. **APIs & Services → OAuth consent screen** → User type **External** → fill app name + your email.
   Add your own Gmail as a test user.
4. **Important:** on the consent screen page click **Publish app** (status: *In production*).
   In *Testing* mode Google expires the refresh token after 7 days and the automation will stop.
   You'll see an "unverified app" warning when you sign in — that's fine for your own channel
   (click *Advanced → Go to app*).
5. **Credentials → Create credentials → OAuth client ID → Desktop app**. Download the JSON,
   rename it `client_secret.json`, put it in `src/` (it's git-ignored).

### 3. Get your refresh token (on your own computer)
```bash
pip install google-auth-oauthlib
python src/get_refresh_token.py
```
Sign in with the account that owns the channel and pick the channel. It prints three values.

### 4. Add GitHub secrets
Repo → **Settings → Secrets and variables → Actions → New repository secret**:
`YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`

### 5. Test it
Repo → **Actions → Daily Quiz Shorts (2 per day) → Run workflow**
- Pick a slot, tick **dry_run** first: it renders the video and attaches it to the run so you can watch it.
  Put a future date (e.g. `2026-11-08`) in the date box to preview that day's Diwali quiz.
- Then run it without dry_run — the Short should appear on your channel.

From then on it posts by itself every day.

## If the first upload shows "Private (locked)"
Google may lock videos uploaded through a brand-new, un-audited API project to private.
If that happens, submit the free **YouTube API Services audit form**
(https://support.google.com/youtube/contact/yt_api_form). Until it's approved you can set
`"privacy": "private"` in `config.json` and switch videos to public by hand.

## Customising
| What | Where |
|---|---|
| Posting times | the two `cron` lines in `.github/workflows/daily-quiz.yml` (UTC) — also update the matching check in the same file |
| Daily bilingual questions | `schedule.json` — one entry per date + slot (`morning`/`evening`), with `_hi` Hindi fields and topic `tags` |
| Title / description / tags | `config.json` |
| First day of the series | `start_date` in `config.json` (question 1 posts that day) |
| Questions | `questions.json` — `a` = correct answer, `w` = 3 wrong answers, `f` = fun fact. Options are shuffled automatically. |
| Your own music | put `.mp3` / `.m4a` / `.wav` files in `assets/music/` |
| Colours, hook lines, timings | top of `src/make_video.py` (`THEMES`, `HOOKS`, `REVEAL_AT`) |

Render a video locally: `python src/daily.py --slot evening --date 2026-11-08 --dry-run` or `python src/make_video.py --id 42 --out out/test.mp4`
(needs `ffmpeg` installed).

Quota: one upload uses ~1,600 of the default 10,000 daily API units, so 2/day (~3,200) is well within limits.

Fonts: Poppins and Noto Sans Devanagari (SIL Open Font License).

## Pre-made Shorts (Google Flow stories / Facts)
The evening slot can post a pre-made video instead of the quiz. Claude pushes it to the `premade`
branch as `<YYYY-MM-DD>/<slot>/video.mp4` + `meta.json` (title, description, tags, `synthetic`, `language`).
`src/post_premade.py` uploads it (with YouTube's AI label when `synthetic` is true); if nothing is
there for that date and slot, the workflow posts the quiz as before, so the channel never goes quiet.
