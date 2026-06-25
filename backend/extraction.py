import json
import os
import tempfile

import pandas as pd
from emergentintegrations.llm.chat import FileContentWithMimeType, LlmChat, UserMessage

EXTRACTION_SYSTEM = """You are a precise financial data extraction engine for a company's weekly \
collection & sales meeting report. You are given a document (PDF / CSV) that contains, per sales \
representative, the OUTSTANDING COLLECTION amounts split into aging buckets (90 days, 60 days, 30 days) \
across two separate companies named MBS and MCORP, plus performance numbers and a quotation pipeline.

Return ONLY valid minified JSON (no markdown, no commentary) matching EXACTLY this schema:
{
  "meeting_date": "YYYY-MM-DD or empty string",
  "period_start": "YYYY-MM-DD or empty string",
  "period_end": "YYYY-MM-DD or empty string",
  "reps": [
    {
      "name": "string",
      "aging": {
        "d90": {"mbs": number, "mcorp": number},
        "d60": {"mbs": number, "mcorp": number},
        "d30": {"mbs": number, "mcorp": number},
        "othera": {"mbs": number, "mcorp": number}
      },
      "performance": {
        "purchase": {"mbs": number, "mcorp": number},
        "sales": {"mbs": number, "mcorp": number},
        "coll_per_day": number,
        "coll_pct": number,
        "new_target": number,
        "last_week_target": number
      }
    }
  ],
  "quotation": {
    "prepair": {"mbs": number, "mcorp": number},
    "conform": {"mbs": number, "mcorp": number},
    "pending": {"mbs": number, "mcorp": number},
    "under_process": {"mbs": number, "mcorp": number},
    "not_conform": {"mbs": number, "mcorp": number}
  }
}

Rules:
- All numbers must be plain numbers (no commas, no currency symbols, no quotes).
- If a value is missing, use 0. If dates are missing, use "".
- "othera" means the OTHER / miscellaneous collection bucket if present, else all 0.
- Do not invent representatives that are not in the document.
"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)
        text = text[1] if len(text) > 1 else ""
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    # take the first {...} block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return text.strip()


def _prepare_file(file_path: str, filename: str):
    """Return (path, mime) suitable for the LLM. Excel is converted to CSV text."""
    lower = filename.lower()
    if lower.endswith((".pdf",)):
        return file_path, "application/pdf"
    if lower.endswith((".csv", ".txt")):
        return file_path, "text/csv"
    if lower.endswith((".xlsx", ".xls")):
        sheets = pd.read_excel(file_path, sheet_name=None, header=None)
        parts = []
        for name, frame in sheets.items():
            parts.append(f"### SHEET: {name}")
            parts.append(frame.fillna("").to_csv(index=False, header=False))
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        tmp.write("\n".join(parts))
        tmp.close()
        return tmp.name, "text/csv"
    # default attempt as csv
    return file_path, "text/csv"


async def extract_meeting(file_path: str, filename: str) -> dict:
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY is not configured")

    prepared_path, mime = _prepare_file(file_path, filename)

    chat = LlmChat(
        api_key=api_key,
        session_id=f"extract-{os.path.basename(file_path)}",
        system_message=EXTRACTION_SYSTEM,
    ).with_model("gemini", "gemini-2.5-pro")

    attachment = FileContentWithMimeType(file_path=prepared_path, mime_type=mime)
    message = UserMessage(
        text="Extract the meeting data from the attached file and return ONLY the JSON.",
        file_contents=[attachment],
    )

    raw = await chat.send_message(message)
    if not isinstance(raw, str):
        raw = str(raw)
    cleaned = _strip_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse extracted data: {exc}. Raw output: {raw[:500]}")
