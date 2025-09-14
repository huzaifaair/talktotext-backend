from celery_worker import celery
from core.ai_pipeline import process_upload

@celery.task(name="tasks.process_upload_task")
def process_upload_task(upload_id, file_path, user_id, language=None):
    """
    Background Celery task for processing uploads.
    """
    return process_upload(upload_id, file_path, user_id, language=language)
