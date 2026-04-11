import csv
import json
import time
import re
import sys
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

from prompts import build_prompt, SYSTEM_INSTRUCTION

 
load_dotenv()

# --- Constants ---
LOCALE_COLUMNS = {
    "zh-Hant": "zh-Hant_value",
    "zh-HK": "zh-HK_value",
    "zh-Hans": "zh-Hans_value",
    "en": "en_value",
}
SKIP_REASON = "en:needs_review"
MODEL_NAME = "gemini-3-flash-preview"
BATCH_SIZE = 10


# --- Functions ---

# 1. Read reference.xcstrings 
def load_xcstring(path: str) -> list:
    with open(path, encoding="utf-8") as ref:
        data = json.load(ref)
    references = []
    for key, entry in data.get("strings", {}).items():
        locs = entry.get("localizations", {})
        ref_entry = {"key": key}
        for locale in LOCALE_COLUMNS:
            loc = locs.get(locale, {})
            ref_entry[locale] = loc.get("stringUnit", {}).get("value", "")
        if any(ref_entry[l] for l in LOCALE_COLUMNS):
            references.append(ref_entry)
    return references

# 2. Read input.csv
def load_input_csv(path: str) -> tuple[list[dict[str, str]], list[str]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    return rows, fieldnames

# 3. Call API
def call_gemini(prompt: str, api_key: str, retries: int = 3) -> list[dict]:
    client = genai.Client(api_key=api_key)
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    temperature=0.5,
                ),
            )
            text = response.text.strip()
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            return json.loads(text)
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            if attempt < retries -1:
                time.sleep(3)
    raise RuntimeError("Gemini API failed after retries.")


# 4. Process batch
def localize_rows(rows, references, api_key, batch_size=BATCH_SIZE):
    results = [dict(r) for r in rows]

    for batch_start in range(0, len(rows), batch_size):
        batch_rows = rows[batch_start: batch_start + batch_size]
        print(f"  → Translating rows {batch_start+1}–{batch_start+len(batch_rows)} …")

        prompt = build_prompt(references, batch_rows, locale_columns=LOCALE_COLUMNS)
        translations = call_gemini(prompt, api_key)

        trans_map = {t["index"]: t for t in translations}
        for local_i, row in enumerate(batch_rows):
            global_i = batch_start + local_i
            t = trans_map.get(local_i)
            if not t:
                continue

            for locale, col in LOCALE_COLUMNS.items():
                if col not in results[global_i]:
                    continue
                # 關鍵：en:needs_review 的 row，en 欄位保持原值不動
                if row.get("reason", "").strip() == SKIP_REASON and locale == "en":
                    continue
                results[global_i][col] = t.get(locale, results[global_i].get(col, ""))

        if batch_start + batch_size < len(rows):
            time.sleep(2)

    return results

# 5. write output.csv
def write_output_csv(rows: list, fieldnames: list, path: str):
    with open(path, "w", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Output file saved: {path}")

# --- Main ---
def main():
    if len(sys.argv) != 3:
        print("Usage: python3 main.py reference.xcstrings input.csv")
        sys.exit(1)
    xcstrings_path, input_csv_path = sys.argv[1], sys.argv[2]
    
    api_key = os.getenv("GEMINI_API_KEY")    
    if not api_key:
        print("GEMINI_API_KEY not set. Add it to your .env file.")
        sys.exit(1)

    references = load_xcstring(xcstrings_path)
    print(f"   {len(references)} reference strings loaded.")

    rows, fieldnames = load_input_csv(input_csv_path)
    print(f"   {len(rows)} rows loaded.")

    print("Calling Gemini for localization...")
    localized = localize_rows(rows, references, api_key)

    write_output_csv(localized, fieldnames, "output.csv")

if __name__ == "__main__":
    main()
