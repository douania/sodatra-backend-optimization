"""
Routes API pour l'optimisation de chargement
"""
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import tempfile
import logging
from typing import Dict, Any

from src.models.item import Item, TruckSpecs, AlgorithmConfig, calculate_statistics
from src.services.extractor import ExcelExtractor
from src.services.optimizer import LoadingOptimizer
from src.services.visualizer import LoadingVisualizer

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Création du blueprint
optimization_bp = Blueprint('optimization', __name__)

# Configuration des fichiers autorisés
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename: str) -> bool:
    """Vérifie si le fichier est autorisé"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@optimization_bp.route('/upload', methods=['POST'])
def upload_packing_list():
    """
    Upload et analyse d'une packing list Excel
    
    Returns:
        JSON avec les articles extraits et les statistiques
    """
    try:
        # Vérification de la présence du fichier
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Aucun fichier fourni'
            }), 400
        
        file = request.files['file']
        
        # Vérification du nom de fichier
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Aucun fichier sélectionné'
            }), 400
        
        # Vérification de l'extension
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Format de fichier non supporté. Utilisez .xlsx ou .xls'
            }), 400
        
        # Sauvegarde temporaire du fichier
        filename = secure_filename(file.filename)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Extraction des données
            extractor = ExcelExtractor()
            items, statistics = extractor.extract_from_file(temp_path)
            
            # Conversion en dictionnaires pour JSON
            items_data = [item.to_dict() for item in items]
            statistics_data = statistics.to_dict()
            
            logger.info(f"Extraction réussie: {len(items)} articles")
            
            return jsonify({
                'success': True,
                'items': items_data,
                'statistics': statistics_data,
                'extraction_report': extractor.get_extraction_report()
            })
            
        finally:
            # Nettoyage du fichier temporaire
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    except Exception as e:
        logger.error(f"Erreur lors de l'upload: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erreur lors du traitement du fichier: {str(e)}'
        }), 500

@optimization_bp.route('/optimize', methods=['POST'])
def optimize_loading():
    """
    Lance l'optimisation du chargement
    
    Expected JSON:
    {
        "items": [...],
        "truck": {...},
        "algorithm": "simple|genetic",
        "population_size": 30,
        "generations": 50,
        "mutation_rate": 0.1
    }
    
    Returns:
        JSON avec le résultat de l'optimisation
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Données JSON manquantes'
            }), 400
        
        # Validation des données requises
        required_fields = ['items', 'truck']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Champ requis manquant: {field}'
                }), 400
        
        # Reconstruction des objets
        items = [Item.from_dict(item_data) for item_data in data['items']]
        truck_specs = TruckSpecs(**data['truck'])
        
        # Configuration de l'algorithme
        algorithm_config = AlgorithmConfig(
            algorithm=data.get('algorithm', 'genetic'),
            population_size=data.get('population_size', 30),
            generations=data.get('generations', 50),
            mutation_rate=data.get('mutation_rate', 0.1),
            crossover_rate=data.get('crossover_rate', 0.8),
            elitism_rate=data.get('elitism_rate', 0.1),
            timeout_seconds=data.get('timeout_seconds', 300)
        )
        
        # Validation des paramètres
        if algorithm_config.population_size < 10 or algorithm_config.population_size > 100:
            return jsonify({
                'success': False,
                'error': 'Taille de population doit être entre 10 et 100'
            }), 400
        
        if algorithm_config.generations < 10 or algorithm_config.generations > 200:
            return jsonify({
                'success': False,
                'error': 'Nombre de générations doit être entre 10 et 200'
            }), 400
        
        # Lancement de l'optimisation
        optimizer = LoadingOptimizer()
        result = optimizer.optimize(items, truck_specs, algorithm_config)
        
        logger.info(f"Optimisation terminée: {result.items_placed}/{result.items_total} articles placés")
        
        return jsonify({
            'success': result.success,
            'results': {
                'items_placed': result.items_placed,
                'items_total': result.items_total,
                'weight_efficiency': result.weight_efficiency,
                'volume_efficiency': result.volume_efficiency,
                'fitness': result.fitness,
                'computation_time': result.computation_time,
                'algorithm_used': result.algorithm_used
            },
            'placements': [p.to_dict() for p in result.placements],
            'truck_specs': result.truck_specs.to_dict() if result.truck_specs else None,
            'error': result.error_message
        })
    
    except Exception as e:
        logger.error(f"Erreur lors de l'optimisation: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erreur lors de l\'optimisation: {str(e)}'
        }), 500

@optimization_bp.route('/visualize', methods=['POST'])
def generate_visualization():
    """
    Génère une visualisation 3D du plan de chargement
    
    Expected JSON:
    {
        "placements": [...],
        "truck_specs": {...},
        "view_type": "3d|2d|sequence"
    }
    
    Returns:
        JSON avec l'image encodée en base64
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Données JSON manquantes'
            }), 400
        
        # Validation des données
        if 'placements' not in data or 'truck_specs' not in data:
            return jsonify({
                'success': False,
                'error': 'Placements et spécifications camion requis'
            }), 400
        
        # Reconstruction des objets
        placements = []
        for p_data in data['placements']:
            placement = Placement(**p_data)
            placements.append(placement)
        
        truck_specs = TruckSpecs(**data['truck_specs'])
        view_type = data.get('view_type', '3d')
        
        # Génération de la visualisation
        visualizer = LoadingVisualizer()
        
        if view_type == '3d':
            image = visualizer.generate_3d_visualization(placements, truck_specs)
            return jsonify({
                'success': True,
                'image': image
            })
        
        elif view_type == '2d':
            views = visualizer.generate_2d_views(placements, truck_specs)
            return jsonify({
                'success': True,
                'views': views
            })
        
        elif view_type == 'sequence':
            sequence = visualizer.generate_loading_sequence(placements, truck_specs)
            return jsonify({
                'success': True,
                'sequence': sequence
            })
        
        else:
            return jsonify({
                'success': False,
                'error': f'Type de vue non supporté: {view_type}'
            }), 400
    
    except Exception as e:
        logger.error(f"Erreur lors de la visualisation: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erreur lors de la génération de visualisation: {str(e)}'
        }), 500

@optimization_bp.route('/truck-specs', methods=['GET'])
def get_default_truck_specs():
    """
    Retourne les spécifications de camion par défaut
    
    Returns:
        JSON avec les spécifications par défaut
    """
    try:
        # Spécifications par défaut pour un camion 26T
        default_specs = TruckSpecs(
            length=1360,  # 13.6m
            width=248,    # 2.48m
            height=270,   # 2.7m
            max_weight=26000  # 26T
        )
        
        # Autres configurations prédéfinies
        presets = {
            'truck_19t': TruckSpecs(length=1200, width=248, height=270, max_weight=19000),
            'truck_26t': default_specs,
            'truck_40t': TruckSpecs(length=1360, width=248, height=270, max_weight=40000),
            'van_3t5': TruckSpecs(length=600, width=200, height=200, max_weight=3500)
        }
        
        return jsonify({
            'success': True,
            'default': default_specs.to_dict(),
            'presets': {name: spec.to_dict() for name, spec in presets.items()}
        })
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des spécifications: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@optimization_bp.route('/algorithms', methods=['GET'])
def get_available_algorithms():
    """
    Retourne la liste des algorithmes disponibles
    
    Returns:
        JSON avec les algorithmes et leurs paramètres
    """
    try:
        algorithms = {
            'simple': {
                'name': 'First Fit Decreasing',
                'description': 'Algorithme rapide pour placement séquentiel',
                'parameters': {},
                'typical_time': '< 1 minute',
                'quality': 'Basique'
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
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des algorithmes: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@optimization_bp.route('/health', methods=['GET'])
def health_check():
    """
    Vérification de l'état du service
    
    Returns:
        JSON avec l'état du service
    """
    try:
        return jsonify({
            'success': True,
            'status': 'healthy',
            'version': '1.0.0',
            'services': {
                'extractor': 'operational',
                'optimizer': 'operational',
                'visualizer': 'operational'
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# Gestionnaire d'erreurs
@optimization_bp.errorhandler(413)
def file_too_large(e):
    """Gestionnaire pour fichiers trop volumineux"""
    return jsonify({
        'success': False,
        'error': f'Fichier trop volumineux. Taille maximum: {MAX_FILE_SIZE // (1024*1024)}MB'
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



@optimization_bp.route('/suggest-fleet', methods=['POST'])
def suggest_fleet():
    """
    Suggère la meilleure combinaison de camions pour une packing list
    
    Request JSON:
        {
            "items": [...],
            "distance_km": 450,
            "available_trucks": ["truck_19t", "truck_26t", "truck_40t"],
            "constraints": {...}
        }
    
    Returns:
        JSON avec plusieurs scénarios d'optimisation et recommandation
    """
    try:
        from src.services.fleet_optimizer import FleetOptimizer
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Aucune donnée fournie'
            }), 400
        
        # Extraction des paramètres
        items_data = data.get('items', [])
        distance_km = data.get('distance_km', 100)
        available_trucks = data.get('available_trucks')
        constraints = data.get('constraints', {})
        
        if not items_data:
            return jsonify({
                'success': False,
                'error': 'Liste d\'articles vide'
            }), 400
        
        # Convertir les données en objets Item
        items = []
        for item_data in items_data:
            try:
                item = Item(
                    name=item_data.get('name', 'Article'),
                    length=float(item_data.get('length', 0)),
                    width=float(item_data.get('width', 0)),
                    height=float(item_data.get('height', 0)),
                    weight=float(item_data.get('weight', 0)),
                    quantity=int(item_data.get('quantity', 1))
                )
                items.append(item)
            except (ValueError, TypeError) as e:
                logger.warning(f"Article invalide ignoré: {e}")
                continue
        
        if not items:
            return jsonify({
                'success': False,
                'error': 'Aucun article valide trouvé'
            }), 400
        
        # Créer l'optimiseur de flotte
        optimizer = FleetOptimizer(
            items=items,
            distance_km=distance_km,
            available_trucks=available_trucks,
            constraints=constraints
        )
        
        # Générer les scénarios
        result = optimizer.suggest_scenarios()
        
        logger.info(f"Scénarios générés avec succès: {len(result.get('scenarios', []))} scénarios")
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Erreur lors de la suggestion de flotte: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erreur lors de la suggestion de flotte: {str(e)}'
        }), 500
