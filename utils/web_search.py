"""
Simple web search utility with multiple backends and graceful fallbacks.
Returns a list of {title, url, snippet} dictionaries.

Priority order:
1) Bing Web Search API (if BING_SEARCH_API_KEY is set)
2) duckduckgo_search package (if available)
3) DuckDuckGo Lite HTML fallback (no API key)
"""
from __future__ import annotations

import os
import re
import html
from typing import List, Dict


def _bing_search(query: str, max_results: int) -> List[Dict[str, str]]:
    api_key = os.getenv("BING_SEARCH_API_KEY")
    if not api_key:
        return []
    try:
        import requests
        endpoint = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        params = {"q": query, "count": max_results}
        resp = requests.get(endpoint, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("webPages", {}).get("value", [])
        out = []
        for it in items[:max_results]:
            out.append({
                "title": it.get("name") or "Untitled",
                "url": it.get("url") or "",
                "snippet": it.get("snippet") or ""
            })
        return out
    except Exception:
        return []


def _ddgs_search(query: str, max_results: int) -> List[Dict[str, str]]:
    try:
        from duckduckgo_search import DDGS  # type: ignore
    except Exception:
        return []
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                # r typically has keys: title, href, body
                results.append({
                    "title": r.get("title") or "Untitled",
                    "url": r.get("href") or "",
                    "snippet": r.get("body") or ""
                })
        return results[:max_results]
    except Exception:
        return []


def _ddg_lite_scrape(query: str, max_results: int) -> List[Dict[str, str]]:
    """Very simple fallback using DuckDuckGo lite HTML results."""
    try:
        import requests
    except Exception:
        return []
    try:
        url = "https://lite.duckduckgo.com/lite/"
        resp = requests.get(url, params={"q": query}, timeout=15)
        if resp.status_code != 200:
            return []
        text = resp.text
        # Each result is like: <a rel="nofollow" class="result-link" href="https://...">Title</a>
        # Followed by a small snippet in <td> elements; keep it simple.
        links = re.findall(r'<a[^>]*class="result-link"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', text, flags=re.I)
        # Decode HTML entities
        out = []
        for href, title in links[:max_results]:
            title_clean = html.unescape(re.sub(r"<.*?>", "", title))
            href_clean = html.unescape(href)
            out.append({
                "title": title_clean or "Untitled",
                "url": href_clean,
                "snippet": ""
            })
        return out
    except Exception:
        return []


def run_web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """High-level web search function with fallbacks.

    Returns list of dicts with keys: title, url, snippet
    """
    query = (query or "").strip()
    if not query:
        return []

    # Try Bing API first if configured
    results = _bing_search(query, max_results)
    if results:
        return results

    # Try duckduckgo_search package next
    results = _ddgs_search(query, max_results)
    if results:
        return results

    # Fallback to DDG lite scraping
    results = _ddg_lite_scrape(query, max_results)
    return results[:max_results]
