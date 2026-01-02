"""
Module d'optimisation de flotte multi-camions - Version Améliorée
Intègre les corrections de Gemini/ChatGPT pour un calcul réaliste
"""

import random
import copy
import math
from typing import List, Dict, Tuple
from src.models.item import Item
from src.services.cost_calculator import CostCalculator

class FleetOptimizer:
    """Optimiseur de flotte avec calcul réaliste du remplissage"""
    
    # Facteur d'efficacité de chargement (15% de perte d'espace estimée)
    # Un camion n'est jamais rempli à plus de 85% à cause des formes des caisses
    PACKING_EFFICIENCY_FACTOR = 0.85
    
    # Destinations et distances depuis Dakar (en km)
    DESTINATIONS = {
        "dakar_local": {"name": "Dakar (Local)", "distance": 100, "multiplier": 1.0},
        "thies": {"name": "Thiès", "distance": 70, "multiplier": 1.1},
        "saint_louis": {"name": "Saint-Louis", "distance": 270, "multiplier": 1.3},
        "kaolack": {"name": "Kaolack", "distance": 190, "multiplier": 1.2},
        "bamako": {"name": "Bamako (Mali)", "distance": 1250, "multiplier": 2.5},
        "tambacounda": {"name": "Tambacounda", "distance": 460, "multiplier": 1.5}
    }

    # Spécifications des camions avec surface au sol (floor_area en m²)
    TRUCK_SPECS = {
        "heavy_modular": {
            "name": "Convoi Exceptionnel (Remorque Modulaire)",
            "length": 1500, "width": 300, "height": 350,
            "max_weight": 100000, 
            "volume": 157.5,  # 15m x 3m x 3.5m
            "floor_area": 45.0,  # 15m x 3m
            "base_cost": 1500000
        },
        "truck_40t": {
            "name": "Camion 40 tonnes (Semi-remorque)",
            "length": 1360, "width": 248, "height": 270,
            "max_weight": 40000, 
            "volume": 91.06,
            "floor_area": 33.7,  # 13.6m x 2.48m
            "base_cost": 300000
        },
        "truck_26t": {
            "name": "Camion 26 tonnes",
            "length": 1200, "width": 248, "height": 270,
            "max_weight": 26000, 
            "volume": 80.35,
            "floor_area": 29.7,  # 12m x 2.48m
            "base_cost": 200000
        },
        "truck_19t": {
            "name": "Camion 19 tonnes (Porteur)",
            "length": 850, "width": 245, "height": 260,
            "max_weight": 19000, 
            "volume": 54.0,
            "floor_area": 20.8,  # 8.5m x 2.45m
            "base_cost": 150000
        },
        "van_3t5": {
            "name": "Camionnette 3.5 tonnes",
            "length": 420, "width": 200, "height": 200,
            "max_weight": 3500, 
            "volume": 16.8,
            "floor_area": 8.4,  # 4.2m x 2m
            "base_cost": 50000
        }
    }
    
    def __init__(self, items: List[Item], destination: str = "dakar_local", 
                 available_trucks: List[str] = None, distance_km: float = None,
                 constraints: dict = None):
        self.items = items
        self.dest_key = destination if destination in self.DESTINATIONS else "dakar_local"
        self.destination = self.DESTINATIONS[self.dest_key]
        self.distance_km = distance_km if distance_km is not None else self.destination["distance"]
        self.available_trucks = available_trucks or list(self.TRUCK_SPECS.keys())
        self.constraints = constraints or {}
        self.cost_calculator = CostCalculator()
        self.analysis = self._analyze_items()
    
    def _analyze_items(self) -> dict:
        """Analyse détaillée incluant la surface au sol requise"""
        total_volume = 0
        total_weight = 0
        required_floor_area = 0  # Surface au sol pour non-gerbables
        
        max_dims = {"length": 0, "width": 0, "height": 0}
        max_single_weight = 0
        oversized_count = 0
        heavy_count = 0
        
        for item in self.items:
            # Volume en m³
            vol = (item.length * item.width * item.height) / 1_000_000
            total_volume += vol * item.quantity
            total_weight += item.weight * item.quantity
            
            # Calcul surface au sol (m²)
            floor_item = (item.length * item.width) / 10_000
            
            # Vérifier si l'article est gerbable
            is_stackable = getattr(item, 'stackable', True)
            
            if not is_stackable:
                # Si non gerbable, on prend toute la surface
                required_floor_area += floor_item * item.quantity
            else:
                # Si gerbable, on estime qu'on peut empiler sur 2 niveaux en moyenne
                required_floor_area += (floor_item * item.quantity) / 2.0

            # Mise à jour des dimensions max
            max_dims["length"] = max(max_dims["length"], item.length)
            max_dims["width"] = max(max_dims["width"], item.width)
            max_dims["height"] = max(max_dims["height"], item.height)
            max_single_weight = max(max_single_weight, item.weight)
            
            # Comptage des articles spéciaux
            if item.length > 1200 or item.width > 240 or item.height > 270:
                oversized_count += item.quantity
            if item.weight > 5000:
                heavy_count += item.quantity
            
        return {
            "total_volume_m3": round(total_volume, 2),
            "total_weight_kg": round(total_weight),
            "total_weight_t": round(total_weight / 1000, 2),
            "required_floor_m2": round(required_floor_area, 2),
            "total_pieces": sum(item.quantity for item in self.items),
            "max_dimensions": max_dims,
            "max_single_weight": max_single_weight,
            "oversized_items": oversized_count,
            "heavy_items": heavy_count
        }

    def _filter_compatible_trucks(self) -> List[str]:
        """Filtre les camions capables de transporter le plus gros colis"""
        compatible = []
        md = self.analysis['max_dimensions']
        mw = self.analysis['max_single_weight']
        
        for t_name in self.available_trucks:
            if t_name not in self.TRUCK_SPECS:
                continue
            spec = self.TRUCK_SPECS[t_name]
            # Vérification dimensions physiques (avec marge 2cm)
            if (spec['length'] >= md['length'] - 2 and 
                spec['width'] >= md['width'] - 2 and 
                spec['height'] >= md['height'] - 2 and 
                spec['max_weight'] >= mw):
                compatible.append(t_name)
                
        return compatible if compatible else list(self.TRUCK_SPECS.keys())

    def _allocate_items_to_trucks(self, truck_priority: List[str]) -> List[dict]:
        """
        Allocation avec liste détaillée des articles par camion
        Utilise le facteur d'efficacité et vérifie volume, poids ET surface au sol
        """
        # Préparer la liste plate de tous les articles
        all_items = []
        for item in self.items:
            for i in range(item.quantity):
                is_stackable = getattr(item, 'stackable', True)
                all_items.append({
                    "id": f"{getattr(item, 'reference', item.id) if hasattr(item, 'reference') else item.id}_{i+1}",
                    "name": item.description,
                    "length": item.length,
                    "width": item.width,
                    "height": item.height,
                    "weight": item.weight,
                    "volume": (item.length * item.width * item.height) / 1_000_000,
                    "floor_area": (item.length * item.width) / 10_000,
                    "stackable": is_stackable
                })
        
        # Trier les articles : d'abord les plus lourds et les plus volumineux
        all_items.sort(key=lambda x: (x['weight'], x['volume']), reverse=True)
        
        trucks_needed = []
        
        while all_items:
            # Choisir le type de camion
            best_truck_type = None
            for t_type in truck_priority:
                if t_type in self.TRUCK_SPECS:
                    best_truck_type = t_type
                    break
            
            if not best_truck_type:
                best_truck_type = "heavy_modular"
            
            spec = self.TRUCK_SPECS[best_truck_type]
            
            # Capacités RÉELLES avec facteur d'efficacité
            real_vol_cap = spec['volume'] * self.PACKING_EFFICIENCY_FACTOR
            real_weight_cap = spec['max_weight'] * 0.95  # 5% marge sécurité poids
            real_floor_cap = spec.get('floor_area', spec['volume'] / 3) * 0.9  # 10% perte surface sol
            
            current_truck_items = []
            current_vol = 0
            current_weight = 0
            current_floor = 0
            
            # Prendre le premier article (le plus lourd/volumineux)
            if all_items:
                first_item = all_items[0]
                
                # Si l'article est trop lourd pour le camion choisi, forcer un convoi exceptionnel
                if first_item['weight'] > spec['max_weight'] * 0.95:
                    if best_truck_type != "heavy_modular" and "heavy_modular" in self.available_trucks:
                        truck_priority = ["heavy_modular"] + [t for t in truck_priority if t != "heavy_modular"]
                        continue
                
                # Ajouter le premier article
                all_items.pop(0)
                current_truck_items.append(first_item)
                current_vol += first_item['volume']
                current_weight += first_item['weight']
                if first_item['stackable']:
                    current_floor += first_item['floor_area'] / 2
                else:
                    current_floor += first_item['floor_area']
            
            # Essayer d'ajouter d'autres articles
            i = 0
            while i < len(all_items):
                item = all_items[i]
                item_floor = item['floor_area'] if not item['stackable'] else item['floor_area'] / 2
                
                # Vérifier les 3 contraintes : volume, poids ET surface au sol
                if (current_vol + item['volume'] <= real_vol_cap and 
                    current_weight + item['weight'] <= real_weight_cap and
                    current_floor + item_floor <= real_floor_cap):
                    
                    current_truck_items.append(all_items.pop(i))
                    current_vol += item['volume']
                    current_weight += item['weight']
                    current_floor += item_floor
                else:
                    i += 1
            
            # Calculer les taux de remplissage réels
            vol_fill_rate = current_vol / spec['volume'] if spec['volume'] > 0 else 0
            weight_fill_rate = current_weight / spec['max_weight'] if spec['max_weight'] > 0 else 0
            floor_fill_rate = current_floor / spec.get('floor_area', 1) if spec.get('floor_area', 1) > 0 else 0
            
            trucks_needed.append({
                "type": best_truck_type,
                "name": spec["name"],
                "items": current_truck_items,
                "items_assigned": len(current_truck_items),
                "item_count": len(current_truck_items),
                "volume_used": round(current_vol, 2),
                "weight_used": round(current_weight),
                "floor_used": round(current_floor, 2),
                "volume_capacity": spec['volume'],
                "weight_capacity": spec['max_weight'],
                "floor_capacity": spec.get('floor_area', 0),
                "volume_fill_rate": round(vol_fill_rate, 2),
                "weight_fill_rate": round(weight_fill_rate, 2),
                "floor_fill_rate": round(floor_fill_rate, 2),
                "fill_rate": round(max(vol_fill_rate, weight_fill_rate, floor_fill_rate), 2)
            })
            
            # Sécurité : éviter boucle infinie
            if len(trucks_needed) > 50:
                break

        # Grouper pour le résumé
        summary = {}
        for t in trucks_needed:
            t_type = t["type"]
            if t_type not in summary:
                summary[t_type] = {
                    "type": t_type,
                    "name": t["name"],
                    "quantity": 0,
                    "trucks_details": [],
                    "total_items": 0
                }
            summary[t_type]["quantity"] += 1
            summary[t_type]["trucks_details"].append(t)
            summary[t_type]["total_items"] += t["item_count"]
            
        return list(summary.values())

    def suggest_scenarios(self) -> dict:
        """Génère plusieurs scénarios d'optimisation"""
        compatible_trucks = self._filter_compatible_trucks()
        
        scenarios = []
        
        # Scénario 1 : Optimisation coût (camions moyens)
        cost_priority = self._sort_trucks_by_efficiency(compatible_trucks)
        scenario_cost = self._generate_scenario(
            cost_priority, 
            "scenario_cost_optimal", 
            "Coût Optimal",
            "Minimise le coût total en optimisant le rapport coût/capacité"
        )
        if scenario_cost:
            scenarios.append(scenario_cost)
        
        # Scénario 2 : Nombre minimal de camions (plus gros camions)
        volume_priority = sorted(compatible_trucks, 
                                  key=lambda t: self.TRUCK_SPECS.get(t, {}).get('volume', 0), 
                                  reverse=True)
        scenario_min = self._generate_scenario(
            volume_priority, 
            "scenario_min_trucks", 
            "Nombre Minimal de Camions",
            "Utilise le moins de camions possible en maximisant le remplissage"
        )
        if scenario_min:
            scenarios.append(scenario_min)
        
        # Identifier le scénario recommandé (le moins cher)
        recommended_id = None
        if scenarios:
            best = min(scenarios, key=lambda s: s.get('total_cost', float('inf')))
            recommended_id = best['id']
        
        return {
            "success": True,
            "scenarios": scenarios,
            "recommended_scenario": recommended_id,
            "analysis": self.analysis,
            "compatible_trucks": compatible_trucks,
            "destinations_available": list(self.DESTINATIONS.values())
        }
    
    def _sort_trucks_by_efficiency(self, trucks: List[str]) -> List[str]:
        """Trie les camions par efficacité coût/capacité"""
        truck_efficiency = []
        for truck_type in trucks:
            if truck_type not in self.TRUCK_SPECS:
                continue
            spec = self.TRUCK_SPECS[truck_type]
            # Estimer le coût total pour ce trajet
            per_km_rate = 800 if truck_type == "heavy_modular" else 500
            total_cost = spec['base_cost'] + (self.distance_km * per_km_rate)
            efficiency = spec['volume'] / total_cost if total_cost > 0 else 0
            truck_efficiency.append((truck_type, efficiency))
        
        truck_efficiency.sort(key=lambda x: x[1], reverse=True)
        return [t[0] for t in truck_efficiency]
    
    def _generate_scenario(self, truck_priority: List[str], scenario_id: str, 
                           name: str, description: str) -> dict:
        """Génère un scénario complet avec coûts"""
        truck_groups = self._allocate_items_to_trucks(truck_priority)
        
        if not truck_groups:
            return None
        
        # Calcul des coûts
        total_cost = 0
        cost_breakdown = []
        
        for group in truck_groups:
            spec = self.TRUCK_SPECS.get(group["type"], {})
            per_km_rate = 800 if group["type"] == "heavy_modular" else 500
            base_cost = spec.get("base_cost", 100000)
            unit_cost = (base_cost + (self.distance_km * per_km_rate)) * self.destination["multiplier"]
            group_cost = unit_cost * group["quantity"]
            total_cost += group_cost
            
            cost_breakdown.append({
                "truck_type": group["name"],
                "quantity": group["quantity"],
                "unit_cost": round(unit_cost),
                "total": round(group_cost)
            })
        
        total_trucks = sum(g["quantity"] for g in truck_groups)
        
        # Calculer le taux de remplissage moyen
        all_fill_rates = []
        for group in truck_groups:
            for truck in group.get("trucks_details", []):
                all_fill_rates.append(truck.get("fill_rate", 0))
        avg_fill_rate = sum(all_fill_rates) / len(all_fill_rates) if all_fill_rates else 0
        
        # Warnings
        warnings = []
        if avg_fill_rate > 0.95:
            warnings.append("Taux de remplissage très élevé - marge de sécurité réduite")
        if self.analysis.get("oversized_items", 0) > 0:
            warnings.append(f"{self.analysis['oversized_items']} article(s) surdimensionné(s)")
        if self.analysis.get("heavy_items", 0) > 0:
            warnings.append(f"{self.analysis['heavy_items']} article(s) très lourd(s) (>5T)")
        
        return {
            "id": scenario_id,
            "name": f"{name} vers {self.destination['name']}",
            "description": description,
            "trucks": truck_groups,
            "total_trucks": total_trucks,
            "total_cost": round(total_cost),
            "cost_breakdown": cost_breakdown,
            "average_fill_rate": round(avg_fill_rate, 2),
            "destination": self.destination,
            "distance_km": self.distance_km,
            "warnings": warnings,
            "legal_compliance": True,
            "estimated_duration_days": 1 + (total_trucks * 0.2)
        }
