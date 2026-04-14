(function () {
  function handleExtractRequest() {
    try {
      const payload = window.ObsiRedbookShared.extractFromDocument(document, window.location.href);
      const markdown = window.ObsiRedbookShared.renderMarkdown(payload);
      return {
        ok: true,
        payload,
        markdown,
        filename: window.ObsiRedbookShared.buildFilename(payload)
      };
    } catch (error) {
      return {
        ok: false,
        error: error instanceof Error ? error.message : String(error)
      };
    }
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message && message.type === "EXTRACT_PAGE") {
      sendResponse(handleExtractRequest());
    }
    return false;
  });
})();
