# src/config/truck_catalog.py
"""
Catalogue des véhicules de transport disponibles en Afrique de l'Ouest.
Basé sur la réglementation UEMOA et les équipements réellement disponibles.

Dimensions en centimètres (cm), poids en kilogrammes (kg).
Coûts en FCFA.

Sources:
- Règlement 14/2005/CM/UEMOA
- Recherche Manus AI - Équipements transport Afrique de l'Ouest
- ChatGPT - Matériel de logistique et manutention
"""

from typing import Dict, Any, List

# =============================================================================
# CAMIONS PORTEURS (véhicules isolés)
# =============================================================================

PORTEURS = {
    "van_3t": {
        "id": "van_3t",
        "name": "Camionnette 3T",
        "category": "porteur",
        "type": "4x2",
        "length": 420,      # 4.2m
        "width": 180,       # 1.8m
        "height": 180,      # 1.8m
        "max_weight": 3000, # 3 tonnes
        "ptac": 6000,       # PTAC 6T
        "nb_essieux": 2,
        "base_cost_fcfa": 45000,
        "cost_per_km_fcfa": 200,
        "usage": "Distribution urbaine, petits colis"
    },
    "porteur_12t": {
        "id": "porteur_12t",
        "name": "Porteur 12T (4x2)",
        "category": "porteur",
        "type": "4x2",
        "length": 700,      # 7m
        "width": 245,       # 2.45m
        "height": 240,      # 2.4m
        "max_weight": 8000, # 8 tonnes charge utile
        "ptac": 12000,      # PTAC 12T
        "nb_essieux": 2,
        "base_cost_fcfa": 100000,
        "cost_per_km_fcfa": 400,
        "usage": "Distribution régionale"
    },
    "porteur_19t": {
        "id": "porteur_19t",
        "name": "Porteur 19T (4x2)",
        "category": "porteur",
        "type": "4x2",
        "length": 960,      # 9.6m
        "width": 248,       # 2.48m
        "height": 260,      # 2.6m
        "max_weight": 12000, # 12 tonnes charge utile
        "ptac": 19000,      # PTAC 19T (limite UEMOA 2 essieux = 18T)
        "nb_essieux": 2,
        "base_cost_fcfa": 150000,
        "cost_per_km_fcfa": 500,
        "usage": "Transport régional, conteneur 20ft"
    },
    "porteur_26t": {
        "id": "porteur_26t",
        "name": "Porteur 26T (6x2/6x4)",
        "category": "porteur",
        "type": "6x2",
        "length": 1000,     # 10m
        "width": 248,       # 2.48m
        "height": 260,      # 2.6m
        "max_weight": 18000, # 18 tonnes charge utile
        "ptac": 26000,      # PTAC 26T (limite UEMOA 3 essieux)
        "nb_essieux": 3,
        "base_cost_fcfa": 200000,
        "cost_per_km_fcfa": 600,
        "usage": "Transport lourd, chantiers"
    },
}

# =============================================================================
# SEMI-REMORQUES STANDARD
# =============================================================================

SEMI_REMORQUES = {
    "semi_plateau_26t": {
        "id": "semi_plateau_26t",
        "name": "Semi-remorque Plateau 26T (13.6m)",
        "category": "semi-remorque",
        "type": "plateau_standard",
        "length": 1360,     # 13.6m (norme EU)
        "width": 248,       # 2.48m
        "height": 270,      # 2.7m hauteur utile
        "max_weight": 26000, # 26 tonnes charge utile
        "ptra": 44000,      # PTRA 44T (tracteur 4x2 + semi 3 essieux)
        "nb_essieux": 3,
        "base_cost_fcfa": 220000,
        "cost_per_km_fcfa": 700,
        "usage": "Marchandises générales, palettes"
    },
    "semi_plateau_32t": {
        "id": "semi_plateau_32t",
        "name": "Semi-remorque Plateau 32T (13.6m)",
        "category": "semi-remorque",
        "type": "plateau_standard",
        "length": 1360,     # 13.6m
        "width": 250,       # 2.5m
        "height": 270,      # 2.7m
        "max_weight": 32000, # 32 tonnes charge utile
        "ptra": 51000,      # PTRA 51T (tracteur 6x4 + semi 3 essieux)
        "nb_essieux": 3,
        "base_cost_fcfa": 280000,
        "cost_per_km_fcfa": 850,
        "usage": "Charges lourdes, project cargo"
    },
    "semi_fourgon_28t": {
        "id": "semi_fourgon_28t",
        "name": "Semi-remorque Fourgon 28T (13.6m)",
        "category": "semi-remorque",
        "type": "fourgon",
        "length": 1360,     # 13.6m
        "width": 248,       # 2.48m
        "height": 270,      # 2.7m intérieur
        "max_weight": 28000, # 28 tonnes
        "ptra": 46000,
        "nb_essieux": 3,
        "volume_m3": 90,
        "base_cost_fcfa": 250000,
        "cost_per_km_fcfa": 750,
        "usage": "Marchandises protégées"
    },
    "semi_tautliner_28t": {
        "id": "semi_tautliner_28t",
        "name": "Semi-remorque Tautliner 28T (13.6m)",
        "category": "semi-remorque",
        "type": "tautliner",
        "length": 1360,     # 13.6m
        "width": 248,       # 2.48m
        "height": 270,      # 2.7m
        "max_weight": 28000, # 28 tonnes
        "ptra": 46000,
        "nb_essieux": 3,
        "volume_m3": 100,
        "base_cost_fcfa": 240000,
        "cost_per_km_fcfa": 720,
        "usage": "Chargement latéral, palettes"
    },
}

# =============================================================================
# CHÂSSIS PORTE-CONTENEURS
# =============================================================================

PORTE_CONTENEURS = {
    "chassis_20ft": {
        "id": "chassis_20ft",
        "name": "Châssis porte-conteneur 20ft",
        "category": "porte-conteneur",
        "type": "chassis_20ft",
        "length": 606,      # 6.06m (conteneur 20ft)
        "width": 244,       # 2.44m
        "height": 259,      # 2.59m (standard) ou 290 (HC)
        "max_weight": 28000, # 28 tonnes (conteneur 20ft max 30.48T brut)
        "ptra": 44000,
        "nb_essieux": 2,
        "base_cost_fcfa": 180000,
        "cost_per_km_fcfa": 600,
        "usage": "Conteneur ISO 20 pieds"
    },
    "chassis_40ft": {
        "id": "chassis_40ft",
        "name": "Châssis porte-conteneur 40ft",
        "category": "porte-conteneur",
        "type": "chassis_40ft",
        "length": 1219,     # 12.19m (conteneur 40ft)
        "width": 244,       # 2.44m
        "height": 259,      # 2.59m (standard) ou 290 (HC)
        "max_weight": 30000, # 30 tonnes
        "ptra": 51000,
        "nb_essieux": 3,
        "base_cost_fcfa": 250000,
        "cost_per_km_fcfa": 800,
        "usage": "Conteneur ISO 40 pieds"
    },
    "chassis_40ft_hc": {
        "id": "chassis_40ft_hc",
        "name": "Châssis porte-conteneur 40ft High Cube",
        "category": "porte-conteneur",
        "type": "chassis_40ft_hc",
        "length": 1219,     # 12.19m
        "width": 244,       # 2.44m
        "height": 290,      # 2.90m (High Cube)
        "max_weight": 30000, # 30 tonnes
        "ptra": 51000,
        "nb_essieux": 3,
        "base_cost_fcfa": 260000,
        "cost_per_km_fcfa": 820,
        "usage": "Conteneur ISO 40ft High Cube"
    },
}

# =============================================================================
# SEMI-REMORQUES SURBAISSÉES (LOWBED) - Pour charges hors gabarit
# =============================================================================

LOWBEDS = {
    "lowbed_2ess_50t": {
        "id": "lowbed_2ess_50t",
        "name": "Lowbed 2 essieux 50T",
        "category": "lowbed",
        "type": "surbaissee_2ess",
        "length": 1000,     # 10m plateau
        "width": 275,       # 2.75m (élargi)
        "height": 350,      # 3.5m hauteur utile (plateau bas ~1m)
        "plateau_height": 100, # Hauteur du plateau: 1m
        "max_weight": 50000, # 50 tonnes
        "ptra": 80000,
        "nb_essieux": 2,
        "base_cost_fcfa": 400000,
        "cost_per_km_fcfa": 1200,
        "usage": "Engins moyens, machines",
        "transport_exceptionnel": False
    },
    "lowbed_3ess_60t": {
        "id": "lowbed_3ess_60t",
        "name": "Lowbed 3 essieux 60T",
        "category": "lowbed",
        "type": "surbaissee_3ess",
        "length": 1100,     # 11m plateau
        "width": 300,       # 3m (élargi)
        "height": 380,      # 3.8m hauteur utile
        "plateau_height": 95, # Hauteur du plateau: 0.95m
        "max_weight": 60000, # 60 tonnes
        "ptra": 100000,
        "nb_essieux": 3,
        "base_cost_fcfa": 500000,
        "cost_per_km_fcfa": 1500,
        "usage": "Engins lourds, transformateurs",
        "transport_exceptionnel": True
    },
    "lowbed_4ess_80t": {
        "id": "lowbed_4ess_80t",
        "name": "Lowbed 4 essieux 80T",
        "category": "lowbed",
        "type": "surbaissee_4ess",
        "length": 1300,     # 13m plateau
        "width": 300,       # 3m
        "height": 400,      # 4m hauteur utile
        "plateau_height": 95, # 0.95m
        "max_weight": 80000, # 80 tonnes
        "ptra": 120000,
        "nb_essieux": 4,
        "base_cost_fcfa": 700000,
        "cost_per_km_fcfa": 2000,
        "usage": "Charges très lourdes",
        "transport_exceptionnel": True
    },
    "lowbed_5ess_120t": {
        "id": "lowbed_5ess_120t",
        "name": "Lowbed 5+ essieux 120T",
        "category": "lowbed",
        "type": "surbaissee_5ess",
        "length": 1500,     # 15m plateau
        "width": 300,       # 3m
        "height": 420,      # 4.2m hauteur utile
        "plateau_height": 90, # 0.9m
        "max_weight": 120000, # 120 tonnes
        "ptra": 180000,
        "nb_essieux": 5,
        "base_cost_fcfa": 1200000,
        "cost_per_km_fcfa": 3500,
        "usage": "Convois exceptionnels",
        "transport_exceptionnel": True
    },
    "lowbed_extra_surbaissee_70t": {
        "id": "lowbed_extra_surbaissee_70t",
        "name": "Lowbed Extra-surbaissée 70T (charges hautes)",
        "category": "lowbed",
        "type": "extra_surbaissee",
        "length": 1200,     # 12m plateau
        "width": 300,       # 3m
        "height": 450,      # 4.5m hauteur utile (plateau très bas)
        "plateau_height": 50, # 0.5m seulement!
        "max_weight": 70000, # 70 tonnes
        "ptra": 110000,
        "nb_essieux": 4,
        "base_cost_fcfa": 800000,
        "cost_per_km_fcfa": 2200,
        "usage": "Charges hautes (transformateurs, cuves)",
        "transport_exceptionnel": True
    },
}

# =============================================================================
# REMORQUES MODULAIRES (SPMT) - Pour charges exceptionnelles
# =============================================================================

MODULAIRES = {
    "modulaire_4lignes_180t": {
        "id": "modulaire_4lignes_180t",
        "name": "Remorque modulaire 4 lignes 180T",
        "category": "modulaire",
        "type": "hydraulique_4lignes",
        "length": 1200,     # 12m configurable
        "width": 300,       # 3m
        "height": 500,      # 5m hauteur utile
        "max_weight": 180000, # 180 tonnes
        "nb_lignes": 4,
        "base_cost_fcfa": 2000000,
        "cost_per_km_fcfa": 5000,
        "usage": "Transport lourd exceptionnel",
        "transport_exceptionnel": True
    },
    "modulaire_6lignes_270t": {
        "id": "modulaire_6lignes_270t",
        "name": "Remorque modulaire 6 lignes 270T",
        "category": "modulaire",
        "type": "hydraulique_6lignes",
        "length": 1500,     # 15m
        "width": 300,       # 3m
        "height": 500,      # 5m
        "max_weight": 270000, # 270 tonnes
        "nb_lignes": 6,
        "base_cost_fcfa": 3000000,
        "cost_per_km_fcfa": 7000,
        "usage": "Transport très lourd",
        "transport_exceptionnel": True
    },
    "spmt_scheuerle_480t": {
        "id": "spmt_scheuerle_480t",
        "name": "SPMT Scheuerle 4-8 lignes 480T",
        "category": "spmt",
        "type": "automoteur",
        "length": 2000,     # 20m configurable
        "width": 300,       # 3m (extensible)
        "height": 600,      # 6m hauteur utile
        "max_weight": 480000, # 480 tonnes
        "nb_lignes": 8,
        "base_cost_fcfa": 5000000,
        "cost_per_km_fcfa": 15000,
        "usage": "Convois exceptionnels majeurs",
        "transport_exceptionnel": True
    },
}

# =============================================================================
# CATALOGUE COMPLET
# =============================================================================

def get_all_trucks() -> List[Dict[str, Any]]:
    """Retourne tous les camions du catalogue."""
    all_trucks = []
    for catalog in [PORTEURS, SEMI_REMORQUES, PORTE_CONTENEURS, LOWBEDS, MODULAIRES]:
        all_trucks.extend(catalog.values())
    return all_trucks


def get_standard_trucks() -> List[Dict[str, Any]]:
    """Retourne les camions standards (hors transport exceptionnel)."""
    trucks = []
    for catalog in [PORTEURS, SEMI_REMORQUES, PORTE_CONTENEURS]:
        trucks.extend(catalog.values())
    # Ajouter lowbed 2 essieux (pas exceptionnel)
    trucks.append(LOWBEDS["lowbed_2ess_50t"])
    return trucks


def get_lowbeds() -> List[Dict[str, Any]]:
    """Retourne les lowbeds pour charges hors gabarit."""
    return list(LOWBEDS.values())


def get_exceptional_trucks() -> List[Dict[str, Any]]:
    """Retourne les équipements pour transport exceptionnel."""
    trucks = []
    for truck in LOWBEDS.values():
        if truck.get("transport_exceptionnel"):
            trucks.append(truck)
    trucks.extend(MODULAIRES.values())
    return trucks


def get_truck_by_id(truck_id: str) -> Dict[str, Any]:
    """Retourne un camion par son ID."""
    for catalog in [PORTEURS, SEMI_REMORQUES, PORTE_CONTENEURS, LOWBEDS, MODULAIRES]:
        if truck_id in catalog:
            return catalog[truck_id]
    return None


# =============================================================================
# RÉGLEMENTATION UEMOA
# =============================================================================

UEMOA_LIMITS = {
    "essieu_simple_avant": 6000,      # 6T
    "essieu_simple_arriere": 12000,   # 12T (roues jumelées)
    "tandem_type2": 16000,            # 16T
    "tandem_type4": 20000,            # 20T
    "tridem_type1": 21000,            # 21T
    "tridem_type2": 25000,            # 25T
    "ptac_2_essieux": 18000,          # 18T
    "ptac_3_essieux": 26000,          # 26T
    "ptra_4_essieux": 38000,          # 38T
    "ptra_5_essieux": 46000,          # 46T
    "ptra_6_essieux": 51000,          # 51T
    "largeur_max_cm": 255,            # 2.55m
    "hauteur_max_cm": 400,            # 4m
    "longueur_vehicule_isole_cm": 1200,   # 12m
    "longueur_semi_remorque_cm": 1360,    # 13.6m
    "longueur_articule_cm": 1650,         # 16.5m
    "longueur_train_routier_cm": 2200,    # 22m
}

TRANSPORT_EXCEPTIONNEL_CATEGORIES = {
    1: {
        "longueur_min_m": 16.6,
        "longueur_max_m": 20.0,
        "largeur_min_m": 2.6,
        "largeur_max_m": 3.0,
        "poids_min_t": 44,
        "poids_max_t": 48,
        "escorte": "1 véhicule"
    },
    2: {
        "longueur_min_m": 20.0,
        "longueur_max_m": 25.0,
        "largeur_min_m": 3.0,
        "largeur_max_m": 4.0,
        "poids_min_t": 48,
        "poids_max_t": 72,
        "escorte": "2 véhicules"
    },
    3: {
        "longueur_min_m": 25.0,
        "longueur_max_m": None,
        "largeur_min_m": 4.0,
        "largeur_max_m": None,
        "poids_min_t": 72,
        "poids_max_t": None,
        "escorte": "Police + 2 véhicules"
    },
}
