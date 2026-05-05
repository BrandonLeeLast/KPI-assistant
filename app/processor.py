import os
import time
import shutil

from app.processed_log import is_already_processed, mark_as_processed
from app.ai_provider import classify, PROVIDERS
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
        ui.log(f"❌ Analysis error: {e}", "error")
        ui.increment_stat("errors")
        ui.notify(f"Failed to process {filename}", "KPI Assistant")


def _classify_and_file(file_path: str, filename: str, user_context: str,
                        settings, ui) -> str:
    provider  = settings.get('AI_PROVIDER', 'Gemini')
    api_key   = settings.get('API_KEY', '') or settings.get('GEMINI_API_KEY', '')
    model     = settings.get('AI_MODEL', 'gemini-2.0-flash')
    level     = settings.get('MY_LEVEL', 'Intermediate')
    kpa_cats  = settings.get('KPA_CATEGORIES',
                             'Technical Mastery,Engineering Operations,Consultant Mindset,'
                             'Communication & Collaboration,Leadership')
    custom_prompt = settings.get('CONTEXT_PROMPT', '')

    instructions = (
        f"You are a Performance Auditor for an '{level}' developer. "
        "Task: Use the STAR Method (Situation, Task, Action, Result). "
        f"User Context: '{user_context}'. "
        f"{custom_prompt} "
        f"Pick ONE KPA from: {kpa_cats}. "
        "Format: CATEGORY | STAR SUMMARY."
    )

    ui.log(f"🤖 Calling {provider} ({model}) for classification…", "info")

    res = classify(file_path, instructions, provider, api_key, model)

    category_part, summary = (res.split("|") + ["No summary"])[:2]
    category = (category_part.strip()
                .replace("*", "").replace(":", "")
                .replace("/", "").replace("\\", ""))

    target   = os.path.join(settings.get('BASE_KPI_FOLDER'), category)
    os.makedirs(target, exist_ok=True)
    new_path = os.path.join(target, filename)
    shutil.copy2(file_path, new_path)

    if category.lower() not in ["junk", "nocontext"]:
        with open(f"{new_path}.txt", "w", encoding="utf-8") as f:
            f.write(f"USER CONTEXT: {user_context}\nAI SUMMARY ({provider}): {summary.strip()}")
        ui.log(f"✅ Filed → {category}", "success")
        ui.increment_stat("filed")
    else:
        ui.log(f"⚠️  Low-context item held in: {category}", "warn")

    return category
