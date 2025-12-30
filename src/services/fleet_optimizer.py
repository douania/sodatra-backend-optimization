"""
Module d'optimisation de flotte multi-camions - Version Détaillée avec Destinations
"""

import random
import copy
import math
from typing import List, Dict, Tuple
from src.models.item import Item
from src.services.cost_calculator import CostCalculator

class FleetOptimizer:
    """Optimiseur de flotte avec détail par camion et gestion des destinations"""
    
    # Destinations et distances depuis Dakar (en km)
    DESTINATIONS = {
        "dakar_local": {"name": "Dakar (Local)", "distance": 50, "multiplier": 1.0},
        "thies": {"name": "Thiès", "distance": 70, "multiplier": 1.1},
        "saint_louis": {"name": "Saint-Louis", "distance": 270, "multiplier": 1.3},
        "kaolack": {"name": "Kaolack", "distance": 190, "multiplier": 1.2},
        "bamako": {"name": "Bamako (Mali)", "distance": 1250, "multiplier": 2.5},
        "tambacounda": {"name": "Tambacounda", "distance": 460, "multiplier": 1.5}
    }

    TRUCK_SPECS = {
        "heavy_modular": {
            "name": "Convoi Exceptionnel (Remorque Modulaire)",
            "length": 2000, "width": 350, "height": 450,
            "max_weight": 100000, "volume": 315.0, "base_cost": 1500000
        },
        "truck_40t": {
            "name": "Camion 40 tonnes (Semi-remorque)",
            "length": 1360, "width": 248, "height": 270,
            "max_weight": 40000, "volume": 91.06, "base_cost": 300000
        },
        "truck_26t": {
            "name": "Camion 26 tonnes",
            "length": 1200, "width": 248, "height": 270,
            "max_weight": 26000, "volume": 80.35, "base_cost": 200000
        }
    }
    
    def __init__(self, items: List[Item], destination: str = "dakar_local", 
                 available_trucks: List[str] = None):
        self.items = items
        self.dest_key = destination if destination in self.DESTINATIONS else "dakar_local"
        self.destination = self.DESTINATIONS[self.dest_key]
        self.distance_km = self.destination["distance"]
        self.available_trucks = available_trucks or list(self.TRUCK_SPECS.keys())
        self.analysis = self._analyze_items()
    
    def _analyze_items(self) -> dict:
        total_volume = 0
        total_weight = 0
        for item in self.items:
            vol = (item.length * item.width * item.height) / 1_000_000
            total_volume += vol * item.quantity
            total_weight += item.weight * item.quantity
        
        return {
            "total_volume_m3": round(total_volume, 2),
            "total_weight_kg": round(total_weight),
            "total_weight_t": round(total_weight / 1000, 2),
            "total_pieces": sum(item.quantity for item in self.items)
        }

    def _allocate_items_to_trucks(self, truck_priority: List[str]) -> List[dict]:
        """Allocation avec liste détaillée des articles par camion"""
        # Préparer la liste plate de tous les articles
        all_items = []
        for item in self.items:
            for i in range(item.quantity):
                all_items.append({
                    "id": f"{item.reference}_{i+1}",
                    "name": item.description,
                    "length": item.length,
                    "width": item.width,
                    "height": item.height,
                    "weight": item.weight,
                    "volume": (item.length * item.width * item.height) / 1_000_000
                })
        
        # Trier les articles par poids décroissant
        all_items.sort(key=lambda x: x['weight'], reverse=True)
        
        trucks_needed = []
        
        while all_items:
            # Essayer de remplir un camion avec les articles restants
            best_truck_type = truck_priority[0]
            spec = self.TRUCK_SPECS[best_truck_type]
            
            current_truck_items = []
            current_vol = 0
            current_weight = 0
            
            # On prend le premier article (le plus lourd)
            first_item = all_items.pop(0)
            
            # Si l'article est trop lourd pour le camion choisi, on force un convoi exceptionnel
            if first_item['weight'] > spec['max_weight'] * 0.95:
                if best_truck_type != "heavy_modular":
                    # Remettre l'article et changer de priorité pour ce tour
                    all_items.insert(0, first_item)
                    truck_priority = ["heavy_modular"] + [t for t in truck_priority if t != "heavy_modular"]
                    continue
            
            current_truck_items.append(first_item)
            current_vol += first_item['volume']
            current_weight += first_item['weight']
            
            # Essayer d'ajouter d'autres articles plus petits
            i = 0
            while i < len(all_items):
                item = all_items[i]
                if (current_vol + item['volume'] <= spec['volume'] * 0.85 and 
                    current_weight + item['weight'] <= spec['max_weight'] * 0.85):
                    current_truck_items.append(all_items.pop(i))
                    current_vol += item['volume']
                    current_weight += item['weight']
                else:
                    i += 1
            
            trucks_needed.append({
                "type": best_truck_type,
                "name": spec["name"],
                "items": current_truck_items,
                "item_count": len(current_truck_items),
                "volume_used": round(current_vol, 2),
                "weight_used": round(current_weight),
                "volume_capacity": spec['volume'],
                "weight_capacity": spec['max_weight'],
                "fill_rate": round(max(current_vol/spec['volume'], current_weight/spec['max_weight']), 2)
            })
            
            if len(trucks_needed) > 50: break

        # Grouper pour le résumé
        summary = {}
        for t in trucks_needed:
            t_type = t["type"]
            if t_type not in summary:
                summary[t_type] = {
                    "type": t_type,
                    "name": t["name"],
                    "quantity": 0,
                    "trucks_details": []
                }
            summary[t_type]["quantity"] += 1
            summary[t_type]["trucks_details"].append(t)
            
        return list(summary.values())

    def suggest_scenarios(self) -> dict:
        # Scénario unique optimisé
        priority = ["truck_40t", "truck_26t", "heavy_modular"]
        truck_groups = self._allocate_items_to_trucks(priority)
        
        # Calcul des coûts basé sur la destination
        total_cost = 0
        cost_breakdown = []
        
        for group in truck_groups:
            spec = self.TRUCK_SPECS[group["type"]]
            # Coût = (Base + (Distance * Taux)) * Multiplicateur Destination
            per_km_rate = 800 if group["type"] == "heavy_modular" else 500
            unit_cost = (spec["base_cost"] + (self.distance_km * per_km_rate)) * self.destination["multiplier"]
            group_cost = unit_cost * group["quantity"]
            total_cost += group_cost
            
            cost_breakdown.append({
                "truck_type": group["name"],
                "quantity": group["quantity"],
                "unit_cost": round(unit_cost),
                "total": round(group_cost)
            })

        scenario = {
            "id": "sodatra_optimized",
            "name": f"Optimisation vers {self.destination['name']}",
            "description": f"Transport de {self.analysis['total_pieces']} articles sur {self.distance_km} km",
            "trucks": truck_groups,
            "total_trucks": sum(g["quantity"] for g in truck_groups),
            "total_cost": round(total_cost),
            "cost_breakdown": cost_breakdown,
            "destination": self.destination
        }
        
        return {
            "success": True,
            "scenarios": [scenario],
            "analysis": self.analysis,
            "destinations_available": [d for d in self.DESTINATIONS.values()]
        }
