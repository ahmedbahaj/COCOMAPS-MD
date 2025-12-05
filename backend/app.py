"""
Main Flask application for PDB Analysis API
"""
from flask import Flask
from flask_cors import CORS
import os

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    CORS(app)  # Enable CORS for Vue.js frontend
    
    # Configuration
    app.config['UPLOAD_FOLDER'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2 GB max
    app.config['DATA_FOLDER'] = app.config['UPLOAD_FOLDER']  # Root folder containing system folders
    
    # Register blueprints
    from backend.routes import data, upload, systems
    app.register_blueprint(systems.bp, url_prefix='/api')
    app.register_blueprint(data.bp, url_prefix='/api')
    app.register_blueprint(upload.bp, url_prefix='/api')
    
    return app

if __name__ == '__main__':
    app = create_app()
    print("Starting PDB Analysis API on http://localhost:5000")
    print("API endpoints available at /api/*")
    app.run(host='0.0.0.0', port=5000, debug=True)

