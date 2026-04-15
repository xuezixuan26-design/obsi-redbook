# Release Checklist

Use this checklist before sharing or submitting the Chrome extension.

## Product Readiness

- [ ] Confirm the extension loads successfully from `extension/` in `chrome://extensions`
- [ ] Test Xiaohongshu capture on at least 2 real post pages
- [ ] Test WeChat article capture on at least 2 public article pages
- [ ] Test `Copy Markdown`
- [ ] Test `Download .md`
- [ ] Test `Download .json`
- [ ] Test `Send To Obsidian` with a real vault name in extension options

## Content And Copy

- [ ] Review [README.md](./README.md)
- [ ] Review [STORE_LISTING.md](./STORE_LISTING.md)
- [ ] Review [PRIVACY.md](./PRIVACY.md)
- [ ] Confirm the extension name is final
- [ ] Confirm the short description is final

## Visual Assets

- [ ] Verify icons exist in `extension/icons/`
- [ ] Capture at least 3 screenshots of the extension UI
- [ ] Prepare a small promotional image if you want a more polished store listing

## Security And Privacy

- [ ] Confirm no secrets are committed
- [ ] Confirm `.env` is ignored
- [ ] Confirm `data/cookies.txt` is ignored
- [ ] Confirm no local Obsidian vault paths are exposed in committed files
- [ ] Re-read [PRIVACY.md](./PRIVACY.md) and make sure it matches actual behavior

## Packaging

- [ ] Create a clean zip from the `extension/` folder only
- [ ] Do not include the whole repository in the store upload
- [ ] Keep the version in `extension/manifest.json` in sync with your release

## Chrome Web Store Submission

- [ ] Create or open your Chrome Web Store developer account
- [ ] Create a new item
- [ ] Upload the packed extension zip
- [ ] Paste the short and detailed descriptions from [STORE_LISTING.md](./STORE_LISTING.md)
- [ ] Upload screenshots
- [ ] Upload privacy policy text or link based on [PRIVACY.md](./PRIVACY.md)
- [ ] Review requested permissions and provide justification
- [ ] Submit for review
