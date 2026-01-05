# src/models/item.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
import math


def _normalize_cm(v: float, is_truck: bool = False) -> float:
    """
    Normalise une dimension vers des centimètres.
    Heuristique robuste (très utile pour PL venant d'Excel / UI):
      - Pour les camions: on garde les valeurs telles quelles (déjà en cm)
      - Pour les items: détection intelligente basée sur les plages réalistes
    
    Plages réalistes pour du cargo (en cm):
      - Longueur: 10 - 1400 cm (0.1m - 14m)
      - Largeur: 10 - 260 cm (0.1m - 2.6m)
      - Hauteur: 10 - 300 cm (0.1m - 3m)
    
    Règles de conversion:
      - v > 10000 => probablement mm, diviser par 10
      - v > 2600 et v <= 10000 => probablement mm, diviser par 10
      - v >= 100 et v <= 2600 => probablement cm, garder tel quel
      - v >= 10 et v < 100 => ambigu, probablement cm
      - v > 0 et v < 10 => probablement m, multiplier par 100
    """
    if v is None:
        return 0.0
    try:
        v = float(v)
    except Exception:
        return 0.0
    
    if v <= 0:
        return 0.0
    
    # Pour les camions, on ne normalise pas (les specs sont déjà en cm)
    if is_truck:
        return v
    
    # Pour les items, détection intelligente
    # Cas 1: Très grande valeur (> 10000) => certainement en mm
    if v > 10000:
        return v * 0.1  # mm -> cm
    
    # Cas 2: Grande valeur (2600 - 10000) => probablement en mm
    # Car une dimension > 26m en cm serait irréaliste
    if v > 2600:
        return v * 0.1  # mm -> cm
    
    # Cas 3: Valeur moyenne (100 - 2600) => probablement en cm
    # C'est la plage réaliste pour du cargo en cm
    if v >= 100:
        return v  # déjà en cm
    
    # Cas 4: Petite valeur (10 - 100) => ambigu, mais probablement cm
    # 10-100 cm = 0.1-1m, réaliste pour petits colis
    if v >= 10:
        return v  # probablement cm
    
    # Cas 5: Très petite valeur (< 10) => probablement en mètres
    # 0.1 - 10 m = 10 - 1000 cm
    return v * 100.0  # m -> cm


def _smart_normalize_item_dimensions(length: float, width: float, height: float) -> tuple:
    """
    Normalise les 3 dimensions d'un item de manière cohérente.
    Analyse les 3 valeurs ensemble pour déterminer l'unité probable.
    """
    dims = [length, width, height]
    
    # Convertir en float
    try:
        dims = [float(d) if d else 0.0 for d in dims]
    except:
        return (0.0, 0.0, 0.0)
    
    # Filtrer les valeurs positives pour l'analyse
    positive_dims = [d for d in dims if d > 0]
    if not positive_dims:
        return (0.0, 0.0, 0.0)
    
    max_dim = max(positive_dims)
    min_dim = min(positive_dims)
    
    # Déterminer l'unité probable basée sur la plus grande dimension
    # et la cohérence entre les dimensions
    
    # Si la plus grande dimension > 10000, c'est certainement en mm
    if max_dim > 10000:
        return tuple(d * 0.1 for d in dims)  # mm -> cm
    
    # Si la plus grande dimension > 1400, probablement en mm
    # (car > 14m en cm serait irréaliste pour du cargo standard)
    # Les plus grands camions font environ 12-14m de long
    if max_dim > 1400:
        return tuple(d * 0.1 for d in dims)  # mm -> cm
    
    # Si la plus grande dimension est entre 500 et 1400, vérifier la cohérence
    # Si les dimensions semblent trop grandes pour du cargo (ex: 1500x1200x1000),
    # c'est probablement en mm
    if max_dim >= 500:
        # Vérifier si les dimensions sont cohérentes avec du cargo en cm
        # Un colis de 5m x 5m x 5m (500x500x500 cm) est déjà très grand
        # Si toutes les dimensions sont > 500, c'est probablement en mm
        large_dims = [d for d in positive_dims if d >= 500]
        if len(large_dims) >= 2:
            # Au moins 2 dimensions >= 500, probablement en mm
            return tuple(d * 0.1 for d in dims)  # mm -> cm
    
    # Si toutes les dimensions sont < 10, probablement en mètres
    if max_dim < 10 and min_dim > 0:
        return tuple(d * 100.0 for d in dims)  # m -> cm
    
    # Sinon, probablement déjà en cm
    return tuple(dims)


@dataclass
class Item:
    """
    Unité d'optimisation (en cm / kg).
    """
    length: float
    width: float
    height: float
    weight: float
    quantity: int = 1
    id: str = ""
    reference: str = ""
    description: str = ""
    fragile: bool = False
    stackable: bool = True  # si False => interdit d'empiler au-dessus

    def normalized(self) -> "Item":
        """Retourne une copie normalisée en cm/kg avec détection intelligente des unités."""
        # Utiliser la normalisation intelligente qui analyse les 3 dimensions ensemble
        norm_l, norm_w, norm_h = _smart_normalize_item_dimensions(
            self.length, self.width, self.height
        )
        return Item(
            length=norm_l,
            width=norm_w,
            height=norm_h,
            weight=float(self.weight or 0.0),
            quantity=max(1, int(self.quantity or 1)),
            id=str(self.id or self.reference or ""),
            reference=str(self.reference or self.id or ""),
            description=str(self.description or ""),
            fragile=bool(self.fragile),
            stackable=bool(self.stackable),
        )

    def rotations(self, allow_rotation: bool = True) -> List[Tuple[float, float, float]]:
        """
        Rotations autorisées: 0° et 90° sur le plan (L/W).
        Project cargo: on évite les rotations verticales (H en base) par défaut.
        """
        L, W, H = self.length, self.width, self.height
        if not allow_rotation:
            return [(L, W, H)]
        # 2 orientations: (L,W,H) et (W,L,H)
        # dédoublonnage si L==W
        if abs(L - W) < 1e-9:
            return [(L, W, H)]
        return [(L, W, H), (W, L, H)]

    @property
    def volume_cm3(self) -> float:
        return float(self.length) * float(self.width) * float(self.height)

    @property
    def volume_m3(self) -> float:
        return self.volume_cm3 / 1_000_000.0

    @property
    def footprint_cm2(self) -> float:
        return float(self.length) * float(self.width)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Item":
        return Item(
            length=float(d.get("length", 0)),
            width=float(d.get("width", 0)),
            height=float(d.get("height", 0)),
            weight=float(d.get("weight", 0)),
            quantity=int(d.get("quantity", 1) or 1),
            id=str(d.get("id", d.get("reference", "")) or ""),
            reference=str(d.get("reference", d.get("id", "")) or ""),
            description=str(d.get("description", "") or ""),
            fragile=bool(d.get("fragile", False)),
            stackable=bool(d.get("stackable", True)),
        ).normalized()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Ajout métriques utiles
        d["volume_m3"] = self.volume_m3
        d["footprint_m2"] = self.footprint_cm2 / 10_000.0
        return d


@dataclass
class TruckSpecs:
    """
    Camion en cm/kg.
    """
    length: float
    width: float
    height: float
    max_weight: float
    id: str = ""
    name: str = ""
    # coûts indicatifs (FCFA) optionnels pour cotation
    base_cost_fcfa: float = 0.0
    cost_per_km_fcfa: float = 0.0

    @property
    def volume_cm3(self) -> float:
        return float(self.length) * float(self.width) * float(self.height)

    @property
    def volume_m3(self) -> float:
        return self.volume_cm3 / 1_000_000.0

    @property
    def floor_area_m2(self) -> float:
        return (float(self.length) * float(self.width)) / 10_000.0

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "TruckSpecs":
        return TruckSpecs(
            length=_normalize_cm(d.get("length", 0), is_truck=True),
            width=_normalize_cm(d.get("width", 0), is_truck=True),
            height=_normalize_cm(d.get("height", 0), is_truck=True),
            max_weight=float(d.get("max_weight", d.get("max_payload", 0)) or 0),
            id=str(d.get("id", "") or ""),
            name=str(d.get("name", "") or d.get("type", "") or ""),
            base_cost_fcfa=float(d.get("base_cost_fcfa", d.get("base_cost", 0)) or 0),
            cost_per_km_fcfa=float(d.get("cost_per_km_fcfa", d.get("cost_per_km", 0)) or 0),
        )


@dataclass
class Placement:
    """
    Placement unitaire dans un camion (cm).
    """
    item_id: str
    x: float
    y: float
    z: float
    length: float
    width: float
    height: float
    weight: float
    reference: str = ""
    stackable: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Placement":
        return Placement(
            item_id=str(d.get("item_id", "")),
            x=float(d.get("x", 0)),
            y=float(d.get("y", 0)),
            z=float(d.get("z", 0)),
            length=float(d.get("length", 0)),
            width=float(d.get("width", 0)),
            height=float(d.get("height", 0)),
            weight=float(d.get("weight", 0)),
            reference=str(d.get("reference", "")),
            stackable=bool(d.get("stackable", True)),
        )


@dataclass
class Statistics:
    total_items: int
    total_weight: float
    total_volume_m3: float
    total_floor_area_m2: float
    max_length_cm: float
    max_width_cm: float
    max_height_cm: float
    max_weight_item: float
    non_stackable_items: int
    oversized_items: int


def calculate_statistics(items: List[Item]) -> Statistics:
    units: List[Item] = []
    for it in items:
        itn = it.normalized()
        for _ in range(max(1, int(itn.quantity))):
            units.append(Item(
                length=itn.length, width=itn.width, height=itn.height,
                weight=itn.weight, quantity=1,
                id=itn.id, reference=itn.reference, description=itn.description,
                fragile=itn.fragile, stackable=itn.stackable
            ))

    if not units:
        return Statistics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    total_weight = sum(u.weight for u in units)
    total_volume = sum(u.volume_m3 for u in units)
    total_floor = sum((u.footprint_cm2 / 10_000.0) for u in units if not u.stackable) \
                  + sum((u.footprint_cm2 / 10_000.0) for u in units if u.stackable) * 0.35

    maxL = max(u.length for u in units)
    maxW = max(u.width for u in units)
    maxH = max(u.height for u in units)
    maxWt = max(u.weight for u in units)

    non_stack = sum(1 for u in units if not u.stackable)
    oversized = sum(1 for u in units if (u.length > 1200 or u.width > 248 or u.height > 260))

    return Statistics(
        total_items=len(units),
        total_weight=total_weight,
        total_volume_m3=total_volume,
        total_floor_area_m2=total_floor,
        max_length_cm=maxL,
        max_width_cm=maxW,
        max_height_cm=maxH,
        max_weight_item=maxWt,
        non_stackable_items=non_stack,
        oversized_items=oversized,
    )


@dataclass
class AlgorithmConfig:
    # sélection algo
    algorithm: str = "genetic"  # "simple" ou "genetic"
    # GA
    population_size: int = 30
    generations: int = 50
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8
    elitism_rate: float = 0.1
    timeout_seconds: int = 300

    # terrain / placement
    grid_step_cm: int = 5
    allow_rotation: bool = True
    min_support_ratio: float = 0.7
    clearance_cm: float = 0.0
    max_height_ratio: float = 1.0  # 1.0 = hauteur camion complète

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AlgorithmConfig":
        data = data or {}
        return AlgorithmConfig(
            algorithm=str(data.get("algorithm", data.get("algo", "genetic"))),
            population_size=int(data.get("population_size", 30)),
            generations=int(data.get("generations", 50)),
            mutation_rate=float(data.get("mutation_rate", 0.1)),
            crossover_rate=float(data.get("crossover_rate", 0.8)),
            elitism_rate=float(data.get("elitism_rate", 0.1)),
            timeout_seconds=int(data.get("timeout_seconds", 300)),
            grid_step_cm=int(data.get("grid_step_cm", 5)),
            allow_rotation=bool(data.get("allow_rotation", True)),
            min_support_ratio=float(data.get("min_support_ratio", 0.7)),
            clearance_cm=float(data.get("clearance_cm", 0.0)),
            max_height_ratio=float(data.get("max_height_ratio", 1.0)),
        )
