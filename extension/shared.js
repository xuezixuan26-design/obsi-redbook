(function () {
  function normalizeWhitespace(text) {
    return (text || "").replace(/\s+/g, " ").trim();
  }

  function splitSentences(text) {
    const cleaned = normalizeWhitespace(text);
    if (!cleaned) {
      return [];
    }
    return cleaned
      .split(/(?<=[。！？.!?])\s+/)
      .map((part) => part.trim())
      .filter(Boolean);
  }

  function deriveSummary(content, maxLength = 180) {
    const sentences = splitSentences(content);
    if (!sentences.length) {
      return "No summary available.";
    }
    const first = sentences[0];
    if (first.length <= maxLength) {
      return first;
    }
    let shortened = first.slice(0, maxLength - 3).trim();
    if (shortened.includes(" ")) {
      shortened = shortened.slice(0, shortened.lastIndexOf(" "));
    }
    return `${shortened}...`;
  }

  function deriveKeyInsights(content, limit = 3) {
    const sentences = splitSentences(content);
    const items = [];
    for (const sentence of sentences) {
      const cleaned = normalizeWhitespace(sentence);
      if (cleaned && !items.includes(cleaned)) {
        items.push(cleaned);
      }
      if (items.length >= limit) {
        break;
      }
    }
    return items;
  }

  function slugify(value) {
    const cleaned = (value || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9\u4e00-\u9fff]+/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "");
    return cleaned || "untitled";
  }

  function formatPublishedDate(value) {
    return value ? String(value).slice(0, 10) : "";
  }

  function buildFilename(payload) {
    const date = formatPublishedDate(payload.published_at) || "undated";
    const title = payload.title || payload.note_id || "untitled";
    return `${date}-${slugify(title)}.md`;
  }

  function preparePayload(payload) {
    const author = typeof payload.author === "string"
      ? { name: payload.author, user_id: "", profile_url: "" }
      : (payload.author || {});

    return {
      ...payload,
      author,
      title: payload.title || payload.note_id || "Untitled",
      summary: deriveSummary(payload.content || ""),
      key_insights: deriveKeyInsights(payload.content || ""),
      published_date: formatPublishedDate(payload.published_at),
      filename: buildFilename(payload),
      tags: Array.isArray(payload.tags) ? payload.tags : [],
      images: Array.isArray(payload.images) ? payload.images : [],
      video_url: payload.video_url || "",
      transcript: typeof payload.transcript === "string" ? payload.transcript.trim() : ""
    };
  }

  function renderMarkdown(payload) {
    const post = preparePayload(payload);
    const lines = [
      `# ${post.title}`,
      "",
      `- Source: [Original Post](${post.url || ""})`,
      `- Author: ${post.author.name || "Unknown"}`,
      `- Published: ${post.published_date || "Unknown"}`,
      "",
      "## Summary",
      "",
      post.summary,
      "",
      "## Key Insights",
      ""
    ];

    if (post.key_insights.length) {
      for (const insight of post.key_insights) {
        lines.push(`- ${insight}`);
      }
    } else {
      lines.push("- No clear insights extracted.");
    }

    lines.push("", "## Tags", "");
    if (post.tags.length) {
      for (const tag of post.tags) {
        lines.push(`- #${tag}`);
      }
    } else {
      lines.push("- No tags");
    }

    lines.push("", "## Original Content", "", post.content || "No content captured.");

    if (post.transcript) {
      lines.push("", "## Transcript", "", post.transcript);
    }

    return `${lines.join("\n").trim()}\n`;
  }

  function parseJsonScriptContent(scriptText, regex) {
    const match = scriptText.match(regex);
    if (!match) {
      return null;
    }
    try {
      return JSON.parse(match[1]);
    } catch (error) {
      return null;
    }
  }

  function findFirstNoteObject(obj) {
    if (!obj || typeof obj !== "object") {
      return null;
    }
    if (!Array.isArray(obj)) {
      if (obj.noteId || (obj.id && (obj.title || obj.desc || obj.content))) {
        return obj;
      }
      for (const value of Object.values(obj)) {
        const found = findFirstNoteObject(value);
        if (found) {
          return found;
        }
      }
      return null;
    }
    for (const item of obj) {
      const found = findFirstNoteObject(item);
      if (found) {
        return found;
      }
    }
    return null;
  }

  function normalizeTimestamp(value) {
    if (value === null || value === undefined || value === "") {
      return "";
    }
    const numeric = Number(value);
    if (!Number.isNaN(numeric) && Number.isFinite(numeric)) {
      const millis = numeric > 10000000000 ? numeric : numeric * 1000;
      return new Date(millis).toISOString();
    }
    return String(value);
  }

  function normalizeXhsPayload(state, url) {
    const note = findFirstNoteObject(state);
    if (!note) {
      throw new Error("Could not locate a note-like object in the page state.");
    }

    const author = note.user && typeof note.user === "object" ? note.user : {};
    const tagsRaw = note.tagList || note.tags || note.topicList || [];
    const tags = [];
    for (const tag of tagsRaw) {
      if (typeof tag === "string" && tag.trim()) {
        tags.push(tag.trim());
      } else if (tag && typeof tag === "object") {
        const value = tag.name || tag.tagName || tag.text || tag.displayName;
        if (value) {
          tags.push(String(value).trim());
        }
      }
    }

    const imageLists = [note.imageList, note.images, note.imageInfoList].find((value) => Array.isArray(value)) || [];
    const images = imageLists
      .map((item) => item && (item.url || item.imageUrl || item.urlDefault || item.originUrl || item.masterUrl))
      .filter(Boolean);

    const videoCandidates = [note.video, note.videoInfo, note.videoMedia, note.noteVideoInfo]
      .filter((item) => item && typeof item === "object");
    let videoUrl = "";
    for (const item of videoCandidates) {
      videoUrl = item.masterUrl || item.url || item.videoUrl || item.originUrl || "";
      if (videoUrl) {
        break;
      }
    }

    return {
      url,
      note_id: String(note.noteId || note.id || ""),
      title: String(note.title || note.displayTitle || ""),
      author: {
        name: String(author.nickname || author.name || "Unknown"),
        user_id: String(author.userId || author.id || ""),
        profile_url: String(author.profileUrl || author.url || "")
      },
      content: String(note.desc || note.content || note.text || ""),
      tags: [...new Set(tags)].sort(),
      images,
      video_url: videoUrl || null,
      published_at: normalizeTimestamp(note.time || note.publishTime || note.publish_time || note.lastUpdateTime),
      source_type: "xhs"
    };
  }

  function extractXhsFromDocument(doc, url) {
    const scripts = Array.from(doc.querySelectorAll("script"));
    for (const script of scripts) {
      const text = script.textContent || "";
      const direct = parseJsonScriptContent(text, /window\.__INITIAL_STATE__\s*=\s*(\{[\s\S]*\})\s*;?/);
      if (direct) {
        return normalizeXhsPayload(direct, url);
      }
      const redux = parseJsonScriptContent(text, /window\.__REDUX_STATE__\s*=\s*(\{[\s\S]*\})\s*;?/);
      if (redux) {
        return normalizeXhsPayload(redux, url);
      }
      const nextData = parseJsonScriptContent(text, /(\{[\s\S]*"props"[\s\S]*\})/);
      if (script.id === "__NEXT_DATA__" && nextData) {
        return normalizeXhsPayload(nextData, url);
      }
    }
    throw new Error("Unable to extract Xiaohongshu embedded state.");
  }

  function decodeJsString(value) {
    if (!value) {
      return "";
    }
    try {
      return JSON.parse(`"${value.replace(/"/g, '\\"')}"`);
    } catch (error) {
      return value;
    }
  }

  function stripHtml(html) {
    const container = document.createElement("div");
    container.innerHTML = html;
    return normalizeWhitespace(container.innerText || "");
  }

  function extractWechatFromDocument(doc, url) {
    const scriptsText = Array.from(doc.querySelectorAll("script"))
      .map((item) => item.textContent || "")
      .join("\n");
    const title = decodeJsString((scriptsText.match(/var\s+msg_title\s*=\s*'((?:\\.|[^'])*)';/) || [])[1] || "");
    const nickname = decodeJsString((scriptsText.match(/var\s+nickname\s*=\s*'((?:\\.|[^'])*)';/) || [])[1] || "");
    const userName = decodeJsString((scriptsText.match(/var\s+user_name\s*=\s*'((?:\\.|[^'])*)';/) || [])[1] || "");
    const publishTime = (scriptsText.match(/var\s+publish_time\s*=\s*"?(\d+)"?;/) || [])[1]
      || (scriptsText.match(/var\s+ct\s*=\s*"?(\d+)"?;/) || [])[1]
      || "";

    const contentNode = doc.querySelector("#js_content");
    if (!contentNode) {
      throw new Error("Unable to find WeChat article content.");
    }
    const content = stripHtml(contentNode.innerHTML);
    const images = Array.from(contentNode.querySelectorAll("img"))
      .map((img) => img.getAttribute("data-src") || img.getAttribute("src") || "")
      .filter(Boolean);

    const query = new URL(url).searchParams;
    const noteId = query.get("sn") || query.get("mid") || slugify(title || "wechat-article");

    return {
      url,
      note_id: noteId,
      title: title || noteId,
      author: {
        name: nickname || userName || "Unknown",
        user_id: userName || "",
        profile_url: ""
      },
      content,
      tags: [],
      images,
      video_url: null,
      published_at: normalizeTimestamp(publishTime),
      source_type: "wechat"
    };
  }

  function detectSourceType(url) {
    const hostname = new URL(url).hostname.toLowerCase();
    if (hostname.includes("xiaohongshu.com") || hostname.includes("xhslink.com")) {
      return "xhs";
    }
    if (hostname.includes("mp.weixin.qq.com")) {
      return "wechat";
    }
    return "unknown";
  }

  function extractFromDocument(doc = document, url = window.location.href) {
    const sourceType = detectSourceType(url);
    if (sourceType === "xhs") {
      return extractXhsFromDocument(doc, url);
    }
    if (sourceType === "wechat") {
      return extractWechatFromDocument(doc, url);
    }
    throw new Error("Unsupported page. Open a Xiaohongshu post or public WeChat article.");
  }

  window.ObsiRedbookShared = {
    buildFilename,
    detectSourceType,
    extractFromDocument,
    preparePayload,
    renderMarkdown
  };
})();
