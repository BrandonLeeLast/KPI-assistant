import os
import time
import shutil

from app.processed_log import is_already_processed, mark_as_processed
from app.ai_provider import classify, PROVIDERS
from app.kpa_context import build_classification_prompt, get_categories_for_level
from app.ui.context_dialog import ask_context


def process_file(file_path: str, settings, ui) -> None:
    """
    Full pipeline for a single screenshot:
      context prompt → AI classify → copy to KPA folder → write summary → log
    """
    filename = os.path.basename(file_path)
    if not os.path.exists(file_path) or not file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        return

    log_file = settings.get('LOG_FILE')
    if is_already_processed(filename, log_file):
        ui.log(f"⏭  Already processed, skipping: {filename}", "info")
        return

    ui.log(f"🔍 New screenshot detected: {filename}", "info")
    ui.increment_stat("queued")
    time.sleep(1.5)  # let OS release file lock

    # Show context window only if both auto-process AND show-context are on
    auto         = settings.get('AUTO_PROCESS',  'true').lower() == 'true'
    show_context = settings.get('SHOW_CONTEXT',  'true').lower() == 'true'

    if auto and show_context:
        user_context = ask_context(file_path, settings.get('MY_LEVEL'))
        if user_context is None:
            user_context = ""
    else:
        user_context = ""

    try:
        category = _classify_and_file(file_path, filename, user_context, settings, ui)
        mark_as_processed(filename, log_file, category)

        notify_success = settings.get('NOTIFY_ON_SUCCESS', 'false').lower() == 'true'
        if notify_success:
            ui.notify(f"Filed under: {category}", "KPI Assistant")

    except Exception as e:
        err = str(e)
        if "429" in err or "RESOURCE_EXHAUSTED" in err:
            ui.log("❌ Rate limit hit — you've exceeded the free tier quota for this model.", "error")
            ui.log("💡 Try: switch to gemini-2.5-flash-lite in Configuration, or wait 24h, or add billing to your Google account.", "warn")
            ui.notify("Rate limit hit — see log for options", "KPI Assistant")
        elif "404" in err or "NOT_FOUND" in err:
            ui.log(f"❌ Model not found — '{settings.get('AI_MODEL')}' is invalid or unavailable.", "error")
            ui.log("💡 Go to Configuration and select a valid model from the dropdown.", "warn")
            ui.notify("Invalid model — check Configuration", "KPI Assistant")
        elif "401" in err or "API_KEY" in err.upper() or "PERMISSION" in err:
            ui.log("❌ Invalid API key — check your key in Configuration.", "error")
            ui.notify("Invalid API key", "KPI Assistant")
        else:
            ui.log(f"❌ Analysis error: {e}", "error")
            ui.notify(f"Failed to process {filename}", "KPI Assistant")
        ui.increment_stat("errors")


def _classify_and_file(file_path: str, filename: str, user_context: str,
                        settings, ui) -> str:
    provider      = settings.get('AI_PROVIDER', 'Gemini')
    api_key       = settings.get('API_KEY', '') or settings.get('GEMINI_API_KEY', '')
    model         = settings.get('AI_MODEL', 'gemini-2.0-flash')
    level         = settings.get('MY_LEVEL', 'Intermediate')
    custom_prompt = settings.get('CONTEXT_PROMPT', '')

    # Build a rich, level-aware prompt using the full skills matrix
    instructions = build_classification_prompt(level, user_context, custom_prompt)
    valid_cats   = get_categories_for_level(level)

    ui.log(f"🤖 Calling {provider} ({model}) | Level: {level}", "info")

    res = classify(file_path, instructions, provider, api_key, model)

    category_part, summary = (res.split("|") + ["No summary"])[:2]
    category = (category_part.strip()
                .replace("*", "").replace(":", "")
                .replace("/", "").replace("\\", ""))

    # Fuzzy-match against valid categories for this level
    matched = next((c for c in valid_cats
                    if c.lower() in category.lower() or category.lower() in c.lower()),
                   None)
    if matched:
        category = matched

    target   = os.path.join(settings.get('BASE_KPI_FOLDER'), category)
    os.makedirs(target, exist_ok=True)
    new_path = os.path.join(target, filename)
    shutil.copy2(file_path, new_path)

    if category.lower() not in ["junk", "nocontext"]:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(f"{new_path}.txt", "w", encoding="utf-8") as f:
            f.write(
                f"========================================\n"
                f"KPI EVIDENCE SUMMARY\n"
                f"========================================\n"
                f"File      : {filename}\n"
                f"Date      : {timestamp}\n"
                f"Level     : {settings.get('MY_LEVEL', 'Unknown')}\n"
                f"Category  : {category}\n"
                f"AI Model  : {provider} / {model}\n"
                f"----------------------------------------\n"
                f"YOUR CONTEXT\n"
                f"----------------------------------------\n"
                f"{user_context.strip() if user_context.strip() else '(no context provided)'}\n"
                f"----------------------------------------\n"
                f"AI STAR SUMMARY\n"
                f"----------------------------------------\n"
                f"{summary.strip()}\n"
                f"========================================\n"
            )
        ui.log(f"✅ Filed → {category}", "success")
        ui.increment_stat("filed")
    else:
        ui.log(f"⚠️  Low-context item held in: {category}", "warn")

    return category
