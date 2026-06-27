import json
import os
import tempfile

EXTRACTION_SYSTEM = """You are a precise financial data extraction engine for a company's weekly \
collection, sales & marketing meeting report. The document contains data split across TWO companies \
named MBS and MCORP. Extract everything into the exact JSON schema below.

Return ONLY valid minified JSON (no markdown, no commentary) matching EXACTLY this schema:
{
  "meeting_date": "YYYY-MM-DD or empty string",
  "period_start": "YYYY-MM-DD or empty string",
  "period_end": "YYYY-MM-DD or empty string",
  "reps": [
    {
      "name": "string (collection person)",
      "aging": {
        "d90": {"mbs": number, "mcorp": number},
        "d60": {"mbs": number, "mcorp": number},
        "d30": {"mbs": number, "mcorp": number},
        "othera": {"mbs": number, "mcorp": number}
      },
      "weekly_collection": {"mbs": number, "mcorp": number},
      "last_week_target": number,
      "working_days": 6
    }
  ],
  "branches": [
    {
      "name": "string (e.g. Sachin, Ankleshwar, Udhna, Kadodra)",
      "purchase": {"tons": {"mbs": number, "mcorp": number}},
      "sales":    {"tons": {"mbs": number, "mcorp": number}}
    }
  ],
  "quotation": {
    "prepair": {"mbs": number, "mcorp": number},
    "conform": {"mbs": number, "mcorp": number},
    "pending": {"mbs": number, "mcorp": number},
    "under_process": {"mbs": number, "mcorp": number},
    "not_conform": {"mbs": number, "mcorp": number}
  },
  "marketing_reps": [
    {
      "name": "string (marketing person)",
      "visit": {"mbs": number, "mcorp": number},
      "inquiry": {"mbs": number, "mcorp": number},
      "inquiry_conform": {"mbs": number, "mcorp": number},
      "order_loss": {"mbs": number, "mcorp": number}
    }
  ]
}

Rules:
- All numbers must be plain numbers (no commas, currency symbols or quotes). Missing -> 0. Missing dates -> "".
- "othera" is the OTHER / miscellaneous collection bucket (accounts not in 30/60/90 days).
- "weekly_collection" is the amount that person collected during the week, split into mbs and mcorp (the second small MBS/MCORP/TOTAL block under each collection person). If only a per-day TOTAL is shown, multiply by the working days (usually 6) for the total and split by company if the breakdown is given.
- For branches, capture the tonnage (tons) for purchase and sales, split by MBS and MCORP.
- Quotation values are COUNTS of quotations per stage. Marketing rep values are COUNTS of visits/inquiries.
- Do not invent people or branches that are not present in the document.

DOCUMENT LAYOUT NOTES (this specific weekly report):
- There are TWO companies in every section: MBS and MCORP. Many figures appear as
  "MBS <n>", "MCORP <n>", "TOTAL <n>" — capture mbs and mcorp; ignore the printed TOTAL
  (it is mbs+mcorp and is recomputed).
- COLLECTION PEOPLE: each "* <NAME> COLLECTION" block has, on the left, the aging buckets
  "90 DAYS", "60 DAYS", "30 DAYS" and "OTHERA" (the OTHER/miscellaneous bucket), each split
  MBS/MCORP, then a "TOTAL OS" or "TOTAL OT" line (grand total — ignore, it is derived).
  To the right of the name is a small MBS/MCORP/TOTAL block that is the WEEKLY COLLECTION
  for that person: use its TOTAL as "weekly_collection". "COLL/DAY" = weekly_collection / 6.
  "NEW TARGET" = 90+60+30 only and is recomputed (do not output it). "LAST WEEK TARGET"
  maps to "last_week_target".
- A person's name may also be a branch name (e.g. "Ankleshwar" is both a collection person
  AND a branch). Keep them as separate entities; do not merge.
- BRANCHES: blocks like "* SACHIN", "* ANKLESHWAR", "* UDHNA", "* KADODRA" (and possibly
  "DIRECTSALE") show PURCHASE and SALES in TONNAGE only, as "MBS MCORP TOTAL PER DAY".
  Capture mbs and mcorp tons for purchase and sales. Ignore the PER DAY column.
- QUOTATION stage labels in this report are spelled: PREPAIR, CONFORM, PENDING,
  UNDER PROCESS, NOT CONFORM -> map to prepair, conform, pending, under_process, not_conform.
- MARKETING PEOPLE (e.g. HITESH, GHANSHYAM, MEETBHAI) show per-branch visit figures plus
  "TOTAL VISIT", "TOTAL INQUIRY", "INQUIRY CONFORM", "ORDER LOSS" split MBS/MCORP ->
  visit, inquiry, inquiry_conform, order_loss. Use the TOTAL line for each, not per-branch.
- meeting_date is the "MEETING DT" value; period_start/period_end come from the date range
  printed near the top (e.g. "14-06-25 to 20-06-25"). Convert all dates to YYYY-MM-DD.
"""

USER_PROMPT = "Extract the meeting data from the attached file and return ONLY the JSON."


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
        import pandas as pd  # lazy import; only needed for Excel uploads
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


async def _extract_with_emergent(api_key: str, prepared_path: str, mime: str, file_path: str) -> str:
    """Original Emergent-platform path. Used when EMERGENT_LLM_KEY is set."""
    from emergentintegrations.llm.chat import FileContentWithMimeType, LlmChat, UserMessage

    chat = LlmChat(
        api_key=api_key,
        session_id=f"extract-{os.path.basename(file_path)}",
        system_message=EXTRACTION_SYSTEM,
    ).with_model("gemini", "gemini-2.5-pro")

    attachment = FileContentWithMimeType(file_path=prepared_path, mime_type=mime)
    message = UserMessage(text=USER_PROMPT, file_contents=[attachment])
    raw = await chat.send_message(message)
    return raw if isinstance(raw, str) else str(raw)


async def _extract_with_gemini(api_key: str, prepared_path: str, mime: str) -> str:
    """Portable path using Google's official google-genai SDK and a standard
    GEMINI_API_KEY (free from https://aistudio.google.com/app/apikey)."""
    import asyncio
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")

    def _run() -> str:
        with open(prepared_path, "rb") as fh:
            data = fh.read()
        resp = client.models.generate_content(
            model=model_name,
            contents=[
                types.Part.from_bytes(data=data, mime_type=mime),
                USER_PROMPT,
            ],
            config=types.GenerateContentConfig(system_instruction=EXTRACTION_SYSTEM),
        )
        return resp.text or ""

    # The SDK call is synchronous; run it off the event loop.
    return await asyncio.to_thread(_run)


async def extract_meeting(file_path: str, filename: str) -> dict:
    """Extract structured meeting data from an uploaded PDF/Excel/CSV.

    Provider selection (first match wins):
      1. EMERGENT_LLM_KEY  -> Emergent universal key (original behaviour)
      2. GEMINI_API_KEY    -> Google AI Studio key (portable, recommended)
    """
    emergent_key = os.environ.get("EMERGENT_LLM_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    if not emergent_key and not gemini_key:
        raise RuntimeError(
            "No AI key configured. Set GEMINI_API_KEY (recommended, free from "
            "https://aistudio.google.com/app/apikey) or EMERGENT_LLM_KEY."
        )

    prepared_path, mime = _prepare_file(file_path, filename)

    if emergent_key:
        raw = await _extract_with_emergent(emergent_key, prepared_path, mime, file_path)
    else:
        raw = await _extract_with_gemini(gemini_key, prepared_path, mime)

    cleaned = _strip_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse extracted data: {exc}. Raw output: {raw[:500]}")
