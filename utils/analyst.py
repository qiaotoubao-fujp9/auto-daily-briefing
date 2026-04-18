"""基于 Gemini 的摘要生成模块。"""

from __future__ import annotations

import time
from typing import Final

from google import genai

DEFAULT_STYLE_GUIDE: Final[dict[str, str]] = {
    "role": "统帅的首席情报官",
    "advice_label": "统帅锦囊",
}
DEFAULT_RETRY_DELAYS: Final[tuple[int, ...]] = (15, 45, 90)
RETRYABLE_STATUS_CODES: Final[set[int]] = {429, 500, 502, 503, 504}
RETRYABLE_KEYWORDS: Final[tuple[str, ...]] = (
    "429",
    "500",
    "502",
    "503",
    "504",
    "service unavailable",
    "temporarily unavailable",
    "temporary unavailable",
    "too many requests",
    "rate limit",
    "resource exhausted",
    "quota exceeded",
    "overloaded",
    "backend error",
    "unavailable",
)


class GeminiChief:
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        style_guide: dict[str, str] | None = None,
        retry_delays: tuple[int, ...] = DEFAULT_RETRY_DELAYS,
    ):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.style_guide = DEFAULT_STYLE_GUIDE | (style_guide or {})
        self.retry_delays = retry_delays
        self.max_attempts = len(retry_delays) + 1

    def _build_package(self, intel_list: list[dict[str, str]]) -> str:
        return "\n\n".join(
            f"[{item['origin']}] {item['title']}\n{item['digest'][:300]}\nLink: {item['url']}"
            for item in intel_list
        )

    def _build_prompt(self, intel_list: list[dict[str, str]]) -> str:
        package = self._build_package(intel_list)
        advice_label = self.style_guide["advice_label"]
        role = self.style_guide["role"]

        return (
            f"你是{role}。请从以下 {len(intel_list)} 条情报中精选 Top 10 进行深度研判：\n\n"
            f"{package}\n\n"
            "--- 最高指令 ---\n"
            "请你必须严格按照以下 Markdown 格式输出每一条情报，**绝对不可漏掉原文链接**：\n\n"
            "**[情报X] [{情报标题}]({原文Link})**\n"
            "* **[核心事实]**：一句话概括核心事件。\n"
            "* **[行业内参]**：深度分析行业影响与趋势。\n"
            f"* **[{advice_label}]**：专门为软件工程学生提供的技术关注点或行动建议。\n"
        )

    def _extract_status_code(self, error: Exception) -> int | None:
        for attr_name in ("status_code", "code"):
            value = getattr(error, attr_name, None)
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)

        response = getattr(error, "response", None)
        if response is not None:
            for attr_name in ("status_code", "status"):
                value = getattr(response, attr_name, None)
                if isinstance(value, int):
                    return value
                if isinstance(value, str) and value.isdigit():
                    return int(value)

        return None

    def _format_error(self, error: Exception) -> str:
        status_code = self._extract_status_code(error)
        message = " ".join(str(error).split()).strip() or error.__class__.__name__

        if len(message) > 220:
            message = f"{message[:217]}..."

        if status_code is not None and f"{status_code}" not in message:
            return f"HTTP {status_code}: {message}"

        return message

    def _should_retry(self, error: Exception) -> bool:
        status_code = self._extract_status_code(error)
        if status_code in RETRYABLE_STATUS_CODES:
            return True

        error_text = self._format_error(error).lower()
        return any(keyword in error_text for keyword in RETRYABLE_KEYWORDS)

    def _request_summary(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        result = (response.text or "").strip()
        if not result:
            raise RuntimeError("Gemini 返回空内容。")
        return result

    def _build_fallback_report(self, intel_list: list[dict[str, str]], reason: str) -> str:
        lines = [
            "## 系统说明",
            "",
            "> 本次为 AI 摘要失败后的 fallback 简报，仅保留基础信息以保证当日产物不断档。",
        ]

        if reason:
            lines.extend(["", f"> 失败原因：{reason}"])

        lines.extend(
            [
                "",
                f"## 今日新内容速览（共 {len(intel_list)} 条）",
                "",
            ]
        )

        for index, item in enumerate(intel_list, start=1):
            lines.extend(
                [
                    f"### [{index}] {item['title']}",
                    f"- 来源：{item['origin']}",
                    f"- 原文链接：{item['url']}",
                    "",
                ]
            )

        return "\n".join(lines).rstrip() + "\n"

    def summarize(self, intel_list: list[dict[str, str]]) -> str:
        if not intel_list:
            return "今日无重大情报。"

        prompt = self._build_prompt(intel_list)
        last_error: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                print(f"[Gemini] 正在进行第 {attempt}/{self.max_attempts} 次摘要请求...")
                summary = self._request_summary(prompt)
                if attempt > 1:
                    print(f"[Gemini] 第 {attempt} 次请求成功，继续生成正式日报。")
                return summary
            except Exception as error:
                last_error = error
                error_text = self._format_error(error)
                has_next_attempt = attempt < self.max_attempts

                print(f"[Gemini] 第 {attempt} 次请求失败：{error_text}")

                if has_next_attempt and self._should_retry(error):
                    wait_seconds = self.retry_delays[attempt - 1]
                    print(
                        f"[Gemini] 判定为可重试错误，将在 {wait_seconds} 秒后发起下一次请求。"
                    )
                    time.sleep(wait_seconds)
                    continue

                if has_next_attempt:
                    print("[Gemini] 判定为不可重试错误，将直接生成 fallback 简报。")
                else:
                    print("[Gemini] 已达到最大重试次数，将生成 fallback 简报。")
                break

        fallback_reason = self._format_error(last_error) if last_error else "未知错误"
        print("[Gemini] AI 摘要不可用，开始生成 fallback 简报。")
        return self._build_fallback_report(intel_list, reason=fallback_reason)
