import csv
import json
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
MODLE_NAME = "gemini-3-flash-preview" #選擇這個模型的原因是因為這是最新一代的當中，專為文字的輕量模型。


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

# 4. Call API

# 5. Process batch

# 6. write output.csv
def write_output_csv(rows: list, fieldnames: list, path: str):
    with open(path, "w", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Output file saved: {path}")

# --- Main ---

