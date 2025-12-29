# 🚀 Guide de Démarrage Rapide - Backend SODATRA

## Pour Vous (Non-Technique)

Voici ce que vous devez faire pour avoir le backend fonctionnel en 10 minutes.

### Étape 1 : Télécharger le Dossier

Récupérez le dossier `backend-sodatra-complet` que Manus vous a fourni.

### Étape 2 : Ouvrir un Terminal

**Sur Mac :**
- Ouvrez l'application "Terminal"
- Tapez : `cd ` (avec un espace à la fin)
- Glissez le dossier `backend-sodatra-complet` dans la fenêtre
- Appuyez sur Entrée

**Sur Windows :**
- Ouvrez l'application "Invite de commandes" ou "PowerShell"
- Naviguez vers le dossier avec `cd C:\chemin\vers\backend-sodatra-complet`

### Étape 3 : Installer Python (si pas déjà fait)

**Sur Mac :**
```bash
brew install python3
```

**Sur Windows :**
Téléchargez depuis [python.org](https://www.python.org/downloads/)

### Étape 4 : Installer les Dépendances

Copiez-collez ces commandes une par une :

```bash
python3 -m venv venv
source venv/bin/activate  # Sur Mac/Linux
# OU
venv\Scripts\activate     # Sur Windows

pip install -r requirements.txt
```

### Étape 5 : Lancer le Serveur

```bash
python src/main.py
```

Vous devriez voir :
```
🚀 Backend SODATRA démarré avec succès!
📡 API disponible sur: http://localhost:5000/api/optimization
```

**C'est tout ! Le backend fonctionne maintenant.**

---

## Pour Votre Développeur

### Installation Professionnelle

```bash
# Clone ou extraction du dossier
cd backend-sodatra-complet

# Setup environnement
python3.11 -m venv venv
source venv/bin/activate

# Installation dépendances
pip install -r requirements.txt

# Lancement
python src/main.py
```

### Test Rapide

```bash
# Test health check
curl http://localhost:5000/health

# Test liste camions
curl http://localhost:5000/api/optimization/truck-specs

# Test upload (avec un fichier Excel)
curl -X POST -F "file=@packing_list.xlsx" http://localhost:5000/api/optimization/upload
```

### Configuration Lovable

Dans Lovable, configurez l'URL de l'API :

```javascript
const API_BASE_URL = "http://localhost:5000/api";
```

Ou en production :

```javascript
const API_BASE_URL = "https://votre-backend-deploye.com/api";
```

---

## Déploiement Rapide sur Railway (Gratuit)

### Option 1 : Via Interface Web

1. Allez sur [railway.app](https://railway.app)
2. Cliquez sur "New Project"
3. Sélectionnez "Deploy from GitHub"
4. Connectez votre repo contenant ce dossier
5. Railway détecte automatiquement Python et déploie

### Option 2 : Via CLI

```bash
# Installation Railway CLI
npm install -g @railway/cli

# Login
railway login

# Déploiement
railway init
railway up
```

Railway vous donnera une URL publique comme :
```
https://backend-sodatra-production.up.railway.app
```

Utilisez cette URL dans Lovable en production.

---

## Résolution de Problèmes Courants

### Erreur : "Port 5000 already in use"

Un autre programme utilise le port 5000. Changez le port dans `src/main.py` :

```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Utilisez 5001 au lieu de 5000
```

### Erreur : "Module not found"

Les dépendances ne sont pas installées. Relancez :

```bash
pip install -r requirements.txt
```

### Erreur : "Permission denied"

Sur Mac/Linux, vous devrez peut-être utiliser :

```bash
sudo pip install -r requirements.txt
```

---

## Prochaines Étapes

1. ✅ Backend lancé
2. 📱 Connectez Lovable à `http://localhost:5000/api`
3. 🎨 Lovable peut maintenant appeler les endpoints
4. 🚀 Testez le workflow complet

**Le backend que Gemini cherchait existe maintenant et fonctionne !**
