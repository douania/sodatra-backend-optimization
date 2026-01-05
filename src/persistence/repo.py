import uuid
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.persistence.models import CaseFile, CaseInput, CaseEvent, CaseTask, CaseOutput

def log_event(db: Session, case_id: uuid.UUID, event_type: str, payload: dict | None = None):
    db.add(CaseEvent(case_id=case_id, event_type=event_type, payload=payload))
    db.commit()

def create_case(db: Session, client_name=None, client_email=None, customer_ref=None) -> CaseFile:
    c = CaseFile(client_name=client_name, client_email=client_email, customer_ref=customer_ref)
    db.add(c)
    db.commit()
    db.refresh(c)
    log_event(db, c.id, "intake_received", {"client_name": client_name, "client_email": client_email})
    return c

def add_input_text(db: Session, case_id: uuid.UUID, text_value: str):
    inp = CaseInput(case_id=case_id, source_type="email_text", raw_text=text_value)
    db.add(inp)
    db.commit()
    db.refresh(inp)
    log_event(db, case_id, "input_added", {"type": "email_text"})
    return inp

def update_case_classification(db: Session, case_id: uuid.UUID, normalized_request: dict, missing_fields: list,
                               workflow_key: str, complexity_level: int, assumptions: list, confidence: float | None):
    c = db.get(CaseFile, case_id)
    if not c:
        return None
    c.normalized_request = normalized_request
    c.missing_fields = missing_fields
    c.workflow_key = workflow_key
    c.complexity_level = complexity_level
    c.assumptions = assumptions
    c.confidence = confidence
    c.status = "needs_info" if missing_fields else "ready"
    c.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(c)
    log_event(db, case_id, "classified", {"workflow_key": workflow_key, "complexity_level": complexity_level, "missing": missing_fields})
    return c

def create_tasks_for_workflow(db: Session, case_id: uuid.UUID, workflow_key: str):
    wf = {
        "WF_SIMPLE_QUOTE": ["PRICE", "REPORT"],
        "WF_STANDARD_QUOTE": ["FLEET", "PRICE", "REPORT"],
        "WF_PROJECT_CARGO": ["RULES_UEMOA", "FLEET", "LOAD3D", "PRICE", "REPORT"],
        "WF_TENDER": ["RULES_UEMOA", "FLEET", "LOAD3D", "PRICE", "REPORT", "TENDER_BUILDER"],
    }
    steps = wf.get(workflow_key, ["PRICE", "REPORT"])
    for s in steps:
        db.add(CaseTask(case_id=case_id, step_key=s, status="queued"))
    db.commit()
    log_event(db, case_id, "workflow_selected", {"workflow_key": workflow_key, "steps": steps})

def set_task_status(db: Session, task_id: uuid.UUID, status: str, output_json=None, error=None):
    t = db.get(CaseTask, task_id)
    if not t:
        return None
    t.status = status
    t.output_json = output_json
    t.error = error
    t.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(t)
    return t

def add_output(db: Session, case_id: uuid.UUID, output_type: str, content_json: dict, file_uri: str | None = None):
    out = CaseOutput(case_id=case_id, output_type=output_type, content_json=content_json, file_uri=file_uri)
    db.add(out)
    db.commit()
    db.refresh(out)
    log_event(db, case_id, "output_created", {"output_type": output_type})
    return out

def get_case_full(db: Session, case_id: uuid.UUID):
    c = db.get(CaseFile, case_id)
    if not c:
        return None
    inputs = db.execute(text("select * from case_inputs where case_id=:id order by created_at desc"), {"id": str(case_id)}).mappings().all()
    tasks = db.execute(text("select * from case_tasks where case_id=:id order by created_at asc"), {"id": str(case_id)}).mappings().all()
    outputs = db.execute(text("select * from case_outputs where case_id=:id order by created_at desc"), {"id": str(case_id)}).mappings().all()
    events = db.execute(text("select * from case_events where case_id=:id order by created_at desc limit 200"), {"id": str(case_id)}).mappings().all()
    return c, inputs, tasks, outputs, events
