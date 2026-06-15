from celery import Celery
from app.services.ingestion import extract_text
#from app.services.classification import classify_requirement
from app.services.llm import analisar_requisito

celery = Celery(
    "tasks",
    broker="redis://localhost:6379/0"
)

@celery.task
def extract_task(file_path):
    text = extract_text(file_path)
    return {"text": text}

@celery.task
def classify_task(dataset):

    results = []

    for req in dataset:
        results.append(classify_requirement(req))

    return results