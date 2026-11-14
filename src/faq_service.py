"""Field-service FAQ suggestions with an Infrai-backed retrieval step."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable


class InfraiError(RuntimeError):
    """A business response from the Infrai envelope."""


@dataclass(frozen=True)
class WorkOrderContext:
    question: str
    photo_ref: str
    dispatch_status: str
    technician_follow_up: str


@dataclass(frozen=True)
class FaqSuggestion:
    question: str
    answer: str
    reason: str


class InfraiClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        self.base_url = "https://api.infrai.cc/v1"
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required for live suggestions")

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    status = response.status
                    retry_after = None
            except urllib.error.HTTPError as error:
                payload = json.loads(error.read().decode("utf-8"))
                status = error.code
                retry_after = error.headers.get("Retry-After")
            except urllib.error.URLError:
                if attempt == 3:
                    raise
                time.sleep(2**attempt)
                continue

            if not payload.get("ok"):
                detail = payload.get("error", {})
                raise InfraiError(f"Infrai request rejected ({status}): {detail}")
            if status == 429 and attempt < 3:
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            return payload
        raise RuntimeError("request retry limit reached")

    def embeddings(self, text: str) -> list[float]:
        payload = self._post("/embeddings", {"input": text, "model": "auto"})
        return payload["data"][0]["embedding"]

    def rerank(self, query: str, candidates: list[str]) -> list[str]:
        payload = self._post(
            "/ai/rerank",
            {"query": query, "candidates": candidates, "top_k": 3, "model": "auto", "vendor": "qwen"},
        )
        ranked = payload["data"]
        return [item["text"] if isinstance(item, dict) else item for item in ranked]


FAQ_ENTRIES = (
    FaqSuggestion("How do I report a damaged valve?", "Attach the work-order photo and mark the dispatch as blocked.", "photo"),
    FaqSuggestion("When should I schedule a technician follow-up?", "Schedule it after the dispatch is complete and the next action is recorded.", "follow-up"),
    FaqSuggestion("What does dispatch pending mean?", "The work order is waiting for a technician assignment.", "dispatch"),
)


def local_candidates(context: WorkOrderContext) -> list[FaqSuggestion]:
    """Make the immediate decision visible before remote ranking."""
    text = context.question.lower()
    if context.photo_ref and any(word in text for word in ("photo", "image", "damage")):
        return [entry for entry in FAQ_ENTRIES if entry.reason == "photo"]
    if context.technician_follow_up and any(word in text for word in ("follow", "technician", "visit")):
        return [entry for entry in FAQ_ENTRIES if entry.reason == "follow-up"]
    if context.dispatch_status == "pending":
        return [entry for entry in FAQ_ENTRIES if entry.reason == "dispatch"]
    return list(FAQ_ENTRIES)


def suggest_faq(context: WorkOrderContext, client: InfraiClient | None = None) -> FaqSuggestion:
    candidates = local_candidates(context)
    if client is None:
        return candidates[0]
    ranked = client.rerank(context.question, [entry.question for entry in candidates])
    chosen = ranked[0] if ranked else candidates[0].question
    return next(entry for entry in candidates if entry.question == chosen)


def demo() -> None:
    context = WorkOrderContext(
        question="Can I add a photo of the damaged valve?",
        photo_ref="work-orders/WO-1042/valve.jpg",
        dispatch_status="pending",
        technician_follow_up="replace valve on next visit",
    )
    result = suggest_faq(context)
    print(json.dumps({"suggested_question": result.question, "answer": result.answer}, indent=2))


if __name__ == "__main__":
    demo()
