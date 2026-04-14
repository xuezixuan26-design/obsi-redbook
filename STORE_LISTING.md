# Chrome Web Store Draft

## Extension Name

Obsi Redbook Clipper

## Short Description

Clip Xiaohongshu posts and public WeChat articles into Obsidian-friendly Markdown.

## Detailed Description

Obsi Redbook Clipper helps researchers, readers, and note-takers capture content from Xiaohongshu (Rednote) and public WeChat articles directly in Chrome.

Use it to:

- extract structured content from the current page
- preview title, author, date, and summary
- copy clean Markdown to the clipboard
- download Markdown or JSON
- send notes into Obsidian with an `obsidian://` handoff

The extension is designed to stay lightweight and privacy-friendly. Extraction happens locally in the browser, and no remote service is required.

## Key Features

- Xiaohongshu page capture
- WeChat article capture
- Markdown export
- JSON export
- Obsidian handoff
- Local-only processing

## Suggested Category

Productivity

## Suggested Tags

- obsidian
- markdown
- rednote
- xiaohongshu
- wechat
- note taking
- knowledge management

## Permissions Justification

- `activeTab`: needed to read the currently open supported page when the user opens the extension
- `storage`: needed to save the user's Obsidian vault name and folder preferences
- `downloads`: needed to download Markdown and JSON files when the user explicitly clicks a download button

## Privacy Summary

- No remote server required
- No analytics
- No page data sent off-device
- Only user-triggered extraction on supported pages

## Recommended Screenshots

1. Popup on a Xiaohongshu post showing preview metadata
2. Popup on a WeChat article showing extracted summary
3. Options page with Obsidian vault configuration
