"""
Module d'optimisation de flotte multi-camions - Support Convois Exceptionnels
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
        "heavy_modular": {
            "name": "Convoi Exceptionnel (Remorque Modulaire)",
            "length": 2000,
            "width": 350,
            "height": 450,
            "max_weight": 100000, # 100 tonnes
            "volume": 315.0
        },
        "truck_40t": {
            "name": "Camion 40 tonnes (Semi-remorque)",
            "length": 1360,
            "width": 248,
            "height": 270,
            "max_weight": 40000,
            "volume": 91.06
        },
        "truck_26t": {
            "name": "Camion 26 tonnes",
            "length": 1200,
            "width": 248,
            "height": 270,
            "max_weight": 26000,
            "volume": 80.35
        },
        "truck_19t": {
            "name": "Camion 19 tonnes",
            "length": 600,
            "width": 240,
            "height": 240,
            "max_weight": 19000,
            "volume": 34.56
        },
        "van_3t5": {
            "name": "Camionnette 3.5 tonnes",
            "length": 420,
            "width": 200,
            "height": 200,
            "max_weight": 3500,
            "volume": 16.8
        }
    }
    
    def __init__(self, items: List[Item], distance_km: float = 100, 
                 available_trucks: List[str] = None, constraints: dict = None):
        self.items = items
        self.distance_km = distance_km
        self.available_trucks = available_trucks or list(self.TRUCK_SPECS.keys())
        self.cost_calculator = CostCalculator()
        self.analysis = self._analyze_items()
    
    def _analyze_items(self) -> dict:
        total_volume = 0
        total_weight = 0
        max_length = 0
        max_width = 0
        max_height = 0
        max_single_weight = 0
        
        for item in self.items:
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
            "max_single_weight": max_single_weight,
            "max_dimensions": {"length": max_length, "width": max_width, "height": max_height},
            "total_pieces": sum(item.quantity for item in self.items)
        }

    def _allocate_items_to_trucks(self, truck_priority: List[Tuple]) -> List[dict]:
        """Allocation intelligente gérant les charges lourdes et volumineuses"""
        # On sépare les articles en 2 catégories : Exceptionnels et Standards
        heavy_items = []
        standard_items_volume = 0
        standard_items_weight = 0
        
        for item in self.items:
            # Si l'article dépasse les capacités d'un camion 40t standard
            if item.weight > 35000 or item.length > 1360 or item.width > 248:
                for _ in range(item.quantity):
                    heavy_items.append(item)
            else:
                standard_items_volume += ((item.length * item.width * item.height) / 1_000_000) * item.quantity
                standard_items_weight += item.weight * item.quantity
        
        trucks_needed = []
        
        # 1. Gérer les articles exceptionnels (1 par remorque modulaire par défaut pour sécurité)
        for item in heavy_items:
            spec = self.TRUCK_SPECS["heavy_modular"]
            trucks_needed.append({
                "type": "heavy_modular",
                "name": spec["name"],
                "quantity": 1,
                "volume_used": (item.length * item.width * item.height) / 1_000_000,
                "weight_used": item.weight,
                "fill_rate": round(item.weight / spec["max_weight"], 2),
                "is_special": True
            })
            
        # 2. Gérer le reste avec la logique standard
        remaining_vol = standard_items_volume
        remaining_weight = standard_items_weight
        
        # Filtrer les camions standards de la priorité
        standard_priority = [p for p in truck_priority if p[0] != "heavy_modular"]
        if not standard_priority: # Fallback
            standard_priority = [("truck_40t", 100)]

        while remaining_vol > 0.05 or remaining_weight > 10:
            best_t_type = standard_priority[0][0]
            spec = self.TRUCK_SPECS[best_t_type]
            
            # Facteur de remplissage réaliste 85%
            vol_to_take = min(remaining_vol, spec["volume"] * 0.85)
            weight_to_take = min(remaining_weight, spec["max_weight"] * 0.85)
            
            trucks_needed.append({
                "type": best_t_type,
                "name": spec["name"],
                "quantity": 1,
                "volume_used": vol_to_take,
                "weight_used": weight_to_take,
                "fill_rate": round(max(vol_to_take/spec["volume"], weight_to_take/spec["max_weight"]), 2),
                "is_special": False
            })
            
            remaining_vol -= vol_to_take
            remaining_weight -= weight_to_take
            if len(trucks_needed) > 100: break

        # Grouper par type pour l'affichage
        grouped = {}
        for t in trucks_needed:
            t_type = t["type"]
            if t_type not in grouped:
                grouped[t_type] = t
                grouped[t_type]["quantity"] = 0
                grouped[t_type]["total_weight"] = 0
            grouped[t_type]["quantity"] += 1
            grouped[t_type]["total_weight"] += t["weight_used"]
            
        return list(grouped.values())

    def suggest_scenarios(self) -> dict:
        # Scénario unique adapté aux charges lourdes
        priority = [("truck_40t", 100), ("truck_26t", 80), ("heavy_modular", 50)]
        trucks = self._allocate_items_to_trucks(priority)
        
        # Calcul des coûts (simplifié pour le convoi exceptionnel)
        total_cost = 0
        for t in trucks:
            if t["type"] == "heavy_modular":
                total_cost += 1500000 # Forfait convoi exceptionnel
            else:
                cost_info = self.cost_calculator.TRUCK_COSTS.get(t["type"], {"fixed": 300000, "per_km": 600})
                total_cost += (cost_info["fixed"] + cost_info["per_km"] * self.distance_km) * t["quantity"]

        scenario = {
            "id": "heavy_load_optimized",
            "name": "Optimisation Charges Lourdes",
            "description": "Solution incluant des convois exceptionnels pour les transformateurs",
            "trucks": trucks,
            "total_trucks": sum(t["quantity"] for t in trucks),
            "total_cost": total_cost,
            "average_fill_rate": 0.8,
            "estimated_duration_days": 2
        }
        
        return {
            "success": True,
            "scenarios": [scenario],
            "recommended_scenario": "heavy_load_optimized",
            "analysis": self.analysis
        }
