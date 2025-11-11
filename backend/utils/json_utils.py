import json
import re

def extract_json_block(text: str):
    """
    Extracts and cleans a JSON-like block from GPT replies that may include
    Markdown fences, math expressions, or extra commentary.
    """
    if not text:
        return None

    # 1️⃣ Remove Markdown fences (```json ... ```)
    cleaned_text = re.sub(r"```(?:json)?", "", text)
    cleaned_text = cleaned_text.replace("```", "").strip()

    # 2️⃣ Find first JSON-like section
    match = re.search(r"\{.*\}", cleaned_text, re.DOTALL)
    if not match:
        return None

    raw_json = match.group(0)

    # 3️⃣ Replace math expressions like "1.22 * 1.25 * 1.25"
    raw_json = re.sub(r"(\d+(?:\.\d+)?)\s*\*\s*(\d+(?:\.\d+)?)\s*\*\s*(\d+(?:\.\d+)?)",
                      lambda m: str(round(float(m.group(1)) * float(m.group(2)) * float(m.group(3)), 3)),
                      raw_json)

    # 4️⃣ Fix common issues
    raw_json = raw_json.replace("'", '"')
    raw_json = re.sub(r",\s*}", "}", raw_json)
    raw_json = re.sub(r",\s*]", "]", raw_json)

    # 5️⃣ Try to load JSON
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError:
        return None
    """
    Extracts and parses the first valid JSON block from a mixed GPT reply.
    Handles text before/after JSON and single/double quote mismatches.
    """
    if not text:
        return None

    # Try to find the first JSON block
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        return None

    raw_json = match.group(0)

    # Replace single quotes with double quotes carefully
    cleaned = raw_json.replace("'", '"')

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Sometimes there are trailing commas or formatting issues
        cleaned = re.sub(r",\s*}", "}", cleaned)
        cleaned = re.sub(r",\s*]", "]", cleaned)
        try:
            return json.loads(cleaned)
        except Exception:
            return None
