# src/routes/optimization.py
from __future__ import annotations

from flask import Blueprint, request, jsonify
import tempfile
import os
import logging

from src.models.item import Item, TruckSpecs, Placement, AlgorithmConfig, calculate_statistics
from src.services.optimizer import LoadingOptimizer
from src.services.fleet_optimizer import FleetOptimizer

# Ces services existent généralement déjà dans votre repo.
# Si vous avez des chemins différents, ajustez les imports.
try:
    from src.services.extractor import ExcelExtractor
except Exception:
    ExcelExtractor = None

try:
    from src.services.visualizer import LoadingVisualizer
except Exception:
    LoadingVisualizer = None


# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

optimization_bp = Blueprint("optimization", __name__, url_prefix="/api/optimization")


@optimization_bp.get("/health")
def health():
    return jsonify({"ok": True, "status": "healthy", "version": "2.0.0"})


@optimization_bp.post("/upload")
def upload():
    if ExcelExtractor is None:
        return jsonify({"error": "ExcelExtractor not available"}), 500

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp_path = tmp.name
        f.save(tmp_path)

    try:
        extractor = ExcelExtractor()
        items, stats = extractor.extract_from_file(tmp_path)
        items = [it.normalized() for it in items]
        stat_obj = calculate_statistics(items)
        return jsonify({
            "success": True,
            "items": [i.to_dict() for i in items],
            "statistics": stat_obj.__dict__
        })
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


@optimization_bp.get("/truck-specs")
def truck_specs():
    """
    Presets cohérents (cm/kg) pour SODATRA (à adapter à votre flotte réelle).
    """
    presets = {
        "van_3t": {"id": "van_3t", "name": "Camionnette 3T", "length": 300, "width": 180, "height": 180, "max_weight": 3000,
                   "base_cost_fcfa": 45000, "cost_per_km_fcfa": 350},
        "truck_19t": {"id": "truck_19t", "name": "Porteur / Plateau 19T (12m)", "length": 1200, "width": 248, "height": 260, "max_weight": 19000,
                      "base_cost_fcfa": 150000, "cost_per_km_fcfa": 650},
        "truck_26t": {"id": "truck_26t", "name": "Semi / Plateau 26T (13.6m)", "length": 1360, "width": 248, "height": 260, "max_weight": 26000,
                      "base_cost_fcfa": 220000, "cost_per_km_fcfa": 800},
        "truck_40t": {"id": "truck_40t", "name": "Semi / Plateau 40T (13.6m)", "length": 1360, "width": 248, "height": 260, "max_weight": 40000,
                      "base_cost_fcfa": 300000, "cost_per_km_fcfa": 950},
        "lowbed_45t": {"id": "lowbed_45t", "name": "Porte-char Lowbed 45T", "length": 1100, "width": 300, "height": 350, "max_weight": 45000,
                       "base_cost_fcfa": 350000, "cost_per_km_fcfa": 1200},
    }
    return jsonify({"success": True, "trucks": list(presets.values())})


@optimization_bp.post("/optimize")
def optimize():
    data = request.get_json(force=True, silent=True) or {}
    items = [Item.from_dict(x) for x in (data.get("items") or [])]
    truck_data = data.get("truck") or {}
    truck = TruckSpecs.from_dict(truck_data)
    config = AlgorithmConfig.from_dict(data)

    optimizer = LoadingOptimizer()
    result = optimizer.optimize(items, truck, config)
    return jsonify({"success": True, "result": result})


@optimization_bp.post("/visualize")
def visualize():
    if LoadingVisualizer is None:
        return jsonify({"error": "LoadVisualizer not available"}), 500

    data = request.get_json(force=True, silent=True) or {}
    truck_data = data.get("truck_specs") or data.get("truck") or {}
    truck = TruckSpecs.from_dict(truck_data)
    placements = [Placement.from_dict(p) for p in (data.get("placements") or [])]

    viz = LoadingVisualizer()
    out = viz.create_visualization(placements, truck)
    return jsonify({"success": True, "visualization": out})


@optimization_bp.post("/suggest-fleet")
def suggest_fleet():
    """
    Endpoint principal:
    - propose des scénarios de flotte
    - si run_3d=true => calcule placements 3D pour chaque camion (ou scénario sélectionné)
    """
    data = request.get_json(force=True, silent=True) or {}

    items = [Item.from_dict(x) for x in (data.get("items") or [])]
    if not items:
        return jsonify({"success": False, "error": "No items provided"}), 400

    # Paramètres
    distance_km = float(data.get("distance_km", 0) or 0)
    run_3d = bool(data.get("run_3d", False))
    config = AlgorithmConfig.from_dict(data)

    # Flotte disponible (peut être fourni par frontend, sinon presets)
    trucks_payload = data.get("available_trucks")
    if trucks_payload:
        available_trucks = [TruckSpecs.from_dict(t) for t in trucks_payload]
    else:
        # fallback: utilise presets de /truck-specs
        presets = [
            TruckSpecs.from_dict({"id": "truck_19t", "name": "Porteur 19T 12m", "length": 1200, "width": 248, "height": 260, "max_weight": 19000, "base_cost_fcfa": 150000, "cost_per_km_fcfa": 650}),
            TruckSpecs.from_dict({"id": "truck_26t", "name": "Semi 26T 13.6m", "length": 1360, "width": 248, "height": 260, "max_weight": 26000, "base_cost_fcfa": 220000, "cost_per_km_fcfa": 800}),
            TruckSpecs.from_dict({"id": "truck_40t", "name": "Semi 40T 13.6m", "length": 1360, "width": 248, "height": 260, "max_weight": 40000, "base_cost_fcfa": 300000, "cost_per_km_fcfa": 950}),
            TruckSpecs.from_dict({"id": "lowbed_45t", "name": "Lowbed 45T", "length": 1100, "width": 300, "height": 350, "max_weight": 45000, "base_cost_fcfa": 350000, "cost_per_km_fcfa": 1200}),
        ]
        available_trucks = presets

    fleet = FleetOptimizer(available_trucks)
    scenarios = fleet.suggest_scenarios(items, distance_km=distance_km)

    # run_3d: calcule placements pour chaque camion de chaque scénario
    if run_3d:
        loader = LoadingOptimizer()
        for sc in scenarios:
            for t in sc.get("trucks", []):
                truck = TruckSpecs.from_dict(t["truck_specs"])
                truck_items = [Item.from_dict(x) for x in (t.get("items") or [])]
                res = loader.optimize(truck_items, truck, config)
                t["loading_result"] = {
                    "items_total": res["items_total"],
                    "items_placed": res["items_placed"],
                    "weight_efficiency": res["weight_efficiency"],
                    "volume_efficiency": res["volume_efficiency"],
                }
                t["placements"] = res["placements"]

    return jsonify({"success": True, "scenarios": scenarios})


@optimization_bp.route('/algorithms', methods=['GET'])
def get_available_algorithms():
    """
    Retourne la liste des algorithmes disponibles
    """
    algorithms = {
        'simple': {
            'name': 'Extreme Points Heuristic',
            'description': 'Algorithme rapide pour placement séquentiel avec points extrêmes',
            'parameters': {},
            'typical_time': '< 1 minute',
            'quality': 'Bonne'
        },
        'genetic': {
            'name': 'Algorithme Génétique',
            'description': 'Optimisation avancée pour solutions optimales',
            'parameters': {
                'population_size': {
                    'type': 'integer',
                    'min': 10,
                    'max': 100,
                    'default': 30,
                    'description': 'Taille de la population'
                },
                'generations': {
                    'type': 'integer',
                    'min': 10,
                    'max': 200,
                    'default': 50,
                    'description': 'Nombre de générations'
                },
                'mutation_rate': {
                    'type': 'float',
                    'min': 0.01,
                    'max': 0.5,
                    'default': 0.1,
                    'description': 'Taux de mutation'
                }
            },
            'typical_time': '2-5 minutes',
            'quality': 'Optimale'
        }
    }
    
    return jsonify({
        'success': True,
        'algorithms': algorithms
    })


# Gestionnaire d'erreurs
@optimization_bp.errorhandler(413)
def file_too_large(e):
    """Gestionnaire pour fichiers trop volumineux"""
    return jsonify({
        'success': False,
        'error': 'Fichier trop volumineux. Taille maximum: 10MB'
    }), 413


@optimization_bp.errorhandler(400)
def bad_request(e):
    """Gestionnaire pour requêtes malformées"""
    return jsonify({
        'success': False,
        'error': 'Requête malformée'
    }), 400


@optimization_bp.errorhandler(500)
def internal_error(e):
    """Gestionnaire pour erreurs internes"""
    logger.error(f"Erreur interne: {str(e)}")
    return jsonify({
        'success': False,
        'error': 'Erreur interne du serveur'
    }), 500
