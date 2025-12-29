"""
Service de génération de visualisations 3D des plans de chargement
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import io
import base64
from typing import List, Dict, Any, Optional
import logging
from src.models.item import Placement, TruckSpecs

logger = logging.getLogger(__name__)

class LoadingVisualizer:
    """Générateur de visualisations 3D pour les plans de chargement"""
    
    def __init__(self):
        # Configuration des couleurs pour différents types d'articles
        self.colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
            '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9'
        ]
        self.color_index = 0
    
    def generate_3d_visualization(self, placements: List[Placement], 
                                truck_specs: TruckSpecs) -> str:
        """
        Génère une visualisation 3D du plan de chargement
        
        Args:
            placements: Liste des placements d'articles
            truck_specs: Spécifications du camion
            
        Returns:
            Image encodée en base64
        """
        try:
            # Configuration de la figure
            fig = plt.figure(figsize=(12, 8))
            ax = fig.add_subplot(111, projection='3d')
            
            # Dessin du camion (contour)
            self._draw_truck_outline(ax, truck_specs)
            
            # Dessin des articles
            self._draw_placements(ax, placements)
            
            # Configuration des axes
            self._configure_axes(ax, truck_specs)
            
            # Titre et légende
            ax.set_title('Plan de Chargement 3D', fontsize=14, fontweight='bold')
            
            # Conversion en image base64
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            plt.close(fig)
            
            logger.info("Visualisation 3D générée avec succès")
            return f"data:image/png;base64,{img_base64}"
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de visualisation: {str(e)}")
            raise
    
    def generate_2d_views(self, placements: List[Placement], 
                         truck_specs: TruckSpecs) -> Dict[str, str]:
        """
        Génère des vues 2D (dessus, côté, face)
        
        Args:
            placements: Liste des placements
            truck_specs: Spécifications du camion
            
        Returns:
            Dictionnaire avec les vues encodées en base64
        """
        views = {}
        
        try:
            # Vue de dessus (X-Y)
            views['top'] = self._generate_top_view(placements, truck_specs)
            
            # Vue de côté (X-Z)
            views['side'] = self._generate_side_view(placements, truck_specs)
            
            # Vue de face (Y-Z)
            views['front'] = self._generate_front_view(placements, truck_specs)
            
            logger.info("Vues 2D générées avec succès")
            return views
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération des vues 2D: {str(e)}")
            raise
    
    def _draw_truck_outline(self, ax, truck_specs: TruckSpecs):
        """Dessine le contour du camion"""
        # Coordonnées du camion
        x_max, y_max, z_max = truck_specs.length, truck_specs.width, truck_specs.height
        
        # Lignes du contour
        lines = [
            # Base
            [(0, 0, 0), (x_max, 0, 0)],
            [(x_max, 0, 0), (x_max, y_max, 0)],
            [(x_max, y_max, 0), (0, y_max, 0)],
            [(0, y_max, 0), (0, 0, 0)],
            
            # Hauteur
            [(0, 0, 0), (0, 0, z_max)],
            [(x_max, 0, 0), (x_max, 0, z_max)],
            [(x_max, y_max, 0), (x_max, y_max, z_max)],
            [(0, y_max, 0), (0, y_max, z_max)],
            
            # Toit
            [(0, 0, z_max), (x_max, 0, z_max)],
            [(x_max, 0, z_max), (x_max, y_max, z_max)],
            [(x_max, y_max, z_max), (0, y_max, z_max)],
            [(0, y_max, z_max), (0, 0, z_max)]
        ]
        
        for line in lines:
            xs, ys, zs = zip(*line)
            ax.plot(xs, ys, zs, 'k--', alpha=0.3, linewidth=1)
    
    def _draw_placements(self, ax, placements: List[Placement]):
        """Dessine les articles placés"""
        color_map = {}
        
        for placement in placements:
            # Attribution d'une couleur par référence d'article
            ref = placement.item_id.split('_')[0]
            if ref not in color_map:
                color_map[ref] = self.colors[self.color_index % len(self.colors)]
                self.color_index += 1
            
            color = color_map[ref]
            
            # Création du parallélépipède
            self._draw_box(ax, placement, color)
    
    def _draw_box(self, ax, placement: Placement, color: str):
        """Dessine un parallélépipède représentant un article"""
        x, y, z = placement.x, placement.y, placement.z
        dx, dy, dz = placement.length, placement.width, placement.height
        
        # Définition des 8 sommets du parallélépipède
        vertices = [
            [x, y, z],
            [x + dx, y, z],
            [x + dx, y + dy, z],
            [x, y + dy, z],
            [x, y, z + dz],
            [x + dx, y, z + dz],
            [x + dx, y + dy, z + dz],
            [x, y + dy, z + dz]
        ]
        
        # Définition des 6 faces
        faces = [
            [vertices[0], vertices[1], vertices[2], vertices[3]],  # Base
            [vertices[4], vertices[5], vertices[6], vertices[7]],  # Toit
            [vertices[0], vertices[1], vertices[5], vertices[4]],  # Face avant
            [vertices[2], vertices[3], vertices[7], vertices[6]],  # Face arrière
            [vertices[1], vertices[2], vertices[6], vertices[5]],  # Face droite
            [vertices[4], vertices[7], vertices[3], vertices[0]]   # Face gauche
        ]
        
        # Ajout des faces à la visualisation
        face_collection = Poly3DCollection(faces, alpha=0.7, facecolor=color, edgecolor='black', linewidth=0.5)
        ax.add_collection3d(face_collection)
        
        # Ajout du label (référence de l'article)
        center_x = x + dx / 2
        center_y = y + dy / 2
        center_z = z + dz / 2
        
        ref = placement.item_id.split('_')[0]
        ax.text(center_x, center_y, center_z, ref, fontsize=8, ha='center', va='center')
    
    def _configure_axes(self, ax, truck_specs: TruckSpecs):
        """Configure les axes de la visualisation"""
        ax.set_xlim(0, truck_specs.length)
        ax.set_ylim(0, truck_specs.width)
        ax.set_zlim(0, truck_specs.height)
        
        ax.set_xlabel('Longueur (cm)', fontsize=10)
        ax.set_ylabel('Largeur (cm)', fontsize=10)
        ax.set_zlabel('Hauteur (cm)', fontsize=10)
        
        # Égalisation des proportions
        max_range = max(truck_specs.length, truck_specs.width, truck_specs.height)
        ax.set_box_aspect([truck_specs.length/max_range, 
                          truck_specs.width/max_range, 
                          truck_specs.height/max_range])
    
    def _generate_top_view(self, placements: List[Placement], truck_specs: TruckSpecs) -> str:
        """Génère la vue de dessus (plan X-Y)"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Contour du camion
        truck_rect = patches.Rectangle((0, 0), truck_specs.length, truck_specs.width,
                                     linewidth=2, edgecolor='black', facecolor='none')
        ax.add_patch(truck_rect)
        
        # Articles
        color_map = {}
        for placement in placements:
            ref = placement.item_id.split('_')[0]
            if ref not in color_map:
                color_map[ref] = self.colors[self.color_index % len(self.colors)]
                self.color_index += 1
            
            rect = patches.Rectangle((placement.x, placement.y), 
                                   placement.length, placement.width,
                                   facecolor=color_map[ref], alpha=0.7, edgecolor='black')
            ax.add_patch(rect)
            
            # Label
            ax.text(placement.x + placement.length/2, placement.y + placement.width/2,
                   ref, ha='center', va='center', fontsize=8)
        
        ax.set_xlim(0, truck_specs.length)
        ax.set_ylim(0, truck_specs.width)
        ax.set_xlabel('Longueur (cm)')
        ax.set_ylabel('Largeur (cm)')
        ax.set_title('Vue de Dessus')
        ax.set_aspect('equal')
        
        # Conversion en base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close(fig)
        
        return f"data:image/png;base64,{img_base64}"
    
    def _generate_side_view(self, placements: List[Placement], truck_specs: TruckSpecs) -> str:
        """Génère la vue de côté (plan X-Z)"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Contour du camion
        truck_rect = patches.Rectangle((0, 0), truck_specs.length, truck_specs.height,
                                     linewidth=2, edgecolor='black', facecolor='none')
        ax.add_patch(truck_rect)
        
        # Articles
        color_map = {}
        for placement in placements:
            ref = placement.item_id.split('_')[0]
            if ref not in color_map:
                color_map[ref] = self.colors[self.color_index % len(self.colors)]
                self.color_index += 1
            
            rect = patches.Rectangle((placement.x, placement.z), 
                                   placement.length, placement.height,
                                   facecolor=color_map[ref], alpha=0.7, edgecolor='black')
            ax.add_patch(rect)
            
            # Label
            ax.text(placement.x + placement.length/2, placement.z + placement.height/2,
                   ref, ha='center', va='center', fontsize=8)
        
        ax.set_xlim(0, truck_specs.length)
        ax.set_ylim(0, truck_specs.height)
        ax.set_xlabel('Longueur (cm)')
        ax.set_ylabel('Hauteur (cm)')
        ax.set_title('Vue de Côté')
        ax.set_aspect('equal')
        
        # Conversion en base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close(fig)
        
        return f"data:image/png;base64,{img_base64}"
    
    def _generate_front_view(self, placements: List[Placement], truck_specs: TruckSpecs) -> str:
        """Génère la vue de face (plan Y-Z)"""
        fig, ax = plt.subplots(figsize=(8, 6))
        
        # Contour du camion
        truck_rect = patches.Rectangle((0, 0), truck_specs.width, truck_specs.height,
                                     linewidth=2, edgecolor='black', facecolor='none')
        ax.add_patch(truck_rect)
        
        # Articles
        color_map = {}
        for placement in placements:
            ref = placement.item_id.split('_')[0]
            if ref not in color_map:
                color_map[ref] = self.colors[self.color_index % len(self.colors)]
                self.color_index += 1
            
            rect = patches.Rectangle((placement.y, placement.z), 
                                   placement.width, placement.height,
                                   facecolor=color_map[ref], alpha=0.7, edgecolor='black')
            ax.add_patch(rect)
            
            # Label
            ax.text(placement.y + placement.width/2, placement.z + placement.height/2,
                   ref, ha='center', va='center', fontsize=8)
        
        ax.set_xlim(0, truck_specs.width)
        ax.set_ylim(0, truck_specs.height)
        ax.set_xlabel('Largeur (cm)')
        ax.set_ylabel('Hauteur (cm)')
        ax.set_title('Vue de Face')
        ax.set_aspect('equal')
        
        # Conversion en base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close(fig)
        
        return f"data:image/png;base64,{img_base64}"
    
    def generate_loading_sequence(self, placements: List[Placement], 
                                truck_specs: TruckSpecs) -> List[str]:
        """
        Génère une séquence d'images montrant l'ordre de chargement
        
        Args:
            placements: Liste des placements triés par ordre de chargement
            truck_specs: Spécifications du camion
            
        Returns:
            Liste d'images encodées en base64 montrant la progression
        """
        sequence = []
        
        try:
            for i in range(1, len(placements) + 1):
                # Générer une visualisation avec les i premiers articles
                partial_placements = placements[:i]
                img = self.generate_3d_visualization(partial_placements, truck_specs)
                sequence.append(img)
            
            logger.info(f"Séquence de chargement générée: {len(sequence)} étapes")
            return sequence
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de séquence: {str(e)}")
            raise
    
    def generate_statistics_chart(self, optimization_result) -> str:
        """
        Génère un graphique des statistiques d'optimisation
        
        Args:
            optimization_result: Résultat de l'optimisation
            
        Returns:
            Graphique encodé en base64
        """
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
            
            # Efficacité volumétrique
            ax1.pie([optimization_result.volume_efficiency, 
                    100 - optimization_result.volume_efficiency],
                   labels=['Utilisé', 'Libre'], autopct='%1.1f%%',
                   colors=['#4ECDC4', '#E8E8E8'])
            ax1.set_title('Efficacité Volumétrique')
            
            # Efficacité pondérale
            ax2.pie([optimization_result.weight_efficiency, 
                    100 - optimization_result.weight_efficiency],
                   labels=['Utilisé', 'Libre'], autopct='%1.1f%%',
                   colors=['#FF6B6B', '#E8E8E8'])
            ax2.set_title('Efficacité Pondérale')
            
            # Articles placés
            ax3.bar(['Placés', 'Total'], 
                   [optimization_result.items_placed, optimization_result.items_total],
                   color=['#45B7D1', '#96CEB4'])
            ax3.set_title('Articles Placés')
            ax3.set_ylabel('Nombre d\'articles')
            
            # Métriques combinées
            metrics = ['Volume', 'Poids', 'Articles']
            values = [
                optimization_result.volume_efficiency,
                optimization_result.weight_efficiency,
                (optimization_result.items_placed / optimization_result.items_total) * 100
            ]
            
            bars = ax4.bar(metrics, values, color=['#4ECDC4', '#FF6B6B', '#45B7D1'])
            ax4.set_title('Efficacité Globale')
            ax4.set_ylabel('Pourcentage (%)')
            ax4.set_ylim(0, 100)
            
            # Ajout des valeurs sur les barres
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{value:.1f}%', ha='center', va='bottom')
            
            plt.tight_layout()
            
            # Conversion en base64
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            plt.close(fig)
            
            return f"data:image/png;base64,{img_base64}"
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du graphique: {str(e)}")
            raise

