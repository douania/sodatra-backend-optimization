import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.routes.optimization import optimization_bp

# Patch 1: Import Case Files
from src.app_config import Config
from src.db import init_db, is_db_available
from src.routes.casefiles import casefiles_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'sodatra-secret-key-2025'

# Enable CORS for all routes (permet à Lovable de communiquer)
CORS(app)

# Configuration pour upload de fichiers
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_UPLOAD_SIZE

# Patch 1: Initialiser la base de données (si DATABASE_URL est définie)
if Config.DATABASE_URL:
    try:
        init_db(Config.DATABASE_URL)
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️ Database initialization failed: {e}")
        print("   Case Files features will be disabled")
else:
    print("⚠️ DATABASE_URL not set - Case Files features disabled")

# Enregistrement des routes d'optimisation
app.register_blueprint(optimization_bp, url_prefix='/api/optimization')

# Patch 1: Enregistrement des routes Case Files
app.register_blueprint(casefiles_bp, url_prefix='/api/casefiles')

@app.route('/health')
def health():
    return {
        "status": "ok", 
        "message": "Backend SODATRA opérationnel",
        "version": "2.1.0",  # Patch 1
        "features": {
            "optimization": True,
            "casefiles": is_db_available(),
        }
    }

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return {
            "message": "API Backend SODATRA v2.1.0",
            "endpoints": {
                "optimization": "/api/optimization/*",
                "casefiles": "/api/casefiles/*" if is_db_available() else "disabled (no DATABASE_URL)",
            }
        }

if __name__ == '__main__':
    # Railway fournit le port via la variable d'environnement PORT
    port = int(os.environ.get('PORT', 5000))
    print("=" * 60)
    print("🚀 Backend SODATRA v2.1.0 démarré avec succès!")
    print("=" * 60)
    print(f"📡 API Optimization: http://localhost:{port}/api/optimization")
    print(f"📁 API Case Files:   http://localhost:{port}/api/casefiles" + (" (enabled)" if is_db_available() else " (disabled)"))
    print(f"💚 Health check:     http://localhost:{port}/health")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=port)
