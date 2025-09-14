from celery_worker import celery
from core.ai_pipeline import process_upload

@celery.task(name="tasks.process_upload_task")
def process_upload_task(upload_id, file_path, user_id, language=None):
    """
    Background Celery task for processing uploads.
    Ensures return is JSON serializable.
    """
    result = process_upload(upload_id, file_path, user_id, language=language)

    # ObjectId ko string banado agar hai
    if isinstance(result, dict):
        if "_id" in result:
            result["_id"] = str(result["_id"])
        if "note_id" in result:
            result["note_id"] = str(result["note_id"])

    return result
