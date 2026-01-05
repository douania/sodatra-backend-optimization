from sqlalchemy.orm import Session
from src.persistence import repo

def run_workflow(db: Session, case_id):
    """
    Exécute le workflow associé à un dossier.
    V1: exécution séquentielle synchrone avec placeholders.
    """
    full = repo.get_case_full(db, case_id)
    if not full:
        return None

    c, inputs, tasks, outputs, events = full
    c.status = "running"
    db.commit()
    repo.log_event(db, case_id, "run_started", {"workflow_key": c.workflow_key})

    for t in tasks:
        if t["status"] != "queued":
            continue

        step_key = t["step_key"]
        task_id = t["id"]
        repo.set_task_status(db, task_id, "running")

        try:
            if step_key == "RULES_UEMOA":
                # V1: placeholder - sera branché sur les vraies règles UEMOA
                out = {"is_oog": False, "is_exceptional_convoy": False, "notes": []}
                repo.set_task_status(db, task_id, "done", output_json=out)
                repo.add_output(db, case_id, "rules_json", out)

            elif step_key == "FLEET":
                # TODO Patch 1.1: brancher sur suggest-fleet existant
                out = {"note": "FLEET placeholder - sera branché sur suggest-fleet", "scenarios": []}
                repo.set_task_status(db, task_id, "done", output_json=out)
                repo.add_output(db, case_id, "scenarios_json", out)

            elif step_key == "LOAD3D":
                # TODO Patch 1.1: brancher sur optimize + visualize si run_3d
                repo.set_task_status(db, task_id, "skipped", output_json={"note": "LOAD3D skipped (V1)"})

            elif step_key == "PRICE":
                # V1: placeholder - sera branché sur le pricing engine
                out = {"currency": "XOF", "total_xof": 0, "breakdown": {}}
                repo.set_task_status(db, task_id, "done", output_json=out)
                repo.add_output(db, case_id, "quote_json", out)

            elif step_key == "REPORT":
                # V1: génère un rapport JSON basique
                out = {
                    "sections": [
                        {"type": "header", "title": "Rapport de cotation"},
                        {"type": "kpi", "items": [
                            {"label": "Workflow", "value": c.workflow_key},
                            {"label": "Complexité", "value": c.complexity_level},
                        ]},
                        {"type": "missing_fields", "items": c.missing_fields or []},
                    ]
                }
                repo.set_task_status(db, task_id, "done", output_json=out)
                repo.add_output(db, case_id, "report_json", out)

            elif step_key == "TENDER_BUILDER":
                # V1: placeholder pour le builder de tender
                out = {"note": "TENDER builder placeholder", "checklist": [
                    {"item": "Documents techniques", "status": "pending"},
                    {"item": "Références similaires", "status": "pending"},
                    {"item": "Certifications", "status": "pending"},
                ]}
                repo.set_task_status(db, task_id, "done", output_json=out)
                repo.add_output(db, case_id, "tender_json", out)

            else:
                repo.set_task_status(db, task_id, "skipped", output_json={"note": f"unknown step: {step_key}"})

        except Exception as e:
            repo.set_task_status(db, task_id, "failed", error=str(e))
            repo.log_event(db, case_id, "error", {"step": step_key, "error": str(e)})
            c.status = "failed"
            db.commit()
            return c

    c.status = "completed"
    db.commit()
    repo.log_event(db, case_id, "run_completed", {})
    return c
