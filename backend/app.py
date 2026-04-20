"""
Main Flask application for PDB Analysis API
"""
from flask import Flask
from flask_cors import CORS
import os
import shutil
from pathlib import Path


def _seed_example_systems(data_folder):
    """Copy bundled example systems into systems/ if not already present."""
    examples_dir = Path(data_folder) / 'example_systems'
    systems_dir = Path(data_folder) / 'systems'
    if not examples_dir.exists():
        return
    systems_dir.mkdir(exist_ok=True)
    for src in examples_dir.iterdir():
        if src.is_dir() and not src.name.startswith('.'):
            dst = systems_dir / src.name
            if not dst.exists():
                shutil.copytree(src, dst)


def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    CORS(app)  # Enable CORS for Vue.js frontend
    
    # Configuration
    app.config['UPLOAD_FOLDER'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2 GB max
    app.config['DATA_FOLDER'] = app.config['UPLOAD_FOLDER']  # Root folder containing system folders

    _seed_example_systems(app.config['DATA_FOLDER'])
    
    # Register blueprints
    from backend.routes import data, upload, systems
    app.register_blueprint(systems.bp, url_prefix='/api')
    app.register_blueprint(data.bp, url_prefix='/api')
    app.register_blueprint(upload.bp, url_prefix='/api')
    
    return app

if __name__ == '__main__':
    app = create_app()
    print("Starting PDB Analysis API on http://localhost:5001")
    print("API endpoints available at /api/*")
    app.run(host='0.0.0.0', port=5001, debug=True)

