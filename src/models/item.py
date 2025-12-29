"""
Modèles de données pour les articles et optimisations
"""
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
import json

@dataclass
class Item:
    """Représente un article à charger"""
    reference: str
    description: str
    length: float  # cm
    width: float   # cm
    height: float  # cm
    weight: float  # kg
    quantity: int
    fragile: bool = False
    stackable: bool = True
    max_stack_height: Optional[float] = None
    
    @property
    def volume(self) -> float:
        """Volume unitaire en cm³"""
        return self.length * self.width * self.height
    
    @property
    def total_volume(self) -> float:
        """Volume total pour la quantité"""
        return self.volume * self.quantity
    
    @property
    def total_weight(self) -> float:
        """Poids total pour la quantité"""
        return self.weight * self.quantity
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Item':
        """Création depuis un dictionnaire"""
        return cls(**data)

@dataclass
class TruckSpecs:
    """Spécifications du camion plateau"""
    length: float  # cm
    width: float   # cm
    height: float  # cm
    max_weight: float  # kg
    
    @property
    def volume(self) -> float:
        """Volume total du plateau en cm³"""
        return self.length * self.width * self.height
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class Placement:
    """Position d'un article dans le camion"""
    item_id: str
    x: float  # Position X (cm)
    y: float  # Position Y (cm)
    z: float  # Position Z (cm)
    length: float  # Dimension après rotation
    width: float   # Dimension après rotation
    height: float  # Dimension après rotation
    rotation: int = 0  # Rotation en degrés (0, 90, 180, 270)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class OptimizationResult:
    """Résultat d'une optimisation"""
    success: bool
    items_placed: int
    items_total: int
    weight_efficiency: float  # Pourcentage
    volume_efficiency: float  # Pourcentage
    fitness: Optional[float] = None
    placements: List[Placement] = None
    truck_specs: Optional[TruckSpecs] = None
    algorithm_used: str = "unknown"
    computation_time: float = 0.0
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.placements is None:
            self.placements = []
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        # Conversion des placements
        result['placements'] = [p.to_dict() if hasattr(p, 'to_dict') else p for p in self.placements]
        if self.truck_specs:
            result['truck_specs'] = self.truck_specs.to_dict()
        return result

@dataclass
class Statistics:
    """Statistiques sur un ensemble d'articles"""
    total_items: int
    unique_references: int
    total_weight: float  # kg
    total_volume: float  # cm³
    average_weight: float = 0.0
    average_volume: float = 0.0
    
    def __post_init__(self):
        if self.total_items > 0:
            self.average_weight = self.total_weight / self.total_items
            self.average_volume = self.total_volume / self.total_items
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class AlgorithmConfig:
    """Configuration des algorithmes d'optimisation"""
    algorithm: str = "genetic"  # "simple" ou "genetic"
    population_size: int = 30
    generations: int = 50
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8
    elitism_rate: float = 0.1
    timeout_seconds: int = 300  # 5 minutes max
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlgorithmConfig':
        return cls(**data)

def calculate_statistics(items: List[Item]) -> Statistics:
    """Calcule les statistiques d'un ensemble d'articles"""
    if not items:
        return Statistics(0, 0, 0.0, 0.0)
    
    total_items = sum(item.quantity for item in items)
    unique_references = len(set(item.reference for item in items))
    total_weight = sum(item.total_weight for item in items)
    total_volume = sum(item.total_volume for item in items)
    
    return Statistics(
        total_items=total_items,
        unique_references=unique_references,
        total_weight=total_weight,
        total_volume=total_volume
    )

