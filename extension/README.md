# Chrome Extension

This folder contains the unpacked Chrome extension for Obsi Redbook Clipper.

## Load Locally

1. Open `chrome://extensions`
2. Enable `Developer mode`
3. Click `Load unpacked`
4. Select this `extension/` folder

## What It Can Do

- extract content from Xiaohongshu post pages
- extract content from public WeChat article pages
- preview note metadata
- copy Markdown
- download Markdown
- download JSON
- open an `obsidian://` handoff when configured

## Options

Open the extension options page and set:

- your Obsidian vault name
- the target folder path inside that vault

The extension does not write directly to local files. It uses an Obsidian URI handoff or browser downloads.
