import uuid
from flask import Blueprint, request, jsonify
from src.db import get_session, is_db_available
from src.persistence import repo
from src.router.classifier import parse_text_to_request, complexity_and_workflow
from src.workflows.engine import run_workflow

casefiles_bp = Blueprint("casefiles", __name__)

@casefiles_bp.post("/intake")
def intake():
    """
    Crée un nouveau dossier (case) à partir d'une demande.
    Analyse le texte, classifie la complexité et sélectionne le workflow.
    """
    if not is_db_available():
        return jsonify({"success": False, "error": "Database not configured"}), 503

    payload = request.get_json(force=True, silent=True) or {}
    source = payload.get("source") or {}
    text_value = (source.get("text") or "").strip()

    db = get_session()
    try:
        c = repo.create_case(
            db,
            client_name=payload.get("client_name"),
            client_email=payload.get("client_email"),
            customer_ref=payload.get("customer_ref"),
        )

        if text_value:
            repo.add_input_text(db, c.id, text_value)

        normalized, missing, assumptions, confidence = parse_text_to_request(text_value)
        level, wf = complexity_and_workflow(normalized)

        c2 = repo.update_case_classification(db, c.id, normalized, missing, wf, level, assumptions, confidence)
        repo.create_tasks_for_workflow(db, c.id, wf)

        return jsonify({
            "success": True,
            "case_id": str(c.id),
            "status": c2.status,
            "workflow_key": c2.workflow_key,
            "complexity_level": c2.complexity_level,
            "confidence": float(confidence),
            "missing_fields": c2.missing_fields or [],
            "assumptions": c2.assumptions or [],
            "normalized_request": c2.normalized_request or {},
        })
    finally:
        db.close()

@casefiles_bp.post("/<case_id>/run")
def run(case_id: str):
    """
    Exécute le workflow associé à un dossier.
    """
    if not is_db_available():
        return jsonify({"success": False, "error": "Database not configured"}), 503

    db = get_session()
    try:
        cid = uuid.UUID(case_id)
        c = run_workflow(db, cid)
        if not c:
            return jsonify({"success": False, "error": "not_found"}), 404
        return jsonify({"success": True, "status": c.status})
    except ValueError:
        return jsonify({"success": False, "error": "invalid_case_id"}), 400
    finally:
        db.close()

@casefiles_bp.get("/<case_id>")
def get_case(case_id: str):
    """
    Récupère les détails complets d'un dossier.
    """
    if not is_db_available():
        return jsonify({"success": False, "error": "Database not configured"}), 503

    db = get_session()
    try:
        cid = uuid.UUID(case_id)
        full = repo.get_case_full(db, cid)
        if not full:
            return jsonify({"success": False, "error": "not_found"}), 404

        c, inputs, tasks, outputs, events = full
        return jsonify({
            "success": True,
            "case": {
                "id": str(c.id),
                "status": c.status,
                "workflow_key": c.workflow_key,
                "complexity_level": c.complexity_level,
                "confidence": float(c.confidence) if c.confidence is not None else None,
                "missing_fields": c.missing_fields,
                "assumptions": c.assumptions,
                "normalized_request": c.normalized_request,
                "client_name": c.client_name,
                "client_email": c.client_email,
                "customer_ref": c.customer_ref,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            },
            "inputs": [dict(x) for x in inputs],
            "tasks": [dict(x) for x in tasks],
            "outputs": [dict(x) for x in outputs],
            "events": [dict(x) for x in events],
        })
    except ValueError:
        return jsonify({"success": False, "error": "invalid_case_id"}), 400
    finally:
        db.close()

@casefiles_bp.get("/")
def list_cases():
    """
    Liste tous les dossiers (pagination basique).
    """
    if not is_db_available():
        return jsonify({"success": False, "error": "Database not configured"}), 503

    from sqlalchemy import text
    db = get_session()
    try:
        limit = min(int(request.args.get("limit", 50)), 100)
        offset = int(request.args.get("offset", 0))
        
        result = db.execute(
            text("SELECT id, status, workflow_key, complexity_level, client_name, created_at FROM case_files ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
            {"limit": limit, "offset": offset}
        ).mappings().all()
        
        return jsonify({
            "success": True,
            "cases": [dict(x) for x in result],
            "limit": limit,
            "offset": offset,
        })
    finally:
        db.close()
