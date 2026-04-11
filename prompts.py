# ──────────────────────────────────────────────
# 優化重點（對照 Google Prompting Strategies）
# ──────────────────────────────────────────────
# 1. XML 標籤結構化  — 用 <reference>, <items>, <example> 等標籤清楚區隔 prompt 區塊
# 2. Few-shot example — 提供一組完整的 input → output 範例，引導模型格式與語氣
# 3. Locale 定義      — 明確定義每個 locale 的語言特性與差異（zh-HK vs zh-Hant）
# 4. Format placeholder 保留規則 — 明確要求保留 %@, %d, %lld, \n 等佔位符
# 5. System instruction 分離    — 穩定指令抽成 SYSTEM_INSTRUCTION，動態內容留在 user prompt
# 6. Context-first 順序         — reference（context）放前面，task 放後面
# ──────────────────────────────────────────────


SYSTEM_INSTRUCTION = '''
<role>
You are a professional UI copywriter and localizer for Hikingbook, a hiking and outdoor activity app.
You specialize in translating and polishing short UI strings (buttons, labels, snackbars, dialogs) across locales.
You are precise, consistent, and always match the brand's established tone.
</role>

<brand_tone>
- Friendly, encouraging, and concise
- Keep UI strings short and actionable — avoid verbose or formal phrasing
</brand_tone>

<locale_definitions>
- en: English — natural, polished UI copy. Use sentence case for titles and buttons.
- zh-Hant: 繁體中文（台灣）— 台灣用語。例：帳號、登入、紀錄、註冊
- zh-HK: 繁體中文（香港）— 香港用語，與台灣繁體有細微差異。例：帳戶（非帳號）、返嚟（非回來）
- zh-Hans: 简体中文（中国大陆）— 大陆用语。例：账号、登录、记录、注册
</locale_definitions>

<constraints>
- MUST preserve all format specifiers exactly as-is: %@, %d, %lld, %1$@, %2$@, \\n, etc.
- MUST preserve leading/trailing spaces or punctuation if present in the source string.
- Preserve the existing locale value by default if it is present and non-empty, unless it contains an obvious error.
- Every locale MUST have a non-empty value in the output.
- Use "你" (not "您") for addressing users
- If a locale value is marked [LOCKED], you MUST return it exactly as-is. Do not modify, rephrase, or "improve" locked values.

These terms MUST be translated exactly as specified — no synonyms, no paraphrasing:

| English             | zh-Hant        | zh-HK          | zh-Hans        |
|---------------------|----------------|-----------------|---------------|
| 3D flyover video    | 3D鳥瞰影片      | 3D鳥瞰影片        |3D鸟瞰视频      |
| waypoint            | 紀錄點          | 紀錄點           | 记录点         |
| trail-goers         | 山友           | 山友             | 山友           |
| snapshot            | 快照           | 快照             | 快照           |
</constraints>

<output_format>
Reply with ONLY a valid JSON array. Each element must have:
  "index": (integer matching the [N] bracket in the items),
  "en": "...",
  "zh-Hant": "...",
  "zh-HK": "...",
  "zh-Hans": "..."

No explanation, no markdown fences, no extra text. Only the raw JSON array.
</output_format>'''


USER_PROMPT_TEMPLATE = '''<reference>
The following are existing approved translations for Hikingbook. Use them to learn the brand's tone, terminology, and locale-specific conventions. Do NOT translate these — they are for reference only.

{reference_block}
</reference>

<example>
Here is an example of the expected input and output format:

Input:
[0] Key: account_view.button.continue
  en: Continue
  zh-Hant: 
  zh-HK: 
  zh-Hans: 

[1] Key: account_view.dialog_message.sync_warning
  en: Your data will be synced to %@. Continue?
  zh-Hant: 你的資料將同步至 %@。是否繼續？
  zh-HK: 
  zh-Hans: 

[2] Key: activity_name_view.text.name_this_activity
  en: Name your activity [LOCKED]
  zh-Hant: 為你的活動命名
  zh-HK: 
  zh-Hans: 

Expected output:
[{{"index": 0, "en": "Continue", "zh-Hant": "繼續", "zh-HK": "繼續", "zh-Hans": "继续"}}, {{"index": 1, "en": "Your data will be synced to %@. Continue?", "zh-Hant": "你的資料將同步至 %@。是否繼續？", "zh-HK": "你的資料將同步至 %@。是否繼續？", "zh-Hans": "你的数据将同步至 %@。是否继续？"}}, {{"index": 2, "en": "Name your activity", "zh-Hant": "為你的活動命名", "zh-HK": "為你的活動命名", "zh-Hans": "为你的活动命名"}}]
</example>

<items>
Now translate the following items for ALL locales ({locales_needed}).

{items_block}
</items>'''


def format_reference_block(
    references: list[dict[str, str]],
    locales: list[str],
) -> str:
    """將 reference.xcstrings 的翻譯格式化為 prompt 中的參考區塊。"""
    blocks = []
    for ref in references:
        lines = [f"Key: {ref['key']}"]
        for locale in locales:
            value = ref.get(locale, "")
            if value:
                lines.append(f"  {locale}: {value}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def format_items_block(
    batch: list[dict[str, str]],
    locale_columns: dict[str, str],
    skip_reason: str = "en:needs_review",
) -> str:
    """將待翻譯的 rows 格式化為 prompt 中的任務區塊。
    
    若 row 的 reason == skip_reason，在 en 值後面標註 [LOCKED]，
    讓模型知道該欄位不可修改。
    """
    blocks = []
    for idx, item in enumerate(batch):
        lines = [f"[{idx}] Key: {item['key']}"]
        is_en_locked = item.get("reason", "").strip() == skip_reason
        for locale, column_name in locale_columns.items():
            value = item.get(column_name, "")
            suffix = " [LOCKED]" if locale == "en" and is_en_locked and value else ""
            if value:
                lines.append(f"  {locale}: {value}{suffix}")
            else:
                lines.append(f"  {locale}: ")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def build_prompt(
    reference: list[dict[str, str]],
    batch: list[dict[str, str]],
    locale_columns: dict[str, str],
) -> str:
    """組合 user prompt（不含 system instruction，system instruction 應透過 API 參數傳入）。"""
    reference_block = format_reference_block(reference, list(locale_columns.keys()))
    items_block = format_items_block(batch, locale_columns)
    locales_needed = ", ".join(list(locale_columns.keys()))

    return USER_PROMPT_TEMPLATE.format(
        reference_block=reference_block,
        items_block=items_block,
        locales_needed=locales_needed,
    )


if __name__ == "__main__":
    # 模擬 locale_columns
    locale_columns = {
        "zh-Hant": "zh-Hant_value",
        "zh-HK": "zh-HK_value",
        "zh-Hans": "zh-Hans_value",
        "en": "en_value",
    }

    # 模擬 references（從 reference.xcstrings 來的）
    references = [
        {
            "key": "account_view.button.log_in_another_account",
            "zh-Hant": "登入其他帳號",
            "zh-HK": "登入其他帳戶",
            "zh-Hans": "登录其他账号",
            "en": "Log in to another account",
        },
        {
            "key": "account_view.title.welcome_back",
            "zh-Hant": "歡迎回來！",
            "zh-HK": "歡迎返嚟！",
            "zh-Hans": "欢迎回来！",
            "en": "Great to see you again!",
        },
    ]

    # 模擬 batch（從 input.csv 來的，注意欄位名有 _value）
    batch = [
        {
            "key": "activity_detail_view.snackbar.feel_free_to_share_it_later",
            "reason": "missing_localizations",
            "en_value": "Activity saved. Share it whenever you're ready.",
            "zh-Hant_value": "",
            "zh-HK_value": "",
            "zh-Hans_value": "",
        },
        {
            "key": "activity_name_view.text.name_this_activity",
            "reason": "en:needs_review",
            "en_value": "Name your activity",
            "zh-Hant_value": "為你的活動命名",
            "zh-HK_value": "",
            "zh-Hans_value": "",
        },
    ]

    # 測試每個 function
    print("=== System Instruction ===")
    print(SYSTEM_INSTRUCTION)

    print("\n=== User Prompt ===")
    print(build_prompt(references, batch, locale_columns))
