import os
import time
import shutil
import PIL.Image
from google import genai

from app.processed_log import is_already_processed, mark_as_processed
from app.ui.context_dialog import ask_context


def process_file(file_path: str, settings, ui) -> None:
    """
    Full pipeline for a single screenshot:
      prompt → Gemini classify → copy to KPA folder → write .txt summary → log processed
    `ui` must expose .log(text, level) and .increment_stat(key).
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
    time.sleep(1.5)  # let the OS release the file lock before we open it

    user_context = ask_context(file_path, settings.get('MY_LEVEL'))
    if user_context is None:
        user_context = ""

    try:
        category = _classify_and_file(file_path, filename, user_context, settings, ui)
        mark_as_processed(filename, log_file, category)
    except Exception as e:
        ui.log(f"❌ Analysis error: {e}", "error")
        ui.increment_stat("errors")


def _classify_and_file(file_path: str, filename: str, user_context: str, settings, ui) -> str:
    """Calls Gemini, files the image, writes the .txt summary. Returns the category string."""
    instructions = (
        f"You are a Performance Auditor for an '{settings.get('MY_LEVEL')}' developer. "
        "Task: Use the STAR Method (Situation, Task, Action, Result). "
        f"User Context: '{user_context}'. "
        "Analyze the image and pick ONE KPA: Technical Mastery, Engineering Operations, "
        "Consultant Mindset, Communication & Collaboration, or Leadership. "
        "Format: CATEGORY | STAR SUMMARY."
    )

    ui.log("🤖 Calling Gemini Flash for classification…", "info")
    client = genai.Client(api_key=settings.get('GEMINI_API_KEY'))

    # Open, copy into memory, close — file handle is released before the API call
    with PIL.Image.open(file_path) as raw:
        img = raw.copy()

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[instructions, img],
    )
    res = response.text

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
            f.write(f"USER CONTEXT: {user_context}\nGEMINI SUMMARY: {summary.strip()}")
        ui.log(f"✅ Filed → {category}", "success")
        ui.increment_stat("filed")
    else:
        ui.log(f"⚠️  Low-context item held in: {category}", "warn")

    return category
