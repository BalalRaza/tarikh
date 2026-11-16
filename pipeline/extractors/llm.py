"""Stage 3: LLM extraction — Gemini Flash-Lite free tier."""

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

log = logging.getLogger(__name__)

load_dotenv()

# Lazy import — google-genai may not be installed for rules-only runs
_client = None
MODELS = ["gemini-2.5-flash-lite", "gemini-2.5-flash"]


def _get_client():
    global _client
    if _client is None:
        from google import genai
        from google.genai import types as _types

        _client = genai.Client(
            vertexai=True,
            project=os.environ["GOOGLE_CLOUD_PROJECT"],
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
            http_options=_types.HttpOptions(timeout=120),
        )
    return _client


SYSTEM_PROMPT = """You refine pre-extracted events from classical Arabic historical texts.

Given:
- Arabic section text
- Pre-extracted fields (date_ah, event_type) from rule-based extraction

For each discrete event, output:
- section: the section number (integer) this event came from
- title_ar: Arabic title (5-10 words)
- title_en: English title
- summary_ar: 1-2 sentence Arabic summary
- summary_en: 1-2 sentence English summary
- importance: 1 (era-defining, e.g. major battles, Prophet's key events, caliphate changes) | 2 (significant regional event) | 3 (minor detail)
- people: array of { name_ar, name_en, role }

RULES:
- Extract ONLY what the Arabic text says. Do not add external knowledge.
- Multiple events may exist in one section. Extract all.
- The input contains one or more numbered sections. Tag every event with its source section number.
- Respond with ONLY a JSON array. No markdown, no preamble."""


@dataclass
class LLMResult:
    title_ar: str = ""
    title_en: str = ""
    summary_ar: str = ""
    summary_en: str = ""
    importance: int = 3
    people: list[dict] = field(default_factory=list)


def _build_prompt(sections_with_rules: list[dict]) -> str:
    """Build prompt with section text + pre-extracted rule fields."""
    parts = [SYSTEM_PROMPT, ""]
    for i, item in enumerate(sections_with_rules):
        parts.append(f"--- Section {i + 1} ---")
        parts.append(f"Pre-extracted: date_ah={item.get('date_ah')}, type={item.get('event_type')}")
        if item.get("parent_headers"):
            parts.append("Headers: " + " > ".join(item["parent_headers"]))
        parts.append("Text:")
        parts.append(item["arabic_text"])
        parts.append("")
    return "\n".join(parts)


def _retry_delay(err: str) -> float:
    m = re.search(r"retry in (\d+\.?\d*)s", err, re.IGNORECASE)
    return float(m.group(1)) + 3 if m else 60.0


def call_llm(sections_with_rules: list[dict], model_index: int = 0, retries: int = 5) -> list[dict]:
    """Call Gemini and return list of extracted event dicts."""
    from google.genai import types

    client = _get_client()
    model = MODELS[model_index % len(MODELS)]
    prompt = _build_prompt(sections_with_rules)

    for attempt in range(retries):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            return json.loads(resp.text)
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                delay = _retry_delay(err)
                log.warning("Rate limited (%s). Waiting %.0fs...", model, delay)
                time.sleep(delay)
            else:
                log.error("Attempt %d failed (%s): %s", attempt + 1, model, e)
                if attempt < retries - 1:
                    time.sleep(2**attempt)
    return []


def make_batches(items: list[dict], batch_chars: int = 20000, max_per_batch: int = 8) -> list[list[dict]]:
    """Group sections into batches by char budget to cut LLM call count.

    A section larger than batch_chars goes alone. Otherwise sections accumulate
    until adding the next would exceed batch_chars or max_per_batch.
    """
    batches = []
    cur: list[dict] = []
    cur_chars = 0
    for item in items:
        cc = item.get("char_count", 0)
        if cur and (cur_chars + cc > batch_chars or len(cur) >= max_per_batch):
            batches.append(cur)
            cur = []
            cur_chars = 0
        cur.append(item)
        cur_chars += cc
    if cur:
        batches.append(cur)
    return batches


class ProgressTracker:
    """Track completed section IDs for resumability."""

    def __init__(self, progress_file: str = ".llm_progress.json"):
        self.path = Path(progress_file)
        self.done: set[str] = set()
        if self.path.exists():
            self.done = set(json.loads(self.path.read_text()))

    def is_done(self, section_id: str) -> bool:
        return section_id in self.done

    def mark_done(self, section_ids: list[str]):
        self.done.update(section_ids)
        self.path.write_text(json.dumps(sorted(self.done)))

    def reset(self):
        self.done = set()
        self.path.unlink(missing_ok=True)
