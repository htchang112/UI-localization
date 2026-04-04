PROMPT_TEMPLATE = '''You are a professional UI copywriter and localizer for a hiking app called Hikingbook.
Your job is to provide accurate, natural-sounding translations that match the brand's tone.

## Brand tone & style
- Friendly, encouraging, and concise
- Keep UI strings short and actionable
- Match the style of the reference translations below

## Reference translations (existing approved strings)
{reference_block}

## Task
For each item below, provide translations for ALL of these locales: {locales_needed}
- If a locale value is already provided, you may improve/revise it if needed, OR keep it as-is
- If a locale value is missing, provide a translation
- For the "en" locale, ensure the English copy is polished and natural

## Items to translate
{items_block}

## Output format
Reply with ONLY a JSON array. Each element must have:
  "index": (the number in brackets above),
  "en": "...",
  "zh-Hant": "...",
  "zh-HK": "...",
  "zh-Hans": "..."

No explanation, no markdown, no extra text. Only the JSON array.'''


def format_reference_block(
    references: list[dict[str, str]], #這邊輸入是 load_xcstring() 這個 function 的輸出，也就是一個 list，裡面每個元素都是一個 dict，格式像這樣 {"key": "some_key", "zh-Hant": "some translation", "zh-HK": "some translation", "zh-Hans": "some translation", "en": "some translation"}
    locales: list[str], #這邊輸入應該是 LOCALE_COLUMNS 的 keys，也就是 ["zh-Hant", "zh-HK", "zh-Hans", "en"]
) -> str:
    blocks = []
    for ref in references:
        lines = [f"Key: {ref['key']}"]
        for locale in locales:
            value = ref.get(locale, "") 
            if value:
                lines.append(f" {locale}: {value}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)

def format_items_block(
        batch: list[dict[str, str]], #input.csv 裡面需要翻譯的那些 row（已經過濾掉 en:needs_review 的）
        locale_columns: dict[str, str], #LOCALE_COLUMNS
) -> str:
    blocks = []
    for id, item in enumerate(batch):
        lines = [f"[{id}] Key: {item['key']}"]
        for locale, column_name in locale_columns.items():
            value = item.get(column_name, "")
            if value:
                lines.append(f" {locale}: {value}")
            else:
                lines.append(f" {locale}: ")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)

