"use strict";
(() => {
  const form = document.querySelector("#reference-search");
  if (!form) return;
  const field = document.querySelector("#search-query");
  const results = document.querySelector("#search-results");
  const status = document.querySelector("#search-status");
  let documents = null;

  async function load() {
    if (documents) return documents;
    const response = await fetch(form.dataset.index);
    if (!response.ok) throw new Error("Search index unavailable");
    const data = await response.json();
    if (data.schema_version !== 1 || !Array.isArray(data.documents))
      throw new Error("Unsupported search index");
    documents = data.documents;
    return documents;
  }
  function render(items, words) {
    results.replaceChildren();
    for (const item of items) {
      const row = document.createElement("li");
      const link = document.createElement("a");
      link.href = item.url;
      link.textContent = item.title;
      row.append(link);
      const summary = document.createElement("p");
      const haystack = item.text.toLowerCase();
      const start = Math.max(0, haystack.indexOf(words[0]) - 70);
      const excerpt = item.text.slice(start, start + 230);
      summary.textContent = (start ? "…" : "") + excerpt + (start + 230 < item.text.length ? "…" : "");
      row.append(summary);
      results.append(row);
    }
  }
  async function search(event) {
    if (event) event.preventDefault();
    const words = field.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    results.replaceChildren();
    if (!words.length) {
      status.textContent = "Enter a term to search.";
      return;
    }
    status.textContent = "Searching local reference pages…";
    try {
      const source = await load();
      const hits = source.filter((page) => {
        const text = (page.title + " " + page.text).toLowerCase();
        return words.every((word) => text.includes(word));
      }).sort((a, b) => {
        const score = (x) => words.filter((w) => x.title.toLowerCase().includes(w)).length;
        return score(b) - score(a);
      }).slice(0, 40);
      render(hits, words);
      status.textContent = hits.length + " matching document" +
        (hits.length === 1 ? "" : "s") + (hits.length === 40 ? " (first 40)" : "");
    } catch {
      status.textContent = "Search index could not be loaded. The navigation remains available.";
    }
  }
  form.addEventListener("submit", search);
  field.addEventListener("input", search);
  const q = new URLSearchParams(location.search).get("q");
  if (q) { field.value = q; search(); }
})();
