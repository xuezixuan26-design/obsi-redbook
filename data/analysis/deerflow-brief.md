# DeerFlow Task Brief

- Adapter version: v1
- Source workflow version: v1
- Tasks queued: 3

## Tasks

### 杭州面包店巡礼 -> background_research
- Agent role: researcher
- Priority: 4
- Source: data\raw\sample_note.html
- Instructions:
  - Focus on note: 杭州面包店巡礼
  - Use the note summary as starting context: # 杭州面包店巡礼
  - Prioritize these keywords: https, example, com, bakery, img, jpg
  - Why this task was queued: contains media or transcript hints, rich tag metadata, contains synthesis-oriented language
  - Look for factual background that strengthens the note without drifting too far from the original topic.
  - Capture concise references, trends, competitors, or market context relevant to the note.

### 杭州面包店巡礼 -> deep_summary
- Agent role: synthesizer
- Priority: 4
- Source: data\raw\sample_note.html
- Instructions:
  - Focus on note: 杭州面包店巡礼
  - Use the note summary as starting context: # 杭州面包店巡礼
  - Prioritize these keywords: https, example, com, bakery, img, jpg
  - Why this task was queued: contains media or transcript hints, rich tag metadata, contains synthesis-oriented language
  - Produce a sharper synthesis than the original short summary.
  - Highlight reusable insights, patterns, and possible follow-up topics for Obsidian.

### 杭州面包店巡礼 -> transcribe_media
- Agent role: media-analyst
- Priority: 4
- Source: data\raw\sample_note.html
- Instructions:
  - Focus on note: 杭州面包店巡礼
  - Use the note summary as starting context: # 杭州面包店巡礼
  - Prioritize these keywords: https, example, com, bakery, img, jpg
  - Why this task was queued: contains media or transcript hints, rich tag metadata, contains synthesis-oriented language
  - Check whether local media files or sidecar transcripts already exist before creating new artifacts.
  - If media exists, produce a transcript-ready asset for downstream note enrichment.
