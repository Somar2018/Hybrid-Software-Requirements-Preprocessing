from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from app.workers.tasks import validar_requisitos
from celery.result import AsyncResult

app = FastAPI()

# ---- INPUT MODEL ----
class RequisitosInput(BaseModel):
    requisitos: List[str]


# ---- ENVIAR TASK ----
@app.post("/validar")
def validar(data: RequisitosInput):
    task = validar_requisitos.delay(data.requisitos)
    return {"task_id": task.id}


# ---- VER STATUS ----
@app.get("/status/{task_id}")
def status(task_id: str):
    result = AsyncResult(task_id)
    return {
        "status": result.status,
        "resultado": result.result if result.ready() else None
    }
