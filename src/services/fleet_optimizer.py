"""
Module d'optimisation de flotte multi-camions
"""

import random
import copy
from typing import List, Dict, Tuple
from src.models.item import Item
from src.services.cost_calculator import CostCalculator

class FleetOptimizer:
    """Optimiseur de flotte pour suggérer la meilleure combinaison de camions"""
    
    # Spécifications des camions disponibles (en cm et kg)
    TRUCK_SPECS = {
        "truck_19t": {
            "name": "Camion 19 tonnes",
            "length": 600,
            "width": 240,
            "height": 240,
            "max_weight": 19000,
            "volume": 34.56  # m³
        },
        "truck_26t": {
            "name": "Camion 26 tonnes",
            "length": 1200,
            "width": 248,
            "height": 270,
            "max_weight": 26000,
            "volume": 80.35  # m³
        },
        "truck_40t": {
            "name": "Camion 40 tonnes (Semi-remorque)",
            "length": 1360,
            "width": 248,
            "height": 270,
            "max_weight": 40000,
            "volume": 91.06  # m³
        },
        "van_3t5": {
            "name": "Camionnette 3.5 tonnes",
            "length": 420,
            "width": 200,
            "height": 200,
            "max_weight": 3500,
            "volume": 16.8  # m³
        }
    }
    
    def __init__(self, items: List[Item], distance_km: float = 100, 
                 available_trucks: List[str] = None, constraints: dict = None):
        """
        Initialise l'optimiseur de flotte
        
        Args:
            items: Liste des articles à transporter
            distance_km: Distance du transport
            available_trucks: Liste des types de camions disponibles
            constraints: Contraintes additionnelles
        """
        self.items = items
        self.distance_km = distance_km
        self.available_trucks = available_trucks or list(self.TRUCK_SPECS.keys())
        self.constraints = constraints or {}
        self.cost_calculator = CostCalculator()
        
        # Analyser les articles
        self.analysis = self._analyze_items()
    
    def _analyze_items(self) -> dict:
        """Analyse les caractéristiques de la packing list"""
        total_volume = 0
        total_weight = 0
        max_length = 0
        max_width = 0
        max_height = 0
        max_single_weight = 0
        
        for item in self.items:
            item_volume = (item.length * item.width * item.height) / 1_000_000  # m³
            total_volume += item_volume * item.quantity
            total_weight += item.weight * item.quantity
            
            max_length = max(max_length, item.length)
            max_width = max(max_width, item.width)
            max_height = max(max_height, item.height)
            max_single_weight = max(max_single_weight, item.weight)
        
        return {
            "total_volume_m3": round(total_volume, 2),
            "total_weight_kg": round(total_weight),
            "item_count": len(self.items),
            "total_pieces": sum(item.quantity for item in self.items),
            "max_dimensions": {
                "length": max_length,
                "width": max_width,
                "height": max_height
            },
            "max_single_weight": max_single_weight,
            "oversized_items": self._count_oversized_items(),
            "heavy_items": self._count_heavy_items()
        }
    
    def _count_oversized_items(self) -> int:
        """Compte les articles surdimensionnés"""
        count = 0
        for item in self.items:
            if (item.length > 1200 or item.width > 240 or item.height > 270):
                count += item.quantity
        return count
    
    def _count_heavy_items(self) -> int:
        """Compte les articles très lourds (> 5 tonnes)"""
        count = 0
        for item in self.items:
            if item.weight > 5000:
                count += item.quantity
        return count
    
    def _filter_compatible_trucks(self) -> List[str]:
        """Filtre les camions compatibles avec les dimensions des articles"""
        compatible = []
        
        max_dims = self.analysis['max_dimensions']
        
        for truck_type in self.available_trucks:
            truck = self.TRUCK_SPECS[truck_type]
            
            # Vérifier si les dimensions max rentrent
            if (max_dims['length'] <= truck['length'] and
                max_dims['width'] <= truck['width'] and
                max_dims['height'] <= truck['height'] and
                self.analysis['max_single_weight'] <= truck['max_weight']):
                compatible.append(truck_type)
        
        return compatible if compatible else self.available_trucks
    
    def suggest_scenarios(self) -> dict:
        """
        Génère plusieurs scénarios d'optimisation
        
        Returns:
            dict avec liste de scénarios et recommandation
        """
        compatible_trucks = self._filter_compatible_trucks()
        
        scenarios = []
        
        # Scénario 1 : Optimisation coût (utilise des camions moyens)
        scenario_cost = self._optimize_for_cost(compatible_trucks)
        if scenario_cost:
            scenarios.append(scenario_cost)
        
        # Scénario 2 : Nombre minimal de camions (utilise les plus gros)
        scenario_min = self._optimize_for_truck_count(compatible_trucks)
        if scenario_min:
            scenarios.append(scenario_min)
        
        # Scénario 3 : Équilibré (compromis)
        scenario_balanced = self._optimize_balanced(compatible_trucks)
        if scenario_balanced:
            scenarios.append(scenario_balanced)
        
        # Calculer les coûts pour chaque scénario
        for scenario in scenarios:
            cost_details = self.cost_calculator.calculate_scenario_cost(
                scenario['trucks'],
                self.distance_km,
                duration_days=scenario.get('estimated_duration_days', 1)
            )
            scenario['cost_details'] = cost_details
            scenario['total_cost'] = cost_details['total_cost']
        
        # Identifier le scénario recommandé
        comparison = self.cost_calculator.compare_scenarios(scenarios)
        recommended_id = comparison.get('recommendation', scenarios[0]['id'] if scenarios else None)
        
        return {
            "success": True,
            "scenarios": scenarios,
            "recommended_scenario": recommended_id,
            "analysis": self.analysis,
            "compatible_trucks": compatible_trucks,
            "comparison": comparison
        }
    
    def _optimize_for_cost(self, compatible_trucks: List[str]) -> dict:
        """Optimise pour minimiser le coût total"""
        # Stratégie : Utiliser des camions de taille moyenne pour équilibrer
        # le nombre de camions et le coût unitaire
        
        # Trier par rapport coût/capacité
        truck_efficiency = []
        for truck_type in compatible_trucks:
            truck = self.TRUCK_SPECS[truck_type]
            cost_info = self.cost_calculator.TRUCK_COSTS[truck_type]
            efficiency = truck['volume'] / (cost_info['fixed'] + cost_info['per_km'] * self.distance_km)
            truck_efficiency.append((truck_type, efficiency, truck['volume'], truck['max_weight']))
        
        # Trier par efficacité décroissante
        truck_efficiency.sort(key=lambda x: x[1], reverse=True)
        
        # Allouer les articles aux camions
        trucks_needed = self._allocate_items_to_trucks(truck_efficiency)
        
        if not trucks_needed:
            return None
        
        total_trucks = sum(t['quantity'] for t in trucks_needed)
        avg_fill = sum(t['fill_rate'] for t in trucks_needed) / len(trucks_needed) if trucks_needed else 0
        
        return {
            "id": "scenario_cost_optimal",
            "name": "Coût Optimal",
            "description": "Minimise le coût total du transport en optimisant le rapport coût/capacité",
            "trucks": trucks_needed,
            "total_trucks": total_trucks,
            "average_fill_rate": round(avg_fill, 2),
            "estimated_duration_days": self._estimate_duration(total_trucks),
            "legal_compliance": True,
            "warnings": []
        }
    
    def _optimize_for_truck_count(self, compatible_trucks: List[str]) -> dict:
        """Optimise pour minimiser le nombre de camions"""
        # Stratégie : Utiliser les plus gros camions disponibles
        
        # Trier par capacité décroissante
        sorted_trucks = sorted(
            compatible_trucks,
            key=lambda t: self.TRUCK_SPECS[t]['volume'],
            reverse=True
        )
        
        # Utiliser principalement les plus gros
        truck_priority = [(t, 0, self.TRUCK_SPECS[t]['volume'], self.TRUCK_SPECS[t]['max_weight']) 
                         for t in sorted_trucks]
        
        trucks_needed = self._allocate_items_to_trucks(truck_priority)
        
        if not trucks_needed:
            return None
        
        total_trucks = sum(t['quantity'] for t in trucks_needed)
        avg_fill = sum(t['fill_rate'] for t in trucks_needed) / len(trucks_needed) if trucks_needed else 0
        
        warnings = []
        if avg_fill > 0.95:
            warnings.append("Taux de remplissage très élevé - marge de sécurité réduite")
        
        return {
            "id": "scenario_min_trucks",
            "name": "Nombre Minimal de Camions",
            "description": "Utilise le moins de camions possible en maximisant le remplissage",
            "trucks": trucks_needed,
            "total_trucks": total_trucks,
            "average_fill_rate": round(avg_fill, 2),
            "estimated_duration_days": self._estimate_duration(total_trucks),
            "legal_compliance": True,
            "warnings": warnings
        }
    
    def _optimize_balanced(self, compatible_trucks: List[str]) -> dict:
        """Compromis entre coût et nombre de camions"""
        # Stratégie : Mix de camions moyens et gros
        
        # Utiliser une combinaison équilibrée
        truck_mix = []
        for truck_type in compatible_trucks:
            truck = self.TRUCK_SPECS[truck_type]
            # Score équilibré : volume * 0.6 + (1/coût) * 0.4
            cost_info = self.cost_calculator.TRUCK_COSTS[truck_type]
            cost_score = 1 / (cost_info['fixed'] + cost_info['per_km'] * self.distance_km)
            score = truck['volume'] * 0.6 + cost_score * 1000000 * 0.4
            truck_mix.append((truck_type, score, truck['volume'], truck['max_weight']))
        
        truck_mix.sort(key=lambda x: x[1], reverse=True)
        
        trucks_needed = self._allocate_items_to_trucks(truck_mix)
        
        if not trucks_needed:
            return None
        
        total_trucks = sum(t['quantity'] for t in trucks_needed)
        avg_fill = sum(t['fill_rate'] for t in trucks_needed) / len(trucks_needed) if trucks_needed else 0
        
        return {
            "id": "scenario_balanced",
            "name": "Équilibré",
            "description": "Compromis optimal entre coût, nombre de camions et sécurité",
            "trucks": trucks_needed,
            "total_trucks": total_trucks,
            "average_fill_rate": round(avg_fill, 2),
            "estimated_duration_days": self._estimate_duration(total_trucks),
            "legal_compliance": True,
            "warnings": []
        }
    
    def _allocate_items_to_trucks(self, truck_priority: List[Tuple]) -> List[dict]:
        """
        Alloue les articles aux camions selon une priorité donnée
        
        Args:
            truck_priority: Liste de (truck_type, score, volume, max_weight)
        
        Returns:
            Liste de camions nécessaires avec leurs caractéristiques
        """
        remaining_volume = self.analysis['total_volume_m3']
        remaining_weight = self.analysis['total_weight_kg']
        
        trucks_needed = {}
        
        # Allouer itérativement
        while remaining_volume > 0.01 or remaining_weight > 0:
            # Choisir le meilleur camion disponible
            best_truck = None
            for truck_type, _, volume, max_weight in truck_priority:
                if volume > 0 and max_weight > 0:
                    best_truck = truck_type
                    break
            
            if not best_truck:
                break
            
            truck_spec = self.TRUCK_SPECS[best_truck]
            
            # Calculer combien ce camion peut prendre
            volume_taken = min(remaining_volume, truck_spec['volume'])
            weight_taken = min(remaining_weight, truck_spec['max_weight'])
            
            # Ajouter ce camion
            if best_truck not in trucks_needed:
                trucks_needed[best_truck] = {
                    "type": best_truck,
                    "name": truck_spec['name'],
                    "quantity": 0,
                    "volume_used": 0,
                    "weight_used": 0,
                    "volume_capacity": truck_spec['volume'],
                    "weight_capacity": truck_spec['max_weight']
                }
            
            trucks_needed[best_truck]['quantity'] += 1
            trucks_needed[best_truck]['volume_used'] += volume_taken
            trucks_needed[best_truck]['weight_used'] += weight_taken
            
            remaining_volume -= volume_taken
            remaining_weight -= weight_taken
            
            # Sécurité : éviter boucle infinie
            if trucks_needed[best_truck]['quantity'] > 100:
                break
        
        # Calculer les taux de remplissage
        result = []
        for truck_data in trucks_needed.values():
            volume_fill = truck_data['volume_used'] / (truck_data['volume_capacity'] * truck_data['quantity'])
            weight_fill = truck_data['weight_used'] / (truck_data['weight_capacity'] * truck_data['quantity'])
            
            truck_data['fill_rate'] = min(volume_fill, weight_fill)
            truck_data['volume_fill_rate'] = volume_fill
            truck_data['weight_fill_rate'] = weight_fill
            
            result.append(truck_data)
        
        return result
    
    def _estimate_duration(self, truck_count: int) -> float:
        """Estime la durée du transport en jours"""
        # Formule simple : 1 jour de base + 0.5 jour par camion additionnel
        base_days = 1
        additional_days = (truck_count - 1) * 0.5
        return round(base_days + additional_days, 1)
