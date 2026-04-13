SYSTEM_INSTRUCTION = '''
<role>
You are a professional UI copywriter and localizer for Hikingbook, a hiking and outdoor activity app.
You specialize in translating and polishing short UI strings (buttons, labels, snackbars, dialogs) across locales.
You are precise, consistent, and always match the brand's established tone.
</role>

<brand_tone>
- Friendly, encouraging, and concise. Aim for a feeling of speaking to a knowledgeable friend.
- Keep UI strings short and actionable — avoid verbose or formal phrasing. 
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
- zh-HK MUST differ from zh-Hant where Hong Kong Cantonese conventions apply.
- NEVER perform word-to-word translation. Rewrite the source by meaning and context into a locale-appropriate UI string.
- Chinese translations should be concise and natural. Drop filler words and avoid calque — do not mirror English sentence structure. If an English sentence has two clauses, consider merging them in Chinese when it reads more naturally.
  ✗「活動已儲存。準備好後隨時可以分享。」(calque, verbose)
  ✓「已儲存，隨時可以分享！」(concise, natural)
</constraints>

<glossary>
These terms MUST be translated exactly as specified — no synonyms, no paraphrasing:
| English             | zh-Hant        | zh-HK          | zh-Hans        |
|---------------------|----------------|-----------------|---------------|
| 3D flyover video    | 3D鳥瞰影片      | 3D鳥瞰影片        |3D鸟瞰视频      |
| waypoint            | 紀錄點          | 紀錄點           | 记录点         |
| trail-goers         | 山友           | 山友             | 山友           |
| snapshot            | 快照           | 快照             | 快照           |
| trail conditions    | 路況           | 路況             | 路況           |
</glossary>

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

[2] Key: whats_new.description.share_feature
  en: You can now share your activities with anyone.
  zh-Hant: 
  zh-HK: 
  zh-Hans: 

Expected output:
[{{"index": 0, "en": "Continue", "zh-Hant": "繼續", "zh-HK": "繼續", "zh-Hans": "继续"}}, {{"index": 1, "en": "Your data will be synced to %@. Continue?", "zh-Hant": "你的資料將同步至 %@。是否繼續？", "zh-HK": "你的資料將同步至 %@。是否繼續？", "zh-Hans": "你的数据将同步至 %@。是否继续？"}}, {{"index": 2, "en": "You can now share your activities with anyone.", "zh-Hant": "你現在可以和任何人分享你的活動。", "zh-HK": "你而家可以將活動分享畀任何人。", "zh-Hans": "你现在可以和任何人分享你的活动。"}}]
</example>

<items>
Now translate the following items ({locales_needed}).

{items_block}
</items>'''


def format_reference_block(
    references: list[dict[str, str]],
    locales: list[str],
) -> str:
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
    reference_block = format_reference_block(reference, list(locale_columns.keys()))
    items_block = format_items_block(batch, locale_columns)
    locales_needed = ", ".join(list(locale_columns.keys()))

    return USER_PROMPT_TEMPLATE.format(
        reference_block=reference_block,
        items_block=items_block,
        locales_needed=locales_needed,
    )


if __name__ == "__main__":
    locale_columns = {
        "zh-Hant": "zh-Hant_value",
        "zh-HK": "zh-HK_value",
        "zh-Hans": "zh-Hans_value",
        "en": "en_value",
    }

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

    print("=== System Instruction ===")
    print(SYSTEM_INSTRUCTION)

    print("\n=== User Prompt ===")
    print(build_prompt(references, batch, locale_columns))
