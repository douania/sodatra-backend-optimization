"""
Module de calcul des coûts de transport SODATRA
"""

class CostCalculator:
    """Calculateur de coûts pour les différents types de camions"""
    
    # Tarifs SODATRA (en FCFA)
    # À ajuster selon les tarifs réels de SODATRA
    TRUCK_COSTS = {
        "truck_19t": {
            "name": "Camion 19 tonnes",
            "fixed": 150000,      # Coût fixe de mobilisation (FCFA)
            "per_km": 350,        # Coût par kilomètre (FCFA/km)
            "per_hour": 5000,     # Coût par heure d'immobilisation
            "loading_time": 2     # Temps de chargement estimé (heures)
        },
        "truck_26t": {
            "name": "Camion 26 tonnes",
            "fixed": 200000,
            "per_km": 450,
            "per_hour": 6500,
            "loading_time": 3
        },
        "truck_40t": {
            "name": "Camion 40 tonnes (Semi-remorque)",
            "fixed": 300000,
            "per_km": 600,
            "per_hour": 8000,
            "loading_time": 4
        },
        "van_3t5": {
            "name": "Camionnette 3.5 tonnes",
            "fixed": 75000,
            "per_km": 200,
            "per_hour": 3000,
            "loading_time": 1
        }
    }
    
    # Frais additionnels
    ADDITIONAL_FEES = {
        "insurance_rate": 0.02,        # 2% de la valeur déclarée
        "handling_per_ton": 2500,      # Manutention par tonne
        "overnight_storage": 15000,    # Stockage nuit si nécessaire
        "escort_convoy": 50000,        # Escorte pour convoi exceptionnel
        "weekend_surcharge": 0.25      # 25% de majoration weekend
    }
    
    def __init__(self):
        pass
    
    def calculate_truck_cost(self, truck_type: str, quantity: int, distance_km: float, 
                            duration_days: float = 1, cargo_value: float = 0) -> dict:
        """
        Calcule le coût pour un type de camion donné
        
        Args:
            truck_type: Type de camion (ex: "truck_26t")
            quantity: Nombre de camions de ce type
            distance_km: Distance à parcourir en km
            duration_days: Durée estimée du transport en jours
            cargo_value: Valeur déclarée de la marchandise (pour assurance)
        
        Returns:
            dict avec détails des coûts
        """
        if truck_type not in self.TRUCK_COSTS:
            raise ValueError(f"Type de camion inconnu: {truck_type}")
        
        truck_info = self.TRUCK_COSTS[truck_type]
        
        # Coûts de base
        fixed_cost = truck_info['fixed'] * quantity
        transport_cost = truck_info['per_km'] * distance_km * quantity
        loading_cost = truck_info['per_hour'] * truck_info['loading_time'] * quantity
        
        # Coûts additionnels
        insurance_cost = 0
        if cargo_value > 0:
            insurance_cost = cargo_value * self.ADDITIONAL_FEES['insurance_rate']
        
        # Stockage si transport > 1 jour
        storage_cost = 0
        if duration_days > 1:
            storage_cost = self.ADDITIONAL_FEES['overnight_storage'] * (duration_days - 1) * quantity
        
        # Total
        subtotal = fixed_cost + transport_cost + loading_cost + storage_cost
        total = subtotal + insurance_cost
        
        return {
            "truck_type": truck_type,
            "truck_name": truck_info['name'],
            "quantity": quantity,
            "breakdown": {
                "fixed_cost": fixed_cost,
                "transport_cost": transport_cost,
                "loading_cost": loading_cost,
                "storage_cost": storage_cost,
                "insurance_cost": insurance_cost
            },
            "subtotal": subtotal,
            "total": total,
            "per_truck": total / quantity if quantity > 0 else 0
        }
    
    def calculate_scenario_cost(self, trucks: list, distance_km: float, 
                               duration_days: float = 1, cargo_value: float = 0,
                               is_weekend: bool = False, needs_escort: bool = False) -> dict:
        """
        Calcule le coût total d'un scénario multi-camions
        
        Args:
            trucks: Liste de dict avec 'type' et 'quantity'
            distance_km: Distance totale
            duration_days: Durée estimée
            cargo_value: Valeur de la marchandise
            is_weekend: Si transport en weekend
            needs_escort: Si convoi exceptionnel nécessitant escorte
        
        Returns:
            dict avec coût total et détails
        """
        total_cost = 0
        truck_costs = []
        
        # Calculer coût pour chaque type de camion
        for truck in trucks:
            truck_cost = self.calculate_truck_cost(
                truck['type'],
                truck['quantity'],
                distance_km,
                duration_days,
                cargo_value
            )
            truck_costs.append(truck_cost)
            total_cost += truck_cost['total']
        
        # Frais additionnels globaux
        additional_costs = {}
        
        if needs_escort:
            additional_costs['escort'] = self.ADDITIONAL_FEES['escort_convoy']
            total_cost += additional_costs['escort']
        
        if is_weekend:
            weekend_surcharge = total_cost * self.ADDITIONAL_FEES['weekend_surcharge']
            additional_costs['weekend_surcharge'] = weekend_surcharge
            total_cost += weekend_surcharge
        
        return {
            "total_cost": round(total_cost),
            "total_cost_formatted": f"{round(total_cost):,} FCFA",
            "truck_costs": truck_costs,
            "additional_costs": additional_costs,
            "cost_per_km": round(total_cost / distance_km) if distance_km > 0 else 0
        }
    
    def compare_scenarios(self, scenarios: list) -> dict:
        """
        Compare plusieurs scénarios et identifie le plus économique
        
        Args:
            scenarios: Liste de scénarios avec leurs coûts
        
        Returns:
            dict avec comparaison et recommandation
        """
        if not scenarios:
            return {}
        
        # Trouver le moins cher
        cheapest = min(scenarios, key=lambda s: s.get('total_cost', float('inf')))
        most_expensive = max(scenarios, key=lambda s: s.get('total_cost', 0))
        
        # Calculer économies potentielles
        savings = most_expensive.get('total_cost', 0) - cheapest.get('total_cost', 0)
        savings_percent = (savings / most_expensive.get('total_cost', 1)) * 100 if most_expensive.get('total_cost', 0) > 0 else 0
        
        return {
            "cheapest_scenario": cheapest.get('id'),
            "most_expensive_scenario": most_expensive.get('id'),
            "potential_savings": round(savings),
            "potential_savings_percent": round(savings_percent, 1),
            "recommendation": cheapest.get('id')
        }
