"""
Service d'optimisation de chargement avec algorithmes génétiques
"""
import random
import time
import copy
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from dataclasses import dataclass
import logging
from src.models.item import Item, TruckSpecs, Placement, OptimizationResult, AlgorithmConfig

logger = logging.getLogger(__name__)

@dataclass
class Individual:
    """Individu dans l'algorithme génétique"""
    placements: List[Placement]
    fitness: float = 0.0
    valid: bool = True

class LoadingOptimizer:
    """Optimiseur de chargement de camions plateaux"""
    
    def __init__(self):
        self.items = []
        self.truck_specs = None
        self.config = AlgorithmConfig()
    
    def optimize(self, items: List[Item], truck_specs: TruckSpecs, 
                config: AlgorithmConfig) -> OptimizationResult:
        """
        Lance l'optimisation du chargement
        
        Args:
            items: Liste des articles à charger
            truck_specs: Spécifications du camion
            config: Configuration de l'algorithme
            
        Returns:
            Résultat de l'optimisation
        """
        self.items = items
        self.truck_specs = truck_specs
        self.config = config
        
        start_time = time.time()
        
        try:
            if config.algorithm == "simple":
                result = self._optimize_simple()
            elif config.algorithm == "genetic":
                result = self._optimize_genetic()
            else:
                raise ValueError(f"Algorithme inconnu: {config.algorithm}")
            
            result.computation_time = time.time() - start_time
            result.algorithm_used = config.algorithm
            result.truck_specs = truck_specs
            
            logger.info(f"Optimisation terminée en {result.computation_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation: {str(e)}")
            return OptimizationResult(
                success=False,
                items_placed=0,
                items_total=sum(item.quantity for item in items),
                weight_efficiency=0.0,
                volume_efficiency=0.0,
                error_message=str(e),
                computation_time=time.time() - start_time,
                algorithm_used=config.algorithm
            )
    
    def _optimize_simple(self) -> OptimizationResult:
        """Algorithme simple First Fit Decreasing"""
        # Expansion des articles selon leur quantité
        expanded_items = []
        for item in self.items:
            for i in range(item.quantity):
                expanded_items.append((item, i))
        
        # Tri par volume décroissant
        expanded_items.sort(key=lambda x: x[0].volume, reverse=True)
        
        placements = []
        placed_weight = 0.0
        placed_volume = 0.0
        
        # Placement séquentiel
        for item, instance in expanded_items:
            position = self._find_first_fit_position(item, placements)
            if position and placed_weight + item.weight <= self.truck_specs.max_weight:
                placement = Placement(
                    item_id=f"{item.reference}_{instance}",
                    x=position[0],
                    y=position[1],
                    z=position[2],
                    length=item.length,
                    width=item.width,
                    height=item.height
                )
                placements.append(placement)
                placed_weight += item.weight
                placed_volume += item.volume
        
        # Calcul des métriques
        total_items = sum(item.quantity for item in self.items)
        weight_efficiency = (placed_weight / self.truck_specs.max_weight) * 100
        volume_efficiency = (placed_volume / self.truck_specs.volume) * 100
        
        return OptimizationResult(
            success=True,
            items_placed=len(placements),
            items_total=total_items,
            weight_efficiency=weight_efficiency,
            volume_efficiency=volume_efficiency,
            placements=placements
        )
    
    def _find_first_fit_position(self, item: Item, existing_placements: List[Placement]) -> Optional[Tuple[float, float, float]]:
        """Trouve la première position disponible pour un article"""
        # Grille de positions possibles
        step = 10  # Précision de 10cm
        
        for z in range(0, int(self.truck_specs.height - item.height) + 1, step):
            for y in range(0, int(self.truck_specs.width - item.width) + 1, step):
                for x in range(0, int(self.truck_specs.length - item.length) + 1, step):
                    position = (float(x), float(y), float(z))
                    
                    # Vérification des collisions
                    if not self._check_collision(item, position, existing_placements):
                        # Vérification du support (sauf au sol)
                        if z == 0 or self._check_support(item, position, existing_placements):
                            return position
        
        return None
    
    def _check_collision(self, item: Item, position: Tuple[float, float, float], 
                        existing_placements: List[Placement]) -> bool:
        """Vérifie s'il y a collision avec les articles existants"""
        x, y, z = position
        
        for placement in existing_placements:
            # Vérification de chevauchement 3D
            if (x < placement.x + placement.length and x + item.length > placement.x and
                y < placement.y + placement.width and y + item.width > placement.y and
                z < placement.z + placement.height and z + item.height > placement.z):
                return True
        
        return False
    
    def _check_support(self, item: Item, position: Tuple[float, float, float],
                      existing_placements: List[Placement]) -> bool:
        """Vérifie si l'article a un support suffisant"""
        x, y, z = position
        support_area = 0.0
        item_base_area = item.length * item.width
        
        for placement in existing_placements:
            # L'article doit être juste au-dessus
            if abs(placement.z + placement.height - z) < 1.0:  # Tolérance 1cm
                # Calcul de l'intersection des bases
                overlap_x = max(0, min(x + item.length, placement.x + placement.length) - max(x, placement.x))
                overlap_y = max(0, min(y + item.width, placement.y + placement.width) - max(y, placement.y))
                support_area += overlap_x * overlap_y
        
        # Au moins 50% de support requis
        return support_area >= item_base_area * 0.5
    
    def _optimize_genetic(self) -> OptimizationResult:
        """Algorithme génétique d'optimisation"""
        # Expansion des articles
        expanded_items = []
        for item in self.items:
            for i in range(item.quantity):
                expanded_items.append((item, f"{item.reference}_{i}"))
        
        # Initialisation de la population
        population = self._initialize_population(expanded_items)
        
        best_individual = None
        best_fitness = -float('inf')
        generations_without_improvement = 0
        
        for generation in range(self.config.generations):
            # Évaluation de la population
            for individual in population:
                individual.fitness = self._evaluate_fitness(individual)
                if individual.fitness > best_fitness:
                    best_fitness = individual.fitness
                    best_individual = copy.deepcopy(individual)
                    generations_without_improvement = 0
                else:
                    generations_without_improvement += 1
            
            # Arrêt précoce si pas d'amélioration
            if generations_without_improvement > 20:
                logger.info(f"Arrêt précoce à la génération {generation}")
                break
            
            # Tri par fitness
            population.sort(key=lambda x: x.fitness, reverse=True)
            
            # Nouvelle génération
            new_population = []
            
            # Élitisme
            elite_size = int(len(population) * self.config.elitism_rate)
            new_population.extend(population[:elite_size])
            
            # Croisement et mutation
            while len(new_population) < self.config.population_size:
                parent1 = self._tournament_selection(population)
                parent2 = self._tournament_selection(population)
                
                if random.random() < self.config.crossover_rate:
                    child = self._crossover(parent1, parent2, expanded_items)
                else:
                    child = copy.deepcopy(parent1)
                
                if random.random() < self.config.mutation_rate:
                    child = self._mutate(child, expanded_items)
                
                new_population.append(child)
            
            population = new_population
            
            if generation % 10 == 0:
                logger.info(f"Génération {generation}: Meilleur fitness = {best_fitness:.4f}")
        
        # Construction du résultat
        if best_individual:
            total_items = sum(item.quantity for item in self.items)
            placed_weight = sum(self._get_item_weight(p.item_id, expanded_items) for p in best_individual.placements)
            placed_volume = sum(p.length * p.width * p.height for p in best_individual.placements)
            
            weight_efficiency = (placed_weight / self.truck_specs.max_weight) * 100
            volume_efficiency = (placed_volume / self.truck_specs.volume) * 100
            
            return OptimizationResult(
                success=True,
                items_placed=len(best_individual.placements),
                items_total=total_items,
                weight_efficiency=weight_efficiency,
                volume_efficiency=volume_efficiency,
                fitness=best_fitness,
                placements=best_individual.placements
            )
        else:
            return OptimizationResult(
                success=False,
                items_placed=0,
                items_total=sum(item.quantity for item in self.items),
                weight_efficiency=0.0,
                volume_efficiency=0.0,
                error_message="Aucune solution trouvée"
            )
    
    def _initialize_population(self, expanded_items: List[Tuple[Item, str]]) -> List[Individual]:
        """Initialise la population avec des solutions aléatoires"""
        population = []
        
        for _ in range(self.config.population_size):
            # Mélange aléatoire des articles
            shuffled_items = expanded_items.copy()
            random.shuffle(shuffled_items)
            
            placements = []
            placed_weight = 0.0
            
            for item, item_id in shuffled_items:
                if placed_weight + item.weight > self.truck_specs.max_weight:
                    continue
                
                position = self._find_random_position(item, placements)
                if position:
                    placement = Placement(
                        item_id=item_id,
                        x=position[0],
                        y=position[1],
                        z=position[2],
                        length=item.length,
                        width=item.width,
                        height=item.height
                    )
                    placements.append(placement)
                    placed_weight += item.weight
            
            individual = Individual(placements=placements)
            population.append(individual)
        
        return population
    
    def _find_random_position(self, item: Item, existing_placements: List[Placement]) -> Optional[Tuple[float, float, float]]:
        """Trouve une position aléatoire valide pour un article"""
        max_attempts = 50
        
        for _ in range(max_attempts):
            x = random.uniform(0, max(0, self.truck_specs.length - item.length))
            y = random.uniform(0, max(0, self.truck_specs.width - item.width))
            z = random.uniform(0, max(0, self.truck_specs.height - item.height))
            
            position = (x, y, z)
            
            if not self._check_collision(item, position, existing_placements):
                if z < 10 or self._check_support(item, position, existing_placements):
                    return position
        
        return None
    
    def _evaluate_fitness(self, individual: Individual) -> float:
        """Évalue la fitness d'un individu"""
        if not individual.placements:
            return 0.0
        
        # Métriques de base
        placed_weight = sum(self._get_placement_weight(p) for p in individual.placements)
        placed_volume = sum(p.length * p.width * p.height for p in individual.placements)
        
        weight_ratio = placed_weight / self.truck_specs.max_weight
        volume_ratio = placed_volume / self.truck_specs.volume
        
        # Fitness multi-objectifs
        fitness = (
            len(individual.placements) * 0.4 +  # Nombre d'articles placés
            volume_ratio * 100 * 0.3 +          # Efficacité volumétrique
            weight_ratio * 100 * 0.3            # Efficacité pondérale
        )
        
        # Pénalités
        fitness -= self._calculate_penalties(individual)
        
        return fitness
    
    def _calculate_penalties(self, individual: Individual) -> float:
        """Calcule les pénalités pour les contraintes violées"""
        penalty = 0.0
        
        # Pénalité pour centre de gravité trop haut
        if individual.placements:
            avg_height = sum(p.z + p.height/2 for p in individual.placements) / len(individual.placements)
            if avg_height > self.truck_specs.height * 0.6:
                penalty += 10.0
        
        # Pénalité pour instabilité (articles lourds en hauteur)
        for placement in individual.placements:
            weight = self._get_placement_weight(placement)
            if placement.z > 100 and weight > 50:  # Articles lourds (>50kg) en hauteur (>1m)
                penalty += weight * 0.1
        
        return penalty
    
    def _get_placement_weight(self, placement: Placement) -> float:
        """Récupère le poids d'un placement"""
        # Extraction de la référence depuis l'ID
        ref = placement.item_id.split('_')[0]
        for item in self.items:
            if item.reference == ref:
                return item.weight
        return 0.0
    
    def _get_item_weight(self, item_id: str, expanded_items: List[Tuple[Item, str]]) -> float:
        """Récupère le poids d'un article par son ID"""
        for item, id_str in expanded_items:
            if id_str == item_id:
                return item.weight
        return 0.0
    
    def _tournament_selection(self, population: List[Individual], tournament_size: int = 3) -> Individual:
        """Sélection par tournoi"""
        tournament = random.sample(population, min(tournament_size, len(population)))
        return max(tournament, key=lambda x: x.fitness)
    
    def _crossover(self, parent1: Individual, parent2: Individual, 
                  expanded_items: List[Tuple[Item, str]]) -> Individual:
        """Croisement entre deux parents"""
        # Croisement simple : prendre une partie de chaque parent
        crossover_point = len(parent1.placements) // 2
        
        child_placements = parent1.placements[:crossover_point]
        
        # Ajouter des placements du parent2 qui ne créent pas de collision
        for placement in parent2.placements:
            item = self._find_item_by_id(placement.item_id, expanded_items)
            if item and not self._check_collision(item, (placement.x, placement.y, placement.z), child_placements):
                child_placements.append(placement)
        
        return Individual(placements=child_placements)
    
    def _mutate(self, individual: Individual, expanded_items: List[Tuple[Item, str]]) -> Individual:
        """Mutation d'un individu"""
        if not individual.placements:
            return individual
        
        # Mutation : déplacer un article aléatoirement
        if random.random() < 0.5 and individual.placements:
            placement_idx = random.randint(0, len(individual.placements) - 1)
            placement = individual.placements[placement_idx]
            
            item = self._find_item_by_id(placement.item_id, expanded_items)
            if item:
                # Supprimer temporairement le placement
                temp_placements = individual.placements[:placement_idx] + individual.placements[placement_idx+1:]
                
                # Trouver une nouvelle position
                new_position = self._find_random_position(item, temp_placements)
                if new_position:
                    placement.x, placement.y, placement.z = new_position
        
        return individual
    
    def _find_item_by_id(self, item_id: str, expanded_items: List[Tuple[Item, str]]) -> Optional[Item]:
        """Trouve un article par son ID"""
        for item, id_str in expanded_items:
            if id_str == item_id:
                return item
        return None

