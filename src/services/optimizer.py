# src/services/optimizer.py
from __future__ import annotations

from typing import List, Tuple, Dict, Any, Optional
import random
import time
import math

from src.models.item import Item, TruckSpecs, Placement, AlgorithmConfig


class LoadingOptimizer:
    """
    Optimiseur 3D (cm/kg).
    - Heuristique: Extreme Points + Best Fit + rotations
    - GA: seed avec solution heuristique pour convergence rapide
    """

    def optimize(self, items: List[Item], truck: TruckSpecs, config: AlgorithmConfig):
        config = config or AlgorithmConfig()
        # Normaliser + déplier unités
        units = self._expand_items(items, allow_rotation=config.allow_rotation)
        # tri Project Cargo: volume puis poids
        units.sort(key=lambda u: (u.volume_cm3, u.weight), reverse=True)

        if not units:
            return self._result(truck, [], 0, 0)

        if config.algorithm.lower() == "simple":
            placements = self._optimize_simple(units, truck, config)
        else:
            placements = self._optimize_genetic(units, truck, config)

        placed_ids = {p.item_id for p in placements}
        return self._result(truck, placements, len(placed_ids), len(units))

    # ---------------------------
    # Core: Heuristic (Extreme Points)
    # ---------------------------
    def _optimize_simple(self, units: List[Item], truck: TruckSpecs, config: AlgorithmConfig) -> List[Placement]:
        placements: List[Placement] = []
        placed = set()

        max_height = truck.height * float(config.max_height_ratio)

        for u in units:
            if u.id in placed:
                continue

            best = self._find_best_position(u, placements, truck, config, max_height)
            if best is None:
                continue

            x, y, z, L, W, H = best
            placements.append(Placement(
                item_id=u.id,
                x=x, y=y, z=z,
                length=L, width=W, height=H,
                weight=u.weight,
                reference=u.reference,
                stackable=u.stackable
            ))
            placed.add(u.id)

        return placements

    def _find_best_position(
        self,
        u: Item,
        placements: List[Placement],
        truck: TruckSpecs,
        config: AlgorithmConfig,
        max_height: float
    ) -> Optional[Tuple[float, float, float, float, float, float]]:
        """
        Cherche la meilleure position selon "best-fit":
        - essaye rotations
        - essaie points extrêmes
        - fallback sur grille fine
        """
        best_score = None
        best_sol = None

        for (L, W, H) in u.rotations(config.allow_rotation):
            # Check bounding
            if L + config.clearance_cm > truck.length or W + config.clearance_cm > truck.width:
                continue
            if H > max_height:
                continue

            # 1) Extreme points
            for (x, y, z) in self._candidate_points(placements, config):
                if x + L + config.clearance_cm > truck.length:
                    continue
                if y + W + config.clearance_cm > truck.width:
                    continue
                if z + H > max_height:
                    continue
                if self._collides(x, y, z, L, W, H, placements, config):
                    continue
                if not self._supported(x, y, z, L, W, placements, config, u.stackable):
                    continue

                score = self._score_position(x, y, z, L, W, H, placements)
                if best_score is None or score < best_score:
                    best_score, best_sol = score, (x, y, z, L, W, H)

            # 2) fallback grid
            step = max(1, int(config.grid_step_cm))
            for x in range(0, int(truck.length - L) + 1, step):
                for y in range(0, int(truck.width - W) + 1, step):
                    # try z=0 then z candidates
                    for z in self._z_levels(placements):
                        if z + H > max_height:
                            continue
                        if self._collides(x, y, z, L, W, H, placements, config):
                            continue
                        if not self._supported(x, y, z, L, W, placements, config, u.stackable):
                            continue

                        score = self._score_position(x, y, z, L, W, H, placements)
                        if best_score is None or score < best_score:
                            best_score, best_sol = score, (x, y, z, L, W, H)

        return best_sol

    def _candidate_points(self, placements: List[Placement], config: AlgorithmConfig) -> List[Tuple[float, float, float]]:
        """
        Extreme points:
        - origin
        - right of each placement
        - front of each placement
        - on top of each placement (z+H)
        """
        pts = {(0.0, 0.0, 0.0)}
        c = float(config.clearance_cm)

        for p in placements:
            pts.add((p.x + p.length + c, p.y, p.z))
            pts.add((p.x, p.y + p.width + c, p.z))
            pts.add((p.x, p.y, p.z + p.height))  # vertical stacking candidate

        # Tri: z d'abord (bas), puis y, puis x
        out = list(pts)
        out.sort(key=lambda t: (t[2], t[1], t[0]))
        return out

    def _z_levels(self, placements: List[Placement]) -> List[int]:
        levels = {0}
        for p in placements:
            levels.add(int(round(p.z + p.height)))
        out = sorted(levels)
        return out

    def _collides(self, x, y, z, L, W, H, placements: List[Placement], config: AlgorithmConfig) -> bool:
        c = float(config.clearance_cm)
        for p in placements:
            if self._aabb_intersect(x, y, z, L, W, H, p.x, p.y, p.z, p.length, p.width, p.height, c):
                return True
        return False

    def _aabb_intersect(self, ax, ay, az, aL, aW, aH, bx, by, bz, bL, bW, bH, clearance: float) -> bool:
        # collision avec marge (clearance)
        return not (
            ax + aL + clearance <= bx or
            bx + bL + clearance <= ax or
            ay + aW + clearance <= by or
            by + bW + clearance <= ay or
            az + aH <= bz or
            bz + bH <= az
        )

    def _supported(self, x, y, z, L, W, placements: List[Placement], config: AlgorithmConfig, stackable: bool) -> bool:
        """
        Support:
          - au sol => ok
          - sinon => doit être supporté à min_support_ratio
          - interdit d'empiler sur un élément non stackable
        """
        if z <= 0.0:
            return True

        # surface requise
        need = (L * W) * float(config.min_support_ratio)
        supported = 0.0

        # vérifier supports à la même hauteur (z==p.z+p.height)
        for p in placements:
            top = p.z + p.height
            if abs(top - z) > 1e-6:
                continue

            # interdit si support non stackable (on ne charge pas au-dessus)
            if not p.stackable:
                # si overlap, interdit direct
                if self._overlap_area(x, y, L, W, p.x, p.y, p.length, p.width) > 0:
                    return False

            supported += self._overlap_area(x, y, L, W, p.x, p.y, p.length, p.width)

        return supported + 1e-9 >= need if stackable else False

    def _overlap_area(self, ax, ay, aL, aW, bx, by, bL, bW) -> float:
        ix1 = max(ax, bx)
        iy1 = max(ay, by)
        ix2 = min(ax + aL, bx + bL)
        iy2 = min(ay + aW, by + bW)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0
        return (ix2 - ix1) * (iy2 - iy1)

    def _score_position(self, x, y, z, L, W, H, placements: List[Placement]) -> float:
        """
        Score: on minimise
        - z en priorité (stabilité)
        - puis distance à l'origine
        - puis "compacité" (max extent)
        """
        if not placements:
            return z * 1e6 + x + y

        maxX = max((p.x + p.length) for p in placements)
        maxY = max((p.y + p.width) for p in placements)
        maxZ = max((p.z + p.height) for p in placements)

        newMaxX = max(maxX, x + L)
        newMaxY = max(maxY, y + W)
        newMaxZ = max(maxZ, z + H)

        dist = x + y + (z * 10.0)
        compact = (newMaxX * 0.5) + (newMaxY * 0.5) + (newMaxZ * 2.0)
        return (z * 1e6) + dist + compact

    # ---------------------------
    # Genetic algorithm (seeded)
    # ---------------------------
    def _optimize_genetic(self, units: List[Item], truck: TruckSpecs, config: AlgorithmConfig) -> List[Placement]:
        start = time.time()
        timeout = max(10, int(config.timeout_seconds))

        # seed with heuristic
        seed = self._optimize_simple(units, truck, AlgorithmConfig(
            algorithm="simple",
            grid_step_cm=config.grid_step_cm,
            allow_rotation=config.allow_rotation,
            min_support_ratio=config.min_support_ratio,
            clearance_cm=config.clearance_cm,
            max_height_ratio=config.max_height_ratio
        ))

        def fitness(placements: List[Placement]) -> float:
            # maximise placed count, then weight, then volume used
            placed = len({p.item_id for p in placements})
            w = sum(p.weight for p in placements)
            vol = sum(p.length * p.width * p.height for p in placements)  # cm3
            return placed * 1e9 + w * 1e3 + vol

        population: List[List[Placement]] = []
        population.append(seed)

        # random individuals: shuffle order
        for _ in range(max(0, config.population_size - 1)):
            perm = units[:]
            random.shuffle(perm)
            population.append(self._optimize_simple(perm, truck, config))

        best = max(population, key=fitness)

        for gen in range(config.generations):
            if time.time() - start > timeout:
                break

            population.sort(key=fitness, reverse=True)
            elite_count = max(1, int(config.elitism_rate * len(population)))
            new_pop = population[:elite_count]

            # breed
            while len(new_pop) < config.population_size:
                p1 = self._tournament(population, fitness)
                p2 = self._tournament(population, fitness)
                child_units = self._crossover_units(units, p1, p2, config)
                if random.random() < config.mutation_rate:
                    random.shuffle(child_units)
                child = self._optimize_simple(child_units, truck, config)
                new_pop.append(child)

            population = new_pop
            current_best = max(population, key=fitness)
            if fitness(current_best) > fitness(best):
                best = current_best

        return best

    def _tournament(self, population: List[List[Placement]], fitness_fn, k: int = 3) -> List[Placement]:
        sample = random.sample(population, min(k, len(population)))
        return max(sample, key=fitness_fn)

    def _crossover_units(self, original_units: List[Item], p1: List[Placement], p2: List[Placement], config: AlgorithmConfig) -> List[Item]:
        """
        Crossover sur l'ordre des items: on prend un sous-ensemble d'items placés de p1,
        puis on complète avec l'ordre d'origine et/ou p2.
        """
        placed1 = {pl.item_id for pl in p1}
        placed2 = {pl.item_id for pl in p2}

        take = set()
        for u in original_units:
            if u.id in placed1 and random.random() < 0.6:
                take.add(u.id)
            elif u.id in placed2 and random.random() < 0.3:
                take.add(u.id)

        head = [u for u in original_units if u.id in take]
        tail = [u for u in original_units if u.id not in take]
        return head + tail

    # ---------------------------
    # Helpers
    # ---------------------------
    def _expand_items(self, items: List[Item], allow_rotation: bool) -> List[Item]:
        """
        Déplie quantity => items unitaires,
        et utilise un séparateur sûr REF__idx pour éviter bugs avec underscores.
        Si l'item a déjà quantity=1 et un id unique, on le garde tel quel.
        """
        units: List[Item] = []
        seen_ids = set()
        
        for it in items or []:
            itn = it.normalized()
            ref = itn.reference or itn.id or "ITEM"
            qty = max(1, itn.quantity)
            
            # Si quantity=1 et l'item a déjà un id unique (déjà déplié par fleet_optimizer)
            if qty == 1 and itn.id and itn.id not in seen_ids:
                seen_ids.add(itn.id)
                units.append(Item(
                    length=itn.length, width=itn.width, height=itn.height,
                    weight=itn.weight, quantity=1,
                    id=itn.id, reference=ref, description=itn.description,
                    fragile=itn.fragile, stackable=itn.stackable
                ))
            else:
                # Déplier selon quantity
                for k in range(qty):
                    uid = f"{ref}__{k+1}"
                    # S'assurer que l'id est unique
                    while uid in seen_ids:
                        uid = f"{ref}__{k+1}_{len(seen_ids)}"
                    seen_ids.add(uid)
                    units.append(Item(
                        length=itn.length, width=itn.width, height=itn.height,
                        weight=itn.weight, quantity=1,
                        id=uid, reference=ref, description=itn.description,
                        fragile=itn.fragile, stackable=itn.stackable
                    ))
        return units

    def _result(self, truck: TruckSpecs, placements: List[Placement], placed: int, total: int) -> Dict[str, Any]:
        total_weight = sum(p.weight for p in placements)
        total_vol_cm3 = sum(p.length * p.width * p.height for p in placements)

        weight_eff = (total_weight / truck.max_weight) if truck.max_weight > 0 else 0.0
        vol_eff = (total_vol_cm3 / truck.volume_cm3) if truck.volume_cm3 > 0 else 0.0

        return {
            "truck_specs": {
                "length": truck.length,
                "width": truck.width,
                "height": truck.height,
                "max_weight": truck.max_weight,
                "id": truck.id,
                "name": truck.name,
                "volume_m3": truck.volume_m3
            },
            "items_total": total,
            "items_placed": placed,
            "weight_efficiency": round(weight_eff * 100, 2),
            "volume_efficiency": round(vol_eff * 100, 2),
            "placements": [p.to_dict() for p in placements],
        }
