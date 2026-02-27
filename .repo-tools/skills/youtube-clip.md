---
name: youtube-clip
description: Cut a segment from a YouTube video, optionally upload to Telegram with auto-generated caption
---

# YouTube Clip Cutter Skill

Download a specific time segment from a YouTube video. Optionally upload to the test Hebrew Telegram channel with a caption generated from the video's subtitles.

## User Commands

The user can say:
- "cut a clip from this YouTube video"
- "download segment from YouTube"
- "cut 27:55 to 38:58 from this YouTube link"
- "extract a clip from this video"
- "download from X:XX to Y:YY of this YouTube video"
- "clip this YouTube video"
- "cut and upload this clip to Telegram"
- "clip and send to Telegram"
- "cut X:XX to Y:YY from this video and upload to Telegram"

## What This Skill Does

1. **Validates inputs** — checks URL format, time format (MM:SS or HH:MM:SS), start < end
2. **Checks duration** — fetches video length, verifies end time doesn't exceed it
3. **Downloads segment** — uses `yt-dlp --download-sections` to download only the requested portion
4. **Saves locally** — outputs to `~/Downloads/` as `{title}_{start}-{end}.mp4`
5. **Optionally uploads to Telegram** — with `--upload --message "caption"`:
   - **≤ 50 MB**: uploads video + caption to the test Hebrew Telegram channel
   - **> 50 MB**: sends caption as **text message only** — user uploads the video manually to their real channel

## Implementation Details

- **Script**: `.repo-tools/scripts/youtube_clip_cutter.py`
- **Dependencies**: `yt-dlp` and `ffmpeg` (install via `brew install yt-dlp ffmpeg`)
- **Output**: `~/Downloads/` by default (configurable with `--output`)
- **Time formats**: `MM:SS` or `HH:MM:SS`
- **Telegram config**: reads from `.repo-tools/scripts/telegram_config.yaml` (hebrew_channel section)

## Action Instructions

### Download only (no upload)

When the user asks to cut a clip without mentioning Telegram/upload:

```bash
python3 .repo-tools/scripts/youtube_clip_cutter.py \
  --url "YOUTUBE_URL" \
  --start "START_TIME" \
  --end "END_TIME"
```

### Cut and upload to Telegram (full workflow)

When the user asks to upload, Claude MUST follow all 4 steps below automatically:

**Step 1: Download subtitles for the video**
```bash
yt-dlp --write-auto-sub --sub-lang "iw,en" --skip-download \
  --sub-format json3 -o "/tmp/yt_subs" "YOUTUBE_URL"
```
- YouTube uses `iw` for Hebrew (not `he`)
- `json3` format is more reliable than `vtt` (avoids rate limiting issues)
- Creates `/tmp/yt_subs.iw.json3` and/or `/tmp/yt_subs.en.json3`
- If rate-limited (429), retry with `--cookies-from-browser chrome` or wait and retry

**Step 2: Extract the relevant time range from the subtitle file**
Read the json3 file and extract text from events where `tStartMs` falls between START and END times. Prefer Hebrew (`iw`) if available, otherwise use English (`en`).

```python
import json
with open('/tmp/yt_subs.iw.json3', 'r') as f:
    data = json.load(f)
start_ms = START_SECONDS * 1000
end_ms = END_SECONDS * 1000
lines = []
for event in data.get('events', []):
    t = event.get('tStartMs', 0)
    if start_ms <= t <= end_ms:
        segs = event.get('segs', [])
        text = ''.join(s.get('utf8', '') for s in segs).strip()
        if text and text != '\n':
            lines.append(text)
```

**Step 3: Generate a catchy Hebrew caption**
Based on the transcript of the clipped segment, write a short, clickbait-style Hebrew caption (1-2 sentences with emoji). The caption MUST describe what happens in **this specific segment**, not the video in general.

**Step 4: Run the clip cutter with --upload --message**
```bash
python3 .repo-tools/scripts/youtube_clip_cutter.py \
  --url "YOUTUBE_URL" \
  --start "START_TIME" \
  --end "END_TIME" \
  --upload --message "CAPTION"
```

The script handles the rest:
- Downloads the clip
- If ≤ 50 MB → uploads video + caption to Telegram
- If > 50 MB → sends caption as text message only, logs that the user should upload manually

### Examples

**Download only:**
User says: "cut 27:55 to 38:58 from https://www.youtube.com/watch?v=GhgC8CXtGR0"

```bash
python3 .repo-tools/scripts/youtube_clip_cutter.py \
  --url "https://www.youtube.com/watch?v=GhgC8CXtGR0" \
  --start "27:55" \
  --end "38:58"
```

**Cut and upload:**
User says: "cut 27:55 to 38:58 from this link and upload to Telegram"

1. Download subs: `yt-dlp --write-auto-sub --sub-lang "iw,en" --skip-download --sub-format json3 -o "/tmp/yt_subs" "URL"`
2. Extract transcript for 27:55–38:58 from json3 file
3. Generate caption from transcript
4. Run:
```bash
python3 .repo-tools/scripts/youtube_clip_cutter.py \
  --url "https://www.youtube.com/watch?v=GhgC8CXtGR0" \
  --start "27:55" \
  --end "38:58" \
  --upload --message "🤯 חוקר AI מסביר למה שיעורי בית הפכו ללא רלוונטיים..."
```

## Error Scenarios & Solutions

| Issue | Solution |
|-------|---------|
| "Missing dependencies: yt-dlp" | Run `brew install yt-dlp ffmpeg` |
| "Invalid YouTube URL" | Check the URL is a valid youtube.com or youtu.be link |
| "Start time must be before end time" | Swap the times |
| "End time exceeds video duration" | Use a smaller end time |
| "Invalid time format" | Use MM:SS or HH:MM:SS format |
| Download hangs or fails | Check internet connection; try again |
| "File too large for video upload" | Normal — script sends caption as text instead. Upload the video manually. |
| "--message is required when using --upload" | Add `--message "caption"` |
| Subtitle download 429 rate limit | Retry with `--cookies-from-browser chrome`, or wait a minute |
| No subtitles available | Fall back to video title for caption (less ideal) |

## Response Templates

**Success (download only):**
> Clip saved to `~/Downloads/{filename}` ({size} MB). The segment from {start} to {end} has been downloaded.

**Success (upload, ≤ 50 MB):**
> Clip saved to `~/Downloads/{filename}` ({size} MB) and uploaded to Telegram with caption.

**Success (upload, > 50 MB):**
> Clip saved to `~/Downloads/{filename}` ({size} MB). File is too large for Telegram video upload, so the caption was sent as a text message. Upload the video manually to your real channel.

**Missing dependencies:**
> yt-dlp and/or ffmpeg are not installed. Run `brew install yt-dlp ffmpeg` and try again.

---

**Last Updated:** 2026-02-27
