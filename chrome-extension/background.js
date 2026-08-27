const BRIDGE_ENDPOINTS = [
  "http://127.0.0.1:8765/api/browser/capture",
  "http://localhost:8765/api/browser/capture"
];

chrome.action.onClicked.addListener(async (tab) => {
  if (!tab.id || !tab.url || !/^https?:\/\//i.test(tab.url)) {
    await setBadge("NO", "A aba atual não é uma página HTTP/HTTPS capturável.");
    return;
  }

  try {
    await setBadge("…", "Capturando a aba ativa…");
    const [{ result: capture }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: extractActivePage
    });

    if (!capture || !capture.url) {
      throw new Error("capture_empty");
    }

    const response = await postToBridge({ capture });
    await chrome.storage.local.set({
      last_capture: {
        at: Date.now(),
        page: { url: capture.url, title: capture.title, doi: capture.doi },
        bridge: response
      }
    });
    await setBadge("OK", response.capture?.capture_id || "Captura enviada ao URANO.");
  } catch (error) {
    await chrome.storage.local.set({
      last_error: { at: Date.now(), message: String(error?.message || error) }
    });
    await setBadge("ERR", `Falha ao enviar ao URANO: ${String(error?.message || error)}`);
  }
});

async function postToBridge(body) {
  let lastError = null;
  for (const endpoint of BRIDGE_ENDPOINTS) {
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        throw new Error(data.error || `bridge_http_${response.status}`);
      }
      return data;
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error("bridge_unreachable");
}

async function setBadge(text, title) {
  await chrome.action.setBadgeText({ text });
  await chrome.action.setTitle({ title });
  if (text === "OK") {
    setTimeout(() => chrome.action.setBadgeText({ text: "" }), 4000);
  }
}

function extractActivePage() {
  const MAX_TEXT = 180000;
  const one = (selectors) => {
    for (const selector of selectors) {
      const el = document.querySelector(selector);
      const value = el?.getAttribute("content") || el?.textContent;
      if (value && value.trim()) return value.trim();
    }
    return "";
  };
  const allMeta = (selectors) => {
    const seen = new Set();
    for (const selector of selectors) {
      for (const el of document.querySelectorAll(selector)) {
        const value = (el.getAttribute("content") || el.textContent || "").trim();
        if (value) seen.add(value);
      }
    }
    return [...seen];
  };

  const normalize = (value) => (value || "").replace(/\s+/g, " ").trim();
  const doiRegex = /10\.\d{4,9}\/[-._;()/:A-Z0-9]+/i;

  const explicitDoi = one([
    'meta[name="citation_doi"]',
    'meta[name="dc.identifier"]',
    'meta[name="DC.Identifier"]',
    'meta[name="prism.doi"]',
    '[data-doi]'
  ]);
  const doiHref = [...document.querySelectorAll('a[href*="doi.org/"]')]
    .map((a) => a.href.match(doiRegex)?.[0])
    .find(Boolean) || "";
  const bodyProbe = normalize(document.body?.innerText || "").slice(0, 40000);
  const doi = (explicitDoi.match(doiRegex)?.[0] || doiHref || bodyProbe.match(doiRegex)?.[0] || "").replace(/[).,;]+$/, "");

  const primary = document.querySelector("article") || document.querySelector("main") || document.body;
  const text = normalize(primary?.innerText || "").slice(0, MAX_TEXT);
  const selectedText = normalize(window.getSelection?.().toString() || "").slice(0, MAX_TEXT);
  const canonical = document.querySelector('link[rel="canonical"]')?.href || location.href;

  return {
    url: location.href,
    title: normalize(document.title),
    doi: doi || null,
    selected_text: selectedText,
    text,
    metadata: {
      authors: allMeta(['meta[name="citation_author"]', 'meta[name="dc.creator"]']),
      journal: one(['meta[name="citation_journal_title"]', 'meta[name="prism.publicationName"]']),
      publisher: one(['meta[name="citation_publisher"]', 'meta[name="dc.publisher"]']),
      publication_date: one(['meta[name="citation_publication_date"]', 'meta[name="citation_date"]', 'meta[name="dc.date"]']),
      language: document.documentElement.lang || "",
      description: one(['meta[name="description"]', 'meta[property="og:description"]']),
      canonical_url: canonical,
      content_type: document.contentType || "text/html"
    }
  };
}
