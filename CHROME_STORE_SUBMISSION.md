# Chrome Web Store Submission Guide

This guide maps the repository files to the fields you will see in the Chrome Web Store dashboard.

## 1. Package The Extension

Create a zip archive from the contents of the `extension/` folder.

Important:

- Zip the files inside `extension/`
- Do not zip the entire repository root

Your zip should include files like:

- `manifest.json`
- `popup.html`
- `popup.js`
- `content.js`
- `shared.js`
- `options.html`
- `options.js`
- `icons/`

## 2. Basic Store Fields

Use [STORE_LISTING.md](./STORE_LISTING.md) as the source of truth.

Recommended mapping:

- Extension name: `Obsi Redbook Clipper`
- Short description: use the short description block
- Detailed description: use the detailed description block
- Category: `Productivity`

## 3. Privacy Section

Use [PRIVACY.md](./PRIVACY.md).

You can either:

- host the privacy policy somewhere public and paste the URL
- or use the policy text as the basis for the Chrome Web Store privacy questionnaire

Important points to declare consistently:

- content extraction is local
- no analytics are collected
- no page content is sent to a remote server
- only user-triggered actions are performed

## 4. Permissions Explanation

Current extension permissions:

- `activeTab`
- `storage`
- `downloads`

Recommended explanations:

- `activeTab`: needed to read the current supported page when the user opens the popup
- `storage`: needed to save the Obsidian vault name and destination folder
- `downloads`: needed to save Markdown and JSON files when the user clicks download

## 5. Screenshots To Prepare

Take screenshots for at least these states:

1. Popup open on a Xiaohongshu post with preview visible
2. Popup open on a WeChat article with preview visible
3. Options page showing Obsidian configuration

Recommended screenshot principles:

- keep the browser width clean and readable
- avoid exposing personal account information if possible
- use real supported pages rather than placeholders

## 6. Versioning

Before each upload:

1. update `version` in `extension/manifest.json`
2. commit the change
3. push to GitHub
4. create a fresh zip from `extension/`

## 7. Final Pre-Submission Checks

- Load the unpacked extension again after the version bump
- Make sure the popup still works
- Make sure the content script still runs on both supported sources
- Make sure the options page still saves correctly
- Make sure the Obsidian handoff still opens
