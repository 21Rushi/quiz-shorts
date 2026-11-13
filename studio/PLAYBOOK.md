# IamRushi Shorts — Daily Playbook

Channel: IamRushi (@I-mRushi). Goal: growth + YouTube Partner Program monetization.
Folder on Mac: ~/Downloads/IamRushi_Shorts  (engine/ = code, flow_clips/, final/, log.json)

## Schedule (from 2026-11-04)
Quizzes are automatic (GitHub Actions, schedule.json / questions.json). Claude does NOT make them.

| IST | Every day |
|---|---|
| 7:47 AM | Quiz #1 (automatic) |
| 1:47 PM | Quiz #2 (automatic) |
| 7:47 PM | Pre-made video slot (below) |
| Sun 8:47 PM | Weekly 40-question long video (automatic, weekly-challenge.yml) |

Pre-made video slot (7:47 PM IST):
- Mon, Wed, Fri: Facts Short made ONLY in Google Flow (3 realistic clips, one per fact) with Hindi voiceover, by the
  "IamRushi – Flow Facts (Mon/Wed/Fri)" scheduled task. Rushikesh did not like the photo version (2026-11-13): never
  post a photo or text-only Facts Short. If the Mac is off, he is notified to open it and run the task manually;
  GitHub Actions builds nothing for Facts on its own, so the slot waits for the Flow video.
- Sun: 1-min story, ALWAYS made in Google Flow (realistic). Topic = the "story" entry for that Sunday in studio/auto_shorts.json.
  Never a plain code-made story (src/build_auto.py skips story days). If the Mac is off, Rushikesh is notified to open
  it and run the "IamRushi – Sunday Flow story" scheduled task manually; that run uploads right away.
- Tue, Thu, Sat: no 7:47 PM Short.

## Formats
**Quiz** — engine.py spec type "quiz" (see engine/specs/*_quiz.json): q_en, q_hi, 4 options (en+hi), answer, fact_en, fact_hi. Reveal at 25s. Rotate categories: Space, Animals, India GK, Science, History, Geography, Tech, Human body.

**Facts (visual)** — planned in studio/auto_shorts.json (kind "facts": hook + 3 facts, 36s, en + hi captions, Hindi "vo" lines).
Built by `python src/build_auto.py --date YYYY-MM-DD --dir <folder>`:
- Always pass `--clips c1.mp4 c2.mp4 c3.mp4` (one 8-10s Google Flow clip per fact, in order). The hook is a
  montage of the clips; meta.json gets "synthetic": true (YouTube AI label). Flow clip prompt:
  "Photorealistic vertical cinematic shot: <scene that SHOWS the fact, with clear motion>. Dramatic lighting, slow
  camera move. No narration, no speech, no subtitles, no on-screen text, no people's faces close-up." (the Hindi voice
  and captions are added by the pipeline, so clips must be silent of speech). Omni 1.1 Flash, 9:16, 10s, x1 = 15
  credits each, 45 total.
- VOICEOVER: build_auto.py writes "voiceover" into meta.json from the "vo" lines; GitHub Actions (src/voiceover.py,
  edge-tts, hi-IN-MadhurNeural) speaks it over the music at upload time.
Topics rotate: Human body, Space, Animals, India, History, Money (Hindi), Ocean, Technology.

**Flow story** — ONE complete story in ONE Short (no parts). 6 clips x 10s, Google Flow model "Omni 1.1 Flash", 9:16, 720p, 10s, x1 (15 credits each, 90 total). If Omni voice is poor, use Veo 3.1 Fast 8s (20 credits) x 5.
Structure: 1 Hook (shocking question) → 2 Setup (key fact) → 3 Build → 4 Twist → 5 Climax → 6 Ending (real answer + "Follow for more").
Every clip prompt: "Photorealistic vertical cinematic shot: <scene>. The same deep, calm male Hindi documentary narrator speaks in clear Hindi: \"<line>\". Epic orchestral music. No people's faces close-up, no subtitles, no on-screen text."
Assemble: assemble.py spec.json out.mp4 clip1..clip6 (captions en + hi, tag pill, CTA).
Topic queue (alternate What if / History-mystery): What if the Moon disappeared?; Roopkund skeleton lake mystery; What if the Sun went out for a day?; Iron Pillar of Delhi that never rusts; What if you fell into a black hole?; How the Kohinoor left India; What if all ice melted?; Nalanda library fire.

## Google Flow credit budget (Rushikesh, 2026-11-13: about 1000 credits, Claude must manage them)
Weekly plan = 225 credits: 3 Flow Facts (Mon/Wed/Fri, 3 clips x 15 = 45 each) + 1 Sunday story (6 clips x 15 = 90).
Every Flow run must:
1. Read the credit balance shown in Google Flow BEFORE generating. If it cannot cover the whole video (45 Facts /
   90 story), generate nothing (no half-made videos) and tell him: balance, what is needed, and to top up or wait.
2. Spend carefully: Omni 1.1 Flash 10s x1 only; write a careful prompt first; regenerate at most ONE clip per video,
   and only if it is clearly unusable. Never use a dearer model or x2/x4 outputs unless he asks.
3. End the message to him with: "Flow credits: used <n>, left <m> (~<m/225, one decimal> weeks of videos)".
4. If the balance after the run is under 225, add: "⚠️ Flow credits low - less than one week left."

## Reach + monetization rules (YouTube policies)
1. Original value every time: own script, accurate facts (verify numbers with a web search), never reuse others' clips/music.
2. No repetitive mass-produced feel: vary topics, wording, colors/themes; never upload near-duplicates.
3. AI disclosure: Flow (realistic) videos → tick "Altered or synthetic content: Yes". Code-animated quiz/facts → No.
4. Not made for kids → "No, it's not made for kids".
5. Title ≤ 60 chars, hook first, Hindi + English mix, 2-3 hashtags incl. #shorts. Description: 2 lines + question + 3-5 hashtags. 5-8 tags.
6. No misleading/clickbait claims, no scary/violent gore, no real people, no copyrighted characters/music.
7. Retention: hook in first 2 seconds, Shorts under 60s, loop-friendly endings, ask a comment question.
8. Consistency: same times daily (7:47 AM, 1:47 PM, 7:47 PM IST), same branding (@I-mRushi, yellow pill).
9. Engagement: pin a comment with the question; reply to early comments.

## Output
Save finals to ~/Downloads/IamRushi_Shorts/final as YYYY-MM-DD_<type>_<slug>.mp4 (+ an upload copy under 10 MB) and a YYYY-MM-DD_upload.txt with title/description/tags/AI-label per video. Append to log.json {date, type, topic, title} and never repeat a topic in log.json.
Upload (automatic): push the evening video to the `premade` branch of github.com/21Rushi/quiz-shorts as
`<YYYY-MM-DD>/evening/video.mp4` (the <10 MB upload copy) + `meta.json`:
{"title","description","tags":[...],"synthetic": true for Flow (story or Flow Facts) / false for photo Facts,"language":"hi"|"en","type","topic",
 "title_language":"en","localizations":{"hi":{"title":"<Hindi title>","description":"<Hindi description>"}}}
English + Hindi viewers: "title"/"description" are ENGLISH (shown to US/Europe and other non-Hindi viewers);
"localizations.hi" holds the HINDI title/description (shown to viewers whose YouTube language is Hindi).
"language" = the spoken voice language (Hindi). Both titles ≤60 chars with a hook; both descriptions keep the
comment question, subscribe line and hashtags.
Force-push an orphan commit holding only today's and future dates (keeps the repo small). GitHub Actions
(daily-quiz.yml, 13:17 UTC = 6:47 PM IST, slot "premade") uploads it and YouTube publishes at 7:47 PM IST with
the AI label. To upload right away, dispatch: gh api -X POST repos/21Rushi/quiz-shorts/actions/workflows/daily-quiz.yml/dispatches
-f ref=main -f 'inputs[slot]=premade' -f 'inputs[date]=<YYYY-MM-DD>' -F 'inputs[dry_run]=false' -f 'inputs[privacy]=public'.
Must be pushed before 6:30 PM IST. If nothing is pushed, the 7:47 PM slot stays empty (both quizzes still post).
Also keep a copy in ~/Downloads/IamRushi_Shorts/final.

## Setup in a fresh session (cloud workspace)
1. Engine lives in the repo at studio/ (engine.py, assemble.py, PLAYBOOK.md); also mirrored in ~/Downloads/IamRushi_Shorts/engine. Copy to /home/claude/shorts.
2. Fonts: mkdir -p ~/fonts && cd ~/fonts && npm pack -s @expo-google-fonts/noto-sans-devanagari @expo-google-fonts/montserrat && for f in *.tgz; do tar xzf $f; done
3. Render: python3 engine.py spec.json out.mp4   (preview frames: python3 engine.py spec.json prefix 2 10 26)
4. Upload copy <10MB: ffmpeg -i in.mp4 -c:v libx264 -preset slow -b:v 2600k -maxrate 3000k -bufsize 5000k -c:a aac -b:a 128k -movflags +faststart upload_x.mp4
5. Commit finals to ~/Downloads/IamRushi_Shorts/final via device_commit_files.
