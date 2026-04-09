import csv
import json
import time
import re
import sys
import os
from google import genai
from dotenv import load_dotenv

from prompts import build_prompt

 
load_dotenv()

# interavtive python 測試輸入
XCSTRINGS_PATH = "reference.xcstrings"
INPUT_CSV_PATH = "input.csv"

# --- Constants ---
LOCALE_COLUMNS = {
    "zh-Hant": "zh-Hant_value",
    "zh-HK": "zh-HK_value",
    "zh-Hans": "zh-Hans_value",
    "en": "en_value",
}
SKIP_REASON = "en:needs_review"
MODEL_NAME = "gemini-3-flash-preview" #選擇這個模型的原因是因為這是最新一代的當中，專為文字的輕量模型。


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
def localize_rows(rows: list, references: list, api_key: str, batch_size: int = 10) -> list:
    results = [dict(r) for r in rows]

    to_translate_indices = [
        i for i, r in enumerate(rows)
        if r.get("reason", "").strip() != SKIP_REASON
    ]
    skipped = len(rows) - len(to_translate_indices)
    print(f"  → {len(to_translate_indices)} rows to localize, {skipped} skipped (en:needs_review)")

    for batch_start in range(0, len(to_translate_indices), batch_size):
        batch_idx = to_translate_indices[batch_start: batch_start + batch_size]
        batch_rows = [rows[i] for i in batch_idx]

        print(f"  → Translating rows {batch_start+1}–{batch_start+len(batch_idx)} …")
        prompt = build_prompt(references, batch_rows, locale_columns=LOCALE_COLUMNS)
        translations = call_gemini(prompt, api_key)

        trans_map = {t["index"]: t for t in translations}
        for local_i, global_i in enumerate(batch_idx):
            t = trans_map.get(local_i)
            if not t:
                print(f"No translation for index {local_i} (key: {batch_rows[local_i]['key']})")
                continue
            for locale, col in LOCALE_COLUMNS.items():
                if col in results[global_i]:
                    results[global_i][col] = t.get(locale, results[global_i].get(col, ""))

        if batch_start + batch_size < len(to_translate_indices):
            time.sleep(2)

    return results

# 5. write output.csv
def write_output_csv(rows: list, fieldnames: list, path: str):
    with open(path, "w", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Output file saved: {path}")

# --- Main ---
def main():
    xcstrings_path, input_csv_path = sys.argv[1], sys.argv[2]
    api_key = os.getenv("GEMINI_API_KEY")

    references = load_xcstring(xcstrings_path)
    print(f"   {len(references)} reference strings loaded.")

    rows, fieldnames = load_input_csv(input_csv_path)
    print(f"   {len(rows)} rows loaded.")

    print("Calling Gemini for localization...")
    localized = localize_rows(rows, references, api_key)

    write_output_csv(localized, fieldnames, "output.csv")
    print("result have saved in output.csv")

if __name__ == "main":
    main()