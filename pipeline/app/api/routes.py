from fastapi import APIRouter
#from app.workers.tasks import extract_task, classify_task

router = APIRouter()

@router.post("/extract")
def extract(file_path: str):
    task = extract_task.delay(file_path)
    return {"task_id": task.id}

@router.post("/classify")
def classify(dataset_id: str):
    task = classify_task.delay(dataset_id)
    return {"task_id": task.id}