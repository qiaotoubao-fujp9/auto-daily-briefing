"""自动日报系统的主入口。"""

from __future__ import annotations

import os
from typing import Final

from dotenv import load_dotenv

from utils.analyst import GeminiChief
from utils.archiver import ArchiveMaster
from utils.collector import IntelligenceCollector
from utils.memory import MemoryBank

load_dotenv()

DEFAULT_SOURCES: Final[dict[str, str]] = {
    "36氪": "https://36kr.com/feed",
    "少数派": "https://sspai.com/feed",
    "IT之家": "https://www.ithome.com/rss/",
}
DEFAULT_HISTORY_FILE: Final[str] = "utils/history.txt"
DEFAULT_HISTORY_CAPACITY: Final[int] = 500
DEFAULT_MODEL: Final[str] = os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"
DEFAULT_OUTPUT_DIR: Final[str] = "每日简报"
DEFAULT_REPORT_PREFIX: Final[str] = "精选简报"


def run_daily_briefing() -> int:
    """抓取新内容、生成日报并完成归档。"""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("错误：未找到 GEMINI_API_KEY，请检查本地 .env 或 GitHub Secrets。")
        return 1

    collector = IntelligenceCollector(DEFAULT_SOURCES)
    memory = MemoryBank(
        history_file=DEFAULT_HISTORY_FILE,
        max_capacity=DEFAULT_HISTORY_CAPACITY,
    )
    analyst = GeminiChief(api_key=api_key, model=DEFAULT_MODEL)

    print("正在抓取 RSS 源...")
    raw_items = collector.scan()

    fresh_items = [item for item in raw_items if memory.is_new(item["url"])]
    new_links = [item["url"] for item in fresh_items]

    if not fresh_items:
        print(f"未发现新内容，本次共扫描 {len(raw_items)} 条，跳过摘要生成。")
        return 0

    print(f"开始生成日报：共扫描 {len(raw_items)} 条，新增 {len(fresh_items)} 条。")
    report = analyst.summarize(fresh_items)

    archived_path = ArchiveMaster.store(
        report,
        output_dir=DEFAULT_OUTPUT_DIR,
        prefix=DEFAULT_REPORT_PREFIX,
    )
    memory.update(new_links)

    print(f"日报已归档到：{archived_path}")
    print(f"历史记录已更新，最多保留最近 {DEFAULT_HISTORY_CAPACITY} 条链接。")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_daily_briefing())
