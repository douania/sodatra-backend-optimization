# Backend SODATRA - Moteur d'Optimisation de Chargement

**Version :** 2.0  
**Auteur :** Manus AI  
**Date :** 31 juillet 2025

## 📦 Qu'est-ce que c'est ?

Ce backend Python/Flask est le **moteur de calcul** de votre application SODATRA. Il gère toute la logique complexe que Lovable ne peut pas faire :

- ✅ Extraction intelligente des packing lists Excel
- ✅ Algorithmes d'optimisation de chargement 3D (simple + génétique)
- ✅ Calculs financiers et de taxes
- ✅ Génération de visualisations 3D
- ✅ API REST complète pour Lovable

## 🚀 Installation Rapide (3 étapes)

### Étape 1 : Installer Python

Assurez-vous d'avoir Python 3.11+ installé :

```bash
python3 --version
```

### Étape 2 : Installer les dépendances

```bash
# Créer un environnement virtuel
python3 -m venv venv

# Activer l'environnement
# Sur Mac/Linux :
source venv/bin/activate
# Sur Windows :
venv\Scripts\activate

# Installer les packages
pip install -r requirements.txt
```

### Étape 3 : Lancer le serveur

```bash
python src/main.py
```

Vous devriez voir :

```
🚀 Backend SODATRA démarré avec succès!
📡 API disponible sur: http://localhost:5000/api/optimization
💚 Health check: http://localhost:5000/health
```

## 🔌 Endpoints API Disponibles

### 1. Health Check
```
GET /health
```
Vérifie que le serveur fonctionne.

### 2. Upload Packing List
```
POST /api/optimization/upload
Content-Type: multipart/form-data

Body: file (fichier Excel)
```

### 3. Liste des Camions
```
GET /api/optimization/truck-specs
```

### 4. Lancer l'Optimisation
```
POST /api/optimization/optimize
Content-Type: application/json

Body: {
  "items": [...],
  "truck": {...},
  "algorithm": "genetic"
}
```

### 5. Générer Visualisation
```
POST /api/optimization/visualize
Content-Type: application/json

Body: {
  "placements": [...],
  "truck_specs": {...}
}
```

## 📁 Structure du Projet

```
backend-sodatra-complet/
├── src/
│   ├── main.py                 # Point d'entrée du serveur
│   ├── models/
│   │   └── item.py            # Modèles de données
│   ├── services/
│   │   ├── extractor.py       # Extraction Excel
│   │   ├── optimizer.py       # Algorithmes d'optimisation
│   │   └── visualizer.py      # Génération visualisations
│   └── routes/
│       └── optimization.py    # Routes API
├── requirements.txt           # Dépendances Python
└── README.md                 # Ce fichier
```

## 🔗 Connexion avec Lovable

Une fois le backend lancé, configurez Lovable pour utiliser l'URL :

**Développement local :**
```
http://localhost:5000/api
```

**Production (après déploiement) :**
```
https://votre-domaine.com/api
```

## 🧪 Tester l'API

### Test avec curl :

```bash
# Health check
curl http://localhost:5000/health

# Liste des camions
curl http://localhost:5000/api/optimization/truck-specs
```

### Test avec Postman :

Importez les endpoints dans Postman et testez chaque route.

## 🚢 Déploiement en Production

### Option 1 : Railway (Recommandé - Gratuit)

1. Créez un compte sur [Railway.app](https://railway.app)
2. Créez un nouveau projet
3. Connectez votre dépôt GitHub
4. Railway détectera automatiquement Python et déploiera

### Option 2 : Google Cloud Run

```bash
gcloud run deploy sodatra-backend \
  --source . \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated
```

### Option 3 : AWS Elastic Beanstalk

Suivez la documentation AWS pour déployer une application Flask.

## 🔧 Configuration Avancée

### Variables d'Environnement

Créez un fichier `.env` :

```
FLASK_ENV=production
SECRET_KEY=votre-clé-secrète
MAX_UPLOAD_SIZE=10485760
```

### Personnalisation des Algorithmes

Modifiez les paramètres dans `src/services/optimizer.py` :

```python
# Algorithme génétique
POPULATION_SIZE = 50
GENERATIONS = 100
MUTATION_RATE = 0.15
```

## 📚 Documentation Technique

Pour plus de détails sur l'implémentation :

- Voir `guide_developpement_backend.md` (fourni séparément)
- Voir `etapes_developpement_backend.md` (fourni séparément)

## ❓ FAQ

**Q : Le backend est-il déjà complet ?**  
R : Oui ! Ce backend contient tous les algorithmes d'optimisation fonctionnels. Vous pouvez l'utiliser tel quel.

**Q : Dois-je modifier le code ?**  
R : Non pour commencer. Pour ajouter les règles SODATRA spécifiques (taxes UEMOA, etc.), vous devrez enrichir le fichier `optimization.py`.

**Q : Puis-je utiliser ce backend avec autre chose que Lovable ?**  
R : Oui ! C'est une API REST standard. N'importe quel frontend peut l'utiliser.

## 🆘 Support

En cas de problème :

1. Vérifiez que toutes les dépendances sont installées
2. Vérifiez que le port 5000 n'est pas déjà utilisé
3. Consultez les logs dans le terminal

## 📝 Licence

Ce code a été développé par Manus AI pour le projet SODATRA.

---

**Prêt à démarrer ? Lancez `python src/main.py` et connectez Lovable !** 🚀
