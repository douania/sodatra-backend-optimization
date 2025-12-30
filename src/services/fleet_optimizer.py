"""
Module d'optimisation de flotte multi-camions
"""

import random
import copy
import math
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
            # Volume en m3 (dimensions en cm)
            item_volume = (item.length * item.width * item.height) / 1_000_000
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
        count = 0
        for item in self.items:
            if (item.length > 1200 or item.width > 240 or item.height > 270):
                count += item.quantity
        return count
    
    def _count_heavy_items(self) -> int:
        count = 0
        for item in self.items:
            if item.weight > 5000:
                count += item.quantity
        return count
    
    def _filter_compatible_trucks(self) -> List[str]:
        compatible = []
        max_dims = self.analysis['max_dimensions']
        
        for truck_type in self.available_trucks:
            truck = self.TRUCK_SPECS[truck_type]
            if (max_dims['length'] <= truck['length'] and
                max_dims['width'] <= truck['width'] and
                max_dims['height'] <= truck['height'] and
                self.analysis['max_single_weight'] <= truck['max_weight']):
                compatible.append(truck_type)
        
        return compatible if compatible else self.available_trucks
    
    def suggest_scenarios(self) -> dict:
        compatible_trucks = self._filter_compatible_trucks()
        scenarios = []
        
        # Scénario 1 : Coût Optimal
        scenario_cost = self._optimize_for_cost(compatible_trucks)
        if scenario_cost: scenarios.append(scenario_cost)
        
        # Scénario 2 : Nombre Minimal
        scenario_min = self._optimize_for_truck_count(compatible_trucks)
        if scenario_min: scenarios.append(scenario_min)
        
        # Scénario 3 : Équilibré
        scenario_balanced = self._optimize_balanced(compatible_trucks)
        if scenario_balanced: scenarios.append(scenario_balanced)
        
        # Calculer les coûts
        for scenario in scenarios:
            cost_details = self.cost_calculator.calculate_scenario_cost(
                scenario['trucks'],
                self.distance_km,
                duration_days=scenario.get('estimated_duration_days', 1)
            )
            scenario['cost_details'] = cost_details
            scenario['total_cost'] = cost_details['total_cost']
        
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

    def _allocate_items_to_trucks(self, truck_priority: List[Tuple]) -> List[dict]:
        """Logique d'allocation corrigée et réaliste"""
        remaining_volume = self.analysis['total_volume_m3']
        remaining_weight = self.analysis['total_weight_kg']
        
        # Facteur de sécurité pour le remplissage (on ne remplit jamais à 100% en réel)
        SAFETY_FACTOR = 0.85 
        
        trucks_needed = {}
        
        # Tant qu'il reste de la marchandise
        while remaining_volume > 0.05 or remaining_weight > 10:
            # Trouver le meilleur camion dans la liste de priorité
            best_truck_type = truck_priority[0][0]
            truck_spec = self.TRUCK_SPECS[best_truck_type]
            
            # Capacité utile avec facteur de sécurité
            usable_volume = truck_spec['volume'] * SAFETY_FACTOR
            usable_weight = truck_spec['max_weight'] * SAFETY_FACTOR
            
            # Combien ce camion prend-il ?
            vol_to_take = min(remaining_volume, usable_volume)
            weight_to_take = min(remaining_weight, usable_weight)
            
            if best_truck_type not in trucks_needed:
                trucks_needed[best_truck_type] = {
                    "type": best_truck_type,
                    "name": truck_spec['name'],
                    "quantity": 0,
                    "volume_used": 0,
                    "weight_used": 0,
                    "volume_capacity": truck_spec['volume'],
                    "weight_capacity": truck_spec['max_weight']
                }
            
            trucks_needed[best_truck_type]['quantity'] += 1
            trucks_needed[best_truck_type]['volume_used'] += vol_to_take
            trucks_needed[best_truck_type]['weight_used'] += weight_to_take
            
            remaining_volume -= vol_to_take
            remaining_weight -= weight_to_take
            
            # Sécurité anti-boucle
            if sum(t['quantity'] for t in trucks_needed.values()) > 50:
                break
                
        result = []
        for t in trucks_needed.values():
            # Taux de remplissage par camion individuel
            v_fill = (t['volume_used'] / t['quantity']) / t['volume_capacity']
            w_fill = (t['weight_used'] / t['quantity']) / t['weight_capacity']
            t['fill_rate'] = round(max(v_fill, w_fill), 2)
            result.append(t)
            
        return result

    def _optimize_for_cost(self, compatible_trucks: List[str]) -> dict:
        truck_efficiency = []
        for t in compatible_trucks:
            truck = self.TRUCK_SPECS[t]
            cost = self.cost_calculator.TRUCK_COSTS[t]['fixed'] + (self.cost_calculator.TRUCK_COSTS[t]['per_km'] * self.distance_km)
            efficiency = truck['volume'] / cost
            truck_efficiency.append((t, efficiency))
        
        truck_efficiency.sort(key=lambda x: x[1], reverse=True)
        trucks = self._allocate_items_to_trucks(truck_efficiency)
        
        return {
            "id": "scenario_cost_optimal",
            "name": "Coût Optimal",
            "description": "Minimise le coût total du transport",
            "trucks": trucks,
            "total_trucks": sum(t['quantity'] for t in trucks),
            "average_fill_rate": sum(t['fill_rate'] for t in trucks) / len(trucks) if trucks else 0,
            "estimated_duration_days": 1
        }

    def _optimize_for_truck_count(self, compatible_trucks: List[str]) -> dict:
        truck_vol = [(t, self.TRUCK_SPECS[t]['volume']) for t in compatible_trucks]
        truck_vol.sort(key=lambda x: x[1], reverse=True)
        trucks = self._allocate_items_to_trucks(truck_vol)
        
        return {
            "id": "scenario_min_trucks",
            "name": "Nombre Minimal",
            "description": "Utilise les plus gros camions",
            "trucks": trucks,
            "total_trucks": sum(t['quantity'] for t in trucks),
            "average_fill_rate": sum(t['fill_rate'] for t in trucks) / len(trucks) if trucks else 0,
            "estimated_duration_days": 1
        }

    def _optimize_balanced(self, compatible_trucks: List[str]) -> dict:
        # Priorité au camion 26t ou 40t si disponible
        priority = []
        for t in compatible_trucks:
            score = 100 if t in ['truck_26t', 'truck_40t'] else 50
            priority.append((t, score))
        
        priority.sort(key=lambda x: x[1], reverse=True)
        trucks = self._allocate_items_to_trucks(priority)
        
        return {
            "id": "scenario_balanced",
            "name": "Équilibré",
            "description": "Compromis coût et sécurité",
            "trucks": trucks,
            "total_trucks": sum(t['quantity'] for t in trucks),
            "average_fill_rate": sum(t['fill_rate'] for t in trucks) / len(trucks) if trucks else 0,
            "estimated_duration_days": 1
        }
