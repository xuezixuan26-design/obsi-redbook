const state = {
  extraction: null,
  options: {
    vaultName: "",
    folderPath: "Inbox/Xiaohongshu"
  }
};

const elements = {
  author: document.getElementById("author"),
  copyBtn: document.getElementById("copyBtn"),
  downloadJsonBtn: document.getElementById("downloadJsonBtn"),
  downloadMarkdownBtn: document.getElementById("downloadMarkdownBtn"),
  obsidianBtn: document.getElementById("obsidianBtn"),
  previewCard: document.getElementById("previewCard"),
  published: document.getElementById("published"),
  refreshBtn: document.getElementById("refreshBtn"),
  sourceType: document.getElementById("sourceType"),
  statusText: document.getElementById("statusText"),
  summary: document.getElementById("summary"),
  tags: document.getElementById("tags"),
  title: document.getElementById("title")
};

async function getActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

async function loadOptions() {
  const stored = await chrome.storage.sync.get({
    vaultName: "",
    folderPath: "Inbox/Xiaohongshu"
  });
  state.options = stored;
}

function setStatus(message) {
  elements.statusText.textContent = message;
}

function downloadText(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  chrome.downloads.download({
    url,
    filename,
    saveAs: true
  }, () => URL.revokeObjectURL(url));
}

function renderPreview(result) {
  const payload = result.payload;
  const prepared = payload;
  elements.previewCard.classList.remove("hidden");
  elements.title.textContent = prepared.title || prepared.note_id || "Untitled";
  elements.sourceType.textContent = prepared.source_type || "unknown";
  elements.author.textContent = prepared.author?.name || "Unknown";
  elements.published.textContent = (prepared.published_at || "").slice(0, 10) || "Unknown";
  elements.summary.textContent = window.ObsiRedbookShared.preparePayload(prepared).summary;
  elements.tags.innerHTML = "";
  for (const tag of prepared.tags || []) {
    const item = document.createElement("span");
    item.className = "tag";
    item.textContent = `#${tag}`;
    elements.tags.appendChild(item);
  }
}

async function requestExtraction() {
  setStatus("Reading current page...");
  elements.previewCard.classList.add("hidden");
  state.extraction = null;
  toggleButtons(false);

  const tab = await getActiveTab();
  if (!tab?.id) {
    setStatus("No active tab found.");
    return;
  }

  const result = await chrome.tabs.sendMessage(tab.id, { type: "EXTRACT_PAGE" }).catch(() => ({
    ok: false,
    error: "This page is not supported or the content script is unavailable."
  }));

  if (!result?.ok) {
    setStatus(result?.error || "Could not extract page content.");
    return;
  }

  state.extraction = result;
  renderPreview(result);
  setStatus("Content captured. You can now copy or download it.");
  toggleButtons(true);
}

function toggleButtons(enabled) {
  elements.copyBtn.disabled = !enabled;
  elements.downloadMarkdownBtn.disabled = !enabled;
  elements.downloadJsonBtn.disabled = !enabled;
  elements.obsidianBtn.disabled = !enabled;
}

async function copyMarkdown() {
  if (!state.extraction) {
    return;
  }
  await navigator.clipboard.writeText(state.extraction.markdown);
  setStatus("Markdown copied to clipboard.");
}

function downloadMarkdown() {
  if (!state.extraction) {
    return;
  }
  downloadText(state.extraction.filename, state.extraction.markdown, "text/markdown;charset=utf-8");
  setStatus("Markdown download started.");
}

function downloadJson() {
  if (!state.extraction) {
    return;
  }
  const filename = state.extraction.filename.replace(/\.md$/i, ".json");
  downloadText(filename, JSON.stringify(state.extraction.payload, null, 2), "application/json;charset=utf-8");
  setStatus("JSON download started.");
}

function sendToObsidian() {
  if (!state.extraction) {
    return;
  }
  if (!state.options.vaultName) {
    setStatus("Set your Obsidian vault name in Options first.");
    return;
  }

  const fileName = state.extraction.filename.replace(/\.md$/i, "");
  const uri = new URL("obsidian://new");
  uri.searchParams.set("vault", state.options.vaultName);
  uri.searchParams.set("name", fileName);
  uri.searchParams.set("content", state.extraction.markdown);
  if (state.options.folderPath) {
    uri.searchParams.set("file", `${state.options.folderPath}/${fileName}`);
  }
  chrome.tabs.create({ url: uri.toString() });
  setStatus("Obsidian URI opened.");
}

elements.refreshBtn.addEventListener("click", requestExtraction);
elements.copyBtn.addEventListener("click", copyMarkdown);
elements.downloadMarkdownBtn.addEventListener("click", downloadMarkdown);
elements.downloadJsonBtn.addEventListener("click", downloadJson);
elements.obsidianBtn.addEventListener("click", sendToObsidian);

loadOptions().then(requestExtraction);
