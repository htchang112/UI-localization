# Hikingbook UI Text Localization Tool

An AI-powered CLI tool that helps engineers localize Hikingbook's UI strings across four locales (**English**, **繁體中文 台灣**, **繁體中文 香港**, **简体中文**), using Google Gemini to generate translations that match the app's brand tone and terminology.

Copywriters can review the AI output directly in CSV — no manual first-draft work needed.

## How It Works

1. **Reads** `reference.xcstrings` — existing approved translations that teach the model Hikingbook's voice, glossary, and locale conventions.
2. **Reads** `input.csv` — the rows that need localization. Each row has a `key`, a `reason`, and value columns for each locale.
3. **Calls Gemini** in batches of 10 rows, sending the reference context + items to translate.
4. **Writes** `output.csv` — a copy of the input with all locale columns filled in by the AI.

### Special handling

- **`en:needs_review` rows** — When the `reason` column is `en:needs_review`, the English value is locked and returned unchanged. Other locales for that row are still translated/polished.
- **Existing values** — If a locale already has a value, the model preserves it unless it spots an obvious error.
- **Format specifiers** — `%@`, `%d`, `%lld`, `\n`, etc. are preserved exactly as-is. _Note: The current input.csv does not contain format specifiers, but this handling is included proactively to support future inputs._

## Prerequisites

- Python 3.10+
- A [Google Gemini API key](https://ai.google.dev/) (free tier works)

## Setup

```bash
# Clone the repo
git clone https://github.com/<your-username>/hikingbook-localization-tool.git
cd hikingbook-localization-tool

# Install dependencies
pip install google-genai python-dotenv

# Add your API key
echo "GEMINI_API_KEY=your_key_here" > .env
```

## Usage

```bash
python3 main.py reference.xcstrings input.csv
```

This generates `output.csv` in the current directory.

### Example output

```
$ python3 main.py reference.xcstrings input.csv
   16 reference strings loaded.
   36 rows loaded.
Calling Gemini for localization...
  → Translating rows 1–10 …
  → Translating rows 11–20 …
  → Translating rows 21–30 …
  → Translating rows 31–36 …
Output file saved: output.csv
```

### Input CSV format

The tool expects a CSV with at least these columns:

| Column          | Description                                                                |
| --------------- | -------------------------------------------------------------------------- |
| `key`           | The string key (e.g. `alert_view.title.share_the_activity`)                |
| `reason`        | Why this row needs work (`missing_localizations`, `en:needs_review`, etc.) |
| `en_value`      | English text                                                               |
| `zh-Hant_value` | Traditional Chinese (Taiwan)                                               |
| `zh-HK_value`   | Traditional Chinese (Hong Kong)                                            |
| `zh-Hans_value` | Simplified Chinese (China)                                                 |

Other columns (like `file_path`, `*_state`) are passed through unchanged.

## Project Structure

```
├── main.py              # Entry point — reads files, calls API, writes output
├── prompts.py           # System instruction + prompt templates
├── reference.xcstrings  # Approved translations (brand tone reference)
├── input.csv            # Strings to localize
└── .env                 # GEMINI_API_KEY (not committed)
```

| File         | Role                                                                                                                                         |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `main.py`    | Orchestration: CSV I/O, batching, Gemini API calls, retry logic                                                                              |
| `prompts.py` | Prompt engineering: system instruction with brand tone, glossary, locale rules, and the user prompt template that formats references + items |

## Configuration

All tunable constants live at the top of `main.py`:

| Constant      | Default                  | Purpose                                    |
| ------------- | ------------------------ | ------------------------------------------ |
| `MODEL_NAME`  | `gemini-3-flash-preview` | Gemini model to use                        |
| `SKIP_REASON` | `en:needs_review`        | Reason value that locks the English column |
| `BATCH_SIZE`  | `10`                     | Rows per API call (in `localize_rows`)     |

## Troubleshooting

| Problem                           | Fix                                                                                                                             |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `GEMINI_API_KEY not set`          | Create a `.env` file with `GEMINI_API_KEY=...`                                                                                  |
| `Gemini API failed after retries` | Check your quota at [Google AI Studio](https://aistudio.google.com/); the free tier has rate limits                             |
| Garbled output encoding           | The tool writes UTF-8 with BOM (`utf-8-sig`) for Excel compatibility. Open in a text editor or spreadsheet that supports UTF-8. |

## Roadmap

### Reference Filtering by Key Category

As `reference.xcstrings` grows, sending all entries in every prompt becomes costly. A future improvement is to categorize keys by their prefix (e.g. `account_view.*`, `alert_view.*`, `map_3d_*`) and only inject references that share the same category as the current batch. This keeps the prompt focused and reduces token usage significantly — especially when the reference file scales to hundreds or thousands of entries.

### Key-Aware Localization Style

UI keys encode context: `*.button.*` implies short, actionable text; `*.description.*` allows longer explanations; `*.title.*` sits somewhere in between. When the token budget allows, the tool could parse key segments and inject per-category style guidance into the prompt — telling the model to keep button translations under ~4 characters in CJK, allow descriptions to be more conversational, and so on. This turns the key itself into a localization signal rather than just an identifier.

## Maintainer

Built as an internship project at [Hikingbook](https://hikingbook.net).
