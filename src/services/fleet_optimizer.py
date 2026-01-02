# src/services/fleet_optimizer.py
from __future__ import annotations

from typing import List, Dict, Any, Tuple
import math

from src.models.item import Item, TruckSpecs, calculate_statistics


class FleetOptimizer:
    """
    Pré-dimensionnement flotte + allocation items -> camions.
    Objectif: proposer des scénarios réalistes (project cargo) avant le 3D.
    """

    def __init__(self, available_trucks: List[TruckSpecs]):
        self.available_trucks = available_trucks or []

    def suggest_scenarios(self, items: List[Item], distance_km: float = 0.0) -> List[Dict[str, Any]]:
        items = [i.normalized() for i in (items or [])]
        stats = calculate_statistics(items)

        compatible_trucks = self._filter_compatible_trucks(items, self.available_trucks)
        if not compatible_trucks:
            return [{
                "id": "no_solution",
                "name": "Aucun camion compatible",
                "error": "Items dépassent les capacités dimensionnelles / poids des camions disponibles.",
                "statistics": stats.__dict__,
                "trucks": [],
                "total_cost_fcfa": None
            }]

        # Scénario 1: coût (efficacité FCFA)
        cost_sorted = sorted(compatible_trucks, key=lambda t: self._truck_cost_score(t, distance_km))
        s1 = self._build_scenario("cost_opt", "Optimisation coût", items, cost_sorted, distance_km, stats)

        # Scénario 2: minimiser nb camions (volume décroissant puis charge utile)
        cap_sorted = sorted(compatible_trucks, key=lambda t: (t.volume_m3, t.max_weight), reverse=True)
        s2 = self._build_scenario("min_trucks", "Minimum camions", items, cap_sorted, distance_km, stats)

        # Scénario 3: "équilibré" (mix 26T puis 19T)
        mix = sorted(compatible_trucks, key=lambda t: (self._class_rank(t.id), -t.volume_m3))
        s3 = self._build_scenario("balanced", "Équilibré", items, mix, distance_km, stats)

        # Reco: coût minimal (si coûts fournis)
        scenarios = [s1, s2, s3]
        with_cost = [s for s in scenarios if isinstance(s.get("total_cost_fcfa"), (int, float))]
        if with_cost:
            best = min(with_cost, key=lambda s: s["total_cost_fcfa"])
            best["recommended"] = True

        return scenarios

    # -------------------------
    # Scenario builder
    # -------------------------
    def _build_scenario(self, sid: str, name: str, items: List[Item], truck_priority: List[TruckSpecs], distance_km: float, stats) -> Dict[str, Any]:
        allocation = self._allocate(items, truck_priority)

        total_cost = 0.0
        for t in allocation:
            ts = TruckSpecs.from_dict(t["truck_specs"])
            total_cost += self._truck_cost(ts, distance_km)

        return {
            "id": sid,
            "name": name,
            "statistics": stats.__dict__,
            "trucks": allocation,
            "total_cost_fcfa": round(total_cost, 0),
            "recommended": False
        }

    def _allocate(self, items: List[Item], truck_priority: List[TruckSpecs]) -> List[Dict[str, Any]]:
        # Déplier items unitaires
        units = []
        for it in items:
            itn = it.normalized()
            ref = itn.reference or itn.id or "ITEM"
            for k in range(max(1, itn.quantity)):
                units.append(Item(
                    length=itn.length, width=itn.width, height=itn.height,
                    weight=itn.weight, quantity=1,
                    id=f"{ref}__{k+1}", reference=ref,
                    description=itn.description, fragile=itn.fragile, stackable=itn.stackable
                ))
        # Tri "terrain"
        units.sort(key=lambda u: (u.volume_cm3, u.weight), reverse=True)

        trucks_out = []
        remaining = units[:]

        # allocation itérative
        while remaining:
            placed_any = False
            for spec in truck_priority:
                # si le plus gros item ne peut pas rentrer, skip
                if not self._can_fit_max_item(remaining[0], spec):
                    continue

                bucket = []
                vol_used = 0.0
                w_used = 0.0
                floor_used = 0.0

                # marges (réalisme)
                vol_cap = spec.volume_m3 * 0.88
                w_cap = spec.max_weight * 0.95
                floor_cap = spec.floor_area_m2 * 0.90

                new_remaining = []
                for u in remaining:
                    u_vol = u.volume_m3
                    u_floor = (u.footprint_cm2 / 10_000.0) * (1.0 if not u.stackable else 0.35)

                    # garde-fous dimensions (project cargo)
                    if not self._can_fit_max_item(u, spec):
                        new_remaining.append(u)
                        continue

                    if (vol_used + u_vol <= vol_cap) and (w_used + u.weight <= w_cap) and (floor_used + u_floor <= floor_cap):
                        bucket.append(u)
                        vol_used += u_vol
                        w_used += u.weight
                        floor_used += u_floor
                        placed_any = True
                    else:
                        new_remaining.append(u)

                if bucket:
                    trucks_out.append({
                        "truck_specs": {
                            "id": spec.id,
                            "name": spec.name,
                            "length": spec.length,
                            "width": spec.width,
                            "height": spec.height,
                            "max_weight": spec.max_weight,
                            "base_cost_fcfa": spec.base_cost_fcfa,
                            "cost_per_km_fcfa": spec.cost_per_km_fcfa,
                            "volume_m3": spec.volume_m3,
                            "floor_area_m2": spec.floor_area_m2
                        },
                        "items": [b.to_dict() for b in bucket],
                        "metrics": {
                            "weight_kg": round(w_used, 2),
                            "volume_m3": round(vol_used, 4),
                            "floor_area_m2": round(floor_used, 4),
                            "fill_weight_pct": round((w_used / spec.max_weight) * 100, 2) if spec.max_weight > 0 else 0.0,
                            "fill_volume_pct": round((vol_used / spec.volume_m3) * 100, 2) if spec.volume_m3 > 0 else 0.0,
                            "fill_floor_pct": round((floor_used / spec.floor_area_m2) * 100, 2) if spec.floor_area_m2 > 0 else 0.0,
                        }
                    })
                    remaining = new_remaining
                    break

            if not placed_any:
                # Impossible de placer le reste: convoi exceptionnel / specs manquantes
                # On renvoie un camion "exception" pour ne pas boucler
                trucks_out.append({
                    "truck_specs": {
                        "id": "exception",
                        "name": "Convoi exceptionnel / étude manuelle requise",
                        "length": 0, "width": 0, "height": 0, "max_weight": 0
                    },
                    "items": [r.to_dict() for r in remaining],
                    "metrics": {
                        "reason": "Remaining items exceed available truck constraints"
                    }
                })
                break

        return trucks_out

    # -------------------------
    # Compatibility / costs
    # -------------------------
    def _filter_compatible_trucks(self, items: List[Item], trucks: List[TruckSpecs]) -> List[TruckSpecs]:
        if not trucks:
            return []
        maxL = max(i.length for i in items)
        maxW = max(i.width for i in items)
        maxH = max(i.height for i in items)
        maxWt = max(i.weight for i in items)

        out = []
        for t in trucks:
            # dimension: on tolère rotation L/W, mais pas sur hauteur
            dim_ok = ((maxL <= t.length and maxW <= t.width) or (maxW <= t.length and maxL <= t.width))
            if not dim_ok:
                continue
            if maxH > t.height:
                continue
            if maxWt > t.max_weight:
                continue
            out.append(t)
        return out

    def _can_fit_max_item(self, item: Item, truck: TruckSpecs) -> bool:
        # rotation L/W autorisée
        dim_ok = ((item.length <= truck.length and item.width <= truck.width) or
                  (item.width <= truck.length and item.length <= truck.width))
        if not dim_ok:
            return False
        if item.height > truck.height:
            return False
        if item.weight > truck.max_weight:
            return False
        return True

    def _truck_cost(self, t: TruckSpecs, distance_km: float) -> float:
        return float(t.base_cost_fcfa or 0) + float(t.cost_per_km_fcfa or 0) * float(distance_km or 0)

    def _truck_cost_score(self, t: TruckSpecs, distance_km: float) -> float:
        # score coût par m3 utile (lower is better)
        cost = self._truck_cost(t, distance_km)
        cap = max(1e-9, t.volume_m3)
        return cost / cap

    def _class_rank(self, truck_id: str) -> int:
        # ordre "terrain": 26t -> 19t -> 40t -> lowbed -> van
        truck_id = (truck_id or "").lower()
        if "26" in truck_id:
            return 1
        if "19" in truck_id:
            return 2
        if "40" in truck_id:
            return 3
        if "low" in truck_id or "45" in truck_id:
            return 4
        if "van" in truck_id:
            return 5
        return 9
