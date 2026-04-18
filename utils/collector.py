"""RSS 抓取模块。"""

from __future__ import annotations

import feedparser


class IntelligenceCollector:
    def __init__(self, sources: dict[str, str]):
        self.sources = sources
        self.seen_links: set[str] = set()

    def scan(self, limit_per_source: int = 15) -> list[dict[str, str]]:
        """抓取 RSS 条目，并在单次运行内做去重。"""

        raw_intel: list[dict[str, str]] = []

        for name, url in self.sources.items():
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit_per_source]:
                link = getattr(entry, "link", "").strip()
                if not link or link in self.seen_links:
                    continue

                raw_intel.append(
                    {
                        "origin": name,
                        "title": getattr(entry, "title", "Untitled"),
                        "digest": getattr(entry, "summary", "No summary"),
                        "url": link,
                    }
                )
                self.seen_links.add(link)

        return raw_intel
