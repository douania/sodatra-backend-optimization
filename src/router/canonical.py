def empty_normalized_request():
    return {
        "intent": "quote",
        "modes": [],
        "parties": {"shipper": {}, "consignee": {}},
        "route": {"origins": [], "hubs": [], "destinations": [], "legs": []},
        "cargo": {"items": [], "units_summary": {}, "dangerous_goods": {"is_dg": False, "un": None, "class": None}},
        "constraints": {"exceptional_convoy": "unknown"},
        "commercial": {"currency": "XOF", "incoterm": None, "insurance": False},
    }
