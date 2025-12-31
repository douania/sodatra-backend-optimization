"""
Service d'extraction de données depuis les packing lists Excel
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import re
from pathlib import Path
import logging
from src.models.item import Item, Statistics, calculate_statistics

logger = logging.getLogger(__name__)

class ExcelExtractor:
    """Extracteur intelligent de packing lists Excel"""
    
    # Patterns de reconnaissance des colonnes
    COLUMN_PATTERNS = {
        'reference': [
            r'ref(?:erence)?', r'code', r'sku', r'item', r'part', r'numero',
            r'id', r'identifiant', r'article'
        ],
        'description': [
            r'desc(?:ription)?', r'libelle', r'designation', r'nom', r'name',
            r'produit', r'product', r'titre', r'title'
        ],
        'length': [
            r'long(?:ueur)?', r'length', r'l\b', r'lg', r'longueur'
        ],
        'width': [
            r'larg(?:eur)?', r'width', r'w\b', r'largeur', r'l(?:arg)?'
        ],
        'height': [
            r'haut(?:eur)?', r'height', r'h\b', r'ht', r'hauteur'
        ],
        'weight': [
            r'poids', r'weight', r'masse', r'mass', r'kg', r'pds'
        ],
        'quantity': [
            r'qte?', r'quantity', r'quantite', r'qty', r'nb', r'nombre',
            r'count', r'pieces?', r'units?'
        ]
    }
    
    # Unités de mesure reconnues
    DIMENSION_UNITS = {
        'mm': 0.1,    # conversion vers cm
        'cm': 1.0,
        'm': 100.0,
        'millimetre': 0.1,
        'centimetre': 1.0,
        'metre': 100.0
    }
    
    WEIGHT_UNITS = {
        'g': 0.001,   # conversion vers kg
        'kg': 1.0,
        't': 1000.0,
        'gramme': 0.001,
        'kilogramme': 1.0,
        'tonne': 1000.0
    }
    
    def __init__(self):
        self.detected_columns = {}
        self.detected_units = {}
    
    def extract_from_file(self, file_path: str) -> Tuple[List[Item], Statistics]:
        """
        Extrait les articles depuis un fichier Excel
        
        Args:
            file_path: Chemin vers le fichier Excel
            
        Returns:
            Tuple contenant la liste des articles et les statistiques
        """
        try:
            # Lecture du fichier Excel
            df = self._read_excel_file(file_path)
            
            # Détection automatique des colonnes
            column_mapping = self._detect_columns(df)
            
            # Extraction et nettoyage des données
            items = self._extract_items(df, column_mapping)
            
            # Calcul des statistiques
            stats = calculate_statistics(items)
            
            logger.info(f"Extraction réussie: {len(items)} articles extraits")
            return items, stats
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction: {str(e)}")
            raise
    
    def _read_excel_file(self, file_path: str) -> pd.DataFrame:
        """Lit le fichier Excel et trouve la feuille avec les données"""
        try:
            # Essai de lecture de la première feuille
            df = pd.read_excel(file_path, sheet_name=0)
            
            # Si la première feuille semble vide, essayer les autres
            if df.empty or len(df.columns) < 3:
                excel_file = pd.ExcelFile(file_path)
                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    if not df.empty and len(df.columns) >= 3:
                        break
            
            # Nettoyage initial
            df = self._clean_dataframe(df)
            
            return df
            
        except Exception as e:
            raise ValueError(f"Impossible de lire le fichier Excel: {str(e)}")
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Nettoie le DataFrame initial"""
        # Suppression des lignes complètement vides
        df = df.dropna(how='all')
        
        # Suppression des colonnes complètement vides
        df = df.dropna(axis=1, how='all')
        
        # Recherche de la ligne d'en-têtes
        header_row = self._find_header_row(df)
        if header_row > 0:
            df = df.iloc[header_row:].reset_index(drop=True)
            df.columns = df.iloc[0]
            df = df.iloc[1:].reset_index(drop=True)
        
        # Nettoyage des noms de colonnes
        df.columns = [str(col).strip().lower() if pd.notna(col) else f'col_{i}' 
                     for i, col in enumerate(df.columns)]
        
        return df
    
    def _find_header_row(self, df: pd.DataFrame) -> int:
        """Trouve la ligne contenant les en-têtes"""
        for i, row in df.iterrows():
            # Compte le nombre de cellules non vides dans la ligne
            non_empty = row.count()
            if non_empty >= 3:  # Au moins 3 colonnes remplies
                # Vérifie si la ligne contient des mots-clés d'en-têtes
                text_values = [str(val).lower() for val in row if pd.notna(val)]
                header_keywords = ['ref', 'desc', 'long', 'larg', 'haut', 'poids', 'qte']
                if any(keyword in ' '.join(text_values) for keyword in header_keywords):
                    return i
        return 0
    
    def _detect_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """Détecte automatiquement les colonnes pertinentes"""
        column_mapping = {}
        
        for field, patterns in self.COLUMN_PATTERNS.items():
            best_match = None
            best_score = 0
            
            for col in df.columns:
                col_str = str(col).lower()
                for pattern in patterns:
                    if re.search(pattern, col_str):
                        # Score basé sur la longueur du match
                        score = len(re.search(pattern, col_str).group())
                        if score > best_score:
                            best_score = score
                            best_match = col
            
            if best_match:
                column_mapping[field] = best_match
                logger.info(f"Colonne détectée: {field} -> {best_match}")
        
        # Vérification des colonnes essentielles
        required_fields = ['reference', 'length', 'width', 'height', 'weight']
        missing_fields = [field for field in required_fields if field not in column_mapping]
        
        if missing_fields:
            raise ValueError(f"Colonnes manquantes: {', '.join(missing_fields)}")
        
        self.detected_columns = column_mapping
        return column_mapping
    
    def _extract_items(self, df: pd.DataFrame, column_mapping: Dict[str, str]) -> List[Item]:
        """Extrait les articles depuis le DataFrame"""
        items = []
        
        for index, row in df.iterrows():
            try:
                # Extraction des valeurs de base
                reference = str(row.get(column_mapping.get('reference', ''), '')).strip()
                if not reference or reference.lower() in ['nan', 'none', '']:
                    continue
                
                description = str(row.get(column_mapping.get('description', ''), reference)).strip()
                
                # Extraction et conversion des dimensions
                length = self._extract_numeric_value(row, column_mapping.get('length'))
                width = self._extract_numeric_value(row, column_mapping.get('width'))
                height = self._extract_numeric_value(row, column_mapping.get('height'))
                weight = self._extract_numeric_value(row, column_mapping.get('weight'))
                
                # Quantité (défaut: 1)
                quantity = self._extract_numeric_value(row, column_mapping.get('quantity'), default=1)
                quantity = max(1, int(quantity))
                
                # Détection des propriétés spéciales
                fragile = self._detect_fragile(description)
                stackable = self._detect_stackable(description)
                
                # Validation des valeurs
                if any(val <= 0 for val in [length, width, height, weight]):
                    logger.warning(f"Valeurs invalides pour {reference}, ignoré")
                    continue
                
                # Conversion des unités si nécessaire
                length = self._convert_dimension(length, column_mapping.get('length'))
                width = self._convert_dimension(width, column_mapping.get('width'))
                height = self._convert_dimension(height, column_mapping.get('height'))
                weight = self._convert_weight(weight, column_mapping.get('weight'))
                
                item = Item(
                    length=length,
                    width=width,
                    height=height,
                    weight=weight,
                    quantity=quantity,
                    id=reference,
                    reference=reference,
                    description=description,
                    fragile=fragile,
                    stackable=stackable
                )
                
                items.append(item)
                
            except Exception as e:
                logger.warning(f"Erreur ligne {index}: {str(e)}")
                continue
        
        if not items:
            raise ValueError("Aucun article valide trouvé dans le fichier")
        
        return items
    
    def _extract_numeric_value(self, row: pd.Series, column: Optional[str], default: float = 0.0) -> float:
        """Extrait une valeur numérique d'une cellule"""
        if not column or column not in row:
            return default
        
        value = row[column]
        
        if pd.isna(value):
            return default
        
        # Si c'est déjà un nombre
        if isinstance(value, (int, float)):
            return float(value)
        
        # Extraction depuis une chaîne
        value_str = str(value).strip()
        
        # Recherche de nombres dans la chaîne
        numbers = re.findall(r'\d+(?:[.,]\d+)?', value_str)
        if numbers:
            # Prendre le premier nombre trouvé
            number_str = numbers[0].replace(',', '.')
            return float(number_str)
        
        return default
    
    def _detect_fragile(self, description: str) -> bool:
        """Détecte si un article est fragile"""
        fragile_keywords = [
            'fragile', 'verre', 'glass', 'ceramic', 'ceramique',
            'breakable', 'delicate', 'sensible'
        ]
        desc_lower = description.lower()
        return any(keyword in desc_lower for keyword in fragile_keywords)
    
    def _detect_stackable(self, description: str) -> bool:
        """Détecte si un article est empilable"""
        non_stackable_keywords = [
            'fragile', 'liquide', 'liquid', 'cylindrique', 'rond',
            'sphere', 'ball', 'unstackable'
        ]
        desc_lower = description.lower()
        return not any(keyword in desc_lower for keyword in non_stackable_keywords)
    
    def _convert_dimension(self, value: float, column_name: Optional[str]) -> float:
        """Convertit une dimension vers les centimètres"""
        if not column_name:
            return value
        
        # Recherche d'unité dans le nom de colonne
        col_lower = column_name.lower()
        for unit, factor in self.DIMENSION_UNITS.items():
            if unit in col_lower:
                return value * factor
        
        # Par défaut, assume que c'est en cm
        return value
    
    def _convert_weight(self, value: float, column_name: Optional[str]) -> float:
        """Convertit un poids vers les kilogrammes"""
        if not column_name:
            return value
        
        # Recherche d'unité dans le nom de colonne
        col_lower = column_name.lower()
        for unit, factor in self.WEIGHT_UNITS.items():
            if unit in col_lower:
                return value * factor
        
        # Par défaut, assume que c'est en kg
        return value
    
    def get_extraction_report(self) -> Dict[str, Any]:
        """Retourne un rapport sur l'extraction effectuée"""
        return {
            'detected_columns': self.detected_columns,
            'detected_units': self.detected_units
        }

