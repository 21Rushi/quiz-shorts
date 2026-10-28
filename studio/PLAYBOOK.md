# IamRushi Shorts — Daily Playbook

Channel: IamRushi (@I-mRushi). Goal: growth + YouTube Partner Program monetization.
Folder on Mac: ~/Downloads/IamRushi_Shorts  (engine/ = code, flow_clips/, final/, log.json)

## Schedule (2 Shorts every day, alternating A/B)
Day index = days since 2026-10-30. Even = Day A, odd = Day B.

| | Day A | Day B |
|---|---|---|
| 7:47 AM IST | Quiz — automatic by GitHub Actions (repo 21Rushi/quiz-shorts, schedule.json / questions.json). Claude does NOT make it. | same |
| 7:47 PM IST | Facts (30-36s, code, 0 credits) | Flow story (60s, Google Flow, ~90 credits) |

## Formats
**Quiz** — engine.py spec type "quiz" (see engine/specs/*_quiz.json): q_en, q_hi, 4 options (en+hi), answer, fact_en, fact_hi. Reveal at 25s. Rotate categories: Space, Animals, India GK, Science, History, Geography, Tech, Human body.

**Facts** — engine.py spec type "story" with "tag": "DID YOU KNOW?", duration 30-36:
- beat 1 (0-4s): scene {"type":"big","text":"3 FACTS"} hook en "3 facts that will blow your mind" + hi
- beats 2-4 (~10s each): scene {"type":"big","text":"#1"/"#2"/"#3"} with the fact as caption (en + hi)
- last caption ends with "Which one shocked you? Comment!"
Topics rotate: Human body, Space, Animals, India, History, Money (Hindi), Ocean, Technology.

**Flow story** — ONE complete story in ONE Short (no parts). 6 clips x 10s, Google Flow model "Omni 1.1 Flash", 9:16, 720p, 10s, x1 (15 credits each, 90 total). If Omni voice is poor, use Veo 3.1 Fast 8s (20 credits) x 5.
Structure: 1 Hook (shocking question) → 2 Setup (key fact) → 3 Build → 4 Twist → 5 Climax → 6 Ending (real answer + "Follow for more").
Every clip prompt: "Photorealistic vertical cinematic shot: <scene>. The same deep, calm male Hindi documentary narrator speaks in clear Hindi: \"<line>\". Epic orchestral music. No people's faces close-up, no subtitles, no on-screen text."
Assemble: assemble.py spec.json out.mp4 clip1..clip6 (captions en + hi, tag pill, CTA).
Topic queue (alternate What if / History-mystery): What if the Moon disappeared?; Roopkund skeleton lake mystery; What if the Sun went out for a day?; Iron Pillar of Delhi that never rusts; What if you fell into a black hole?; How the Kohinoor left India; What if all ice melted?; Nalanda library fire.

## Reach + monetization rules (YouTube policies)
1. Original value every time: own script, accurate facts (verify numbers with a web search), never reuse others' clips/music.
2. No repetitive mass-produced feel: vary topics, wording, colors/themes; never upload near-duplicates.
3. AI disclosure: Flow (realistic) videos → tick "Altered or synthetic content: Yes". Code-animated quiz/facts → No.
4. Not made for kids → "No, it's not made for kids".
5. Title ≤ 60 chars, hook first, Hindi + English mix, 2-3 hashtags incl. #shorts. Description: 2 lines + question + 3-5 hashtags. 5-8 tags.
6. No misleading/clickbait claims, no scary/violent gore, no real people, no copyrighted characters/music.
7. Retention: hook in first 2 seconds, Shorts under 60s, loop-friendly endings, ask a comment question.
8. Consistency: same times daily (7:47 AM, 7:47 PM IST), same branding (@I-mRushi, yellow pill).
9. Engagement: pin a comment with the question; reply to early comments.

## Output
Save finals to ~/Downloads/IamRushi_Shorts/final as YYYY-MM-DD_<type>_<slug>.mp4 (+ an upload copy under 10 MB) and a YYYY-MM-DD_upload.txt with title/description/tags/AI-label per video. Append to log.json {date, type, topic, title} and never repeat a topic in log.json.
Upload (automatic): push the evening video to the `premade` branch of github.com/21Rushi/quiz-shorts as
`<YYYY-MM-DD>/evening/video.mp4` (the <10 MB upload copy) + `meta.json`:
{"title","description","tags":[...],"synthetic": true for Flow / false for Facts,"language":"hi"|"en","type","topic"}
Force-push an orphan commit holding only today's and future dates (keeps the repo small). GitHub Actions
(daily-quiz.yml, 13:17 UTC = 6:47 PM IST) uploads it and YouTube publishes at 7:47 PM IST with the AI label.
Must be pushed before 6:30 PM IST. If nothing is pushed, the workflow posts a quiz instead.
Also keep a copy in ~/Downloads/IamRushi_Shorts/final.

## Setup in a fresh session (cloud workspace)
1. Engine lives in the repo at studio/ (engine.py, assemble.py, PLAYBOOK.md); also mirrored in ~/Downloads/IamRushi_Shorts/engine. Copy to /home/claude/shorts.
2. Fonts: mkdir -p ~/fonts && cd ~/fonts && npm pack -s @expo-google-fonts/noto-sans-devanagari @expo-google-fonts/montserrat && for f in *.tgz; do tar xzf $f; done
3. Render: python3 engine.py spec.json out.mp4   (preview frames: python3 engine.py spec.json prefix 2 10 26)
4. Upload copy <10MB: ffmpeg -i in.mp4 -c:v libx264 -preset slow -b:v 2600k -maxrate 3000k -bufsize 5000k -c:a aac -b:a 128k -movflags +faststart upload_x.mp4
5. Commit finals to ~/Downloads/IamRushi_Shorts/final via device_commit_files.
