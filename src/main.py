import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.routes.optimization import optimization_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'sodatra-secret-key-2025'

# Enable CORS for all routes (permet à Lovable de communiquer)
CORS(app)

# Configuration pour upload de fichiers
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max

# Enregistrement des routes d'optimisation
app.register_blueprint(optimization_bp, url_prefix='/api/optimization')

@app.route('/health')
def health():
    return {"status": "ok", "message": "Backend SODATRA opérationnel"}

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return {"message": "API Backend SODATRA - Utilisez /api/optimization/*"}

if __name__ == '__main__':
    # Railway fournit le port via la variable d'environnement PORT
    port = int(os.environ.get('PORT', 5000))
    print("=" * 60)
    print("🚀 Backend SODATRA démarré avec succès!")
    print("=" * 60)
    print(f"📡 API disponible sur: http://localhost:{port}/api/optimization")
    print(f"💚 Health check: http://localhost:{port}/health")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=port)
