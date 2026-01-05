import re
from src.router.canonical import empty_normalized_request

def parse_text_to_request(text: str):
    """
    V1: extraction heuristique minimale.
    Retourne: (normalized_request, missing_fields, assumptions, confidence)
    """
    req = empty_normalized_request()
    missing = []
    assumptions = []
    confidence = 0.55

    t = (text or "").strip()

    # Détection tender/RFP
    if re.search(r"\b(tender|rfp|appel d['']offre|minusca)\b", t, re.IGNORECASE):
        req["intent"] = "tender"
        confidence += 0.15

    # Détection project cargo
    if re.search(r"\b(project cargo|heavy lift|oog|hors gabarit|convoi exceptionnel)\b", t, re.IGNORECASE):
        req["intent"] = "project_cargo"
        confidence += 0.10

    # Extraction basique des villes (heuristique simple)
    cities_pattern = r"\b(Dakar|Bamako|Abidjan|Douala|Bangui|Conakry|Ouagadougou|Niamey|Lomé|Cotonou|Accra|Lagos)\b"
    cities_found = re.findall(cities_pattern, t, re.IGNORECASE)
    if cities_found:
        unique_cities = list(dict.fromkeys([c.title() for c in cities_found]))
        if len(unique_cities) >= 1:
            req["route"]["origins"] = [{"name": unique_cities[0], "type": "city"}]
        if len(unique_cities) >= 2:
            req["route"]["destinations"] = [{"name": unique_cities[1], "type": "city"}]
        confidence += 0.10

    # Détection poids lourds
    weight_match = re.search(r"(\d+)\s*(kg|t|tonnes?)", t, re.IGNORECASE)
    if weight_match:
        weight = int(weight_match.group(1))
        unit = weight_match.group(2).lower()
        if unit in ["t", "tonne", "tonnes"]:
            weight *= 1000
        if weight > 10000:  # > 10 tonnes
            assumptions.append(f"Colis lourd détecté: {weight}kg")
            confidence += 0.05

    # Champs manquants minimaux
    if not req["route"]["origins"]:
        missing.append({"field": "route.origins", "question": "Quelle est l'origine (ville/site/port) ?", "priority": "high"})
    if not req["route"]["destinations"]:
        missing.append({"field": "route.destinations", "question": "Quelle est la destination (ville/site/port) ?", "priority": "high"})

    return req, missing, assumptions, min(confidence, 0.95)

def complexity_and_workflow(req: dict):
    """
    Calcule le score de complexité et retourne le workflow approprié.
    """
    score = 0

    intent = req.get("intent", "quote")
    if intent == "tender":
        score += 6
    elif intent == "project_cargo":
        score += 4

    items = (req.get("cargo") or {}).get("items") or []
    if len(items) > 10:
        score += 2
    if len(items) > 50:
        score += 2

    origins = (req.get("route") or {}).get("origins") or []
    destinations = (req.get("route") or {}).get("destinations") or []
    legs = (req.get("route") or {}).get("legs") or []

    if len(origins) > 1:
        score += 2
    if len(destinations) > 1:
        score += 2
    if len(legs) > 1:
        score += 3

    # Vérifier les contraintes
    constraints = req.get("constraints") or {}
    if constraints.get("exceptional_convoy") == "yes":
        score += 3

    # Mapping vers workflows
    if score >= 6:
        return 4, "WF_TENDER"
    if score >= 4:
        return 3, "WF_PROJECT_CARGO"
    if score >= 2:
        return 2, "WF_STANDARD_QUOTE"
    return 1, "WF_SIMPLE_QUOTE"
