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
    app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB max for web uploads
    app.config['DATA_FOLDER'] = app.config['UPLOAD_FOLDER']  # Root folder containing system folders

    _seed_example_systems(app.config['DATA_FOLDER'])

    # Return a JSON error when upload exceeds MAX_CONTENT_LENGTH
    from werkzeug.exceptions import RequestEntityTooLarge
    from flask import jsonify as _jsonify

    @app.errorhandler(RequestEntityTooLarge)
    def handle_too_large(e):
        max_mb = app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)
        return _jsonify({
            'error': f'File too large. The web app accepts files up to {max_mb} MB. '
                     f'For larger files, use the command-line interface (CLI).'
        }), 413
    
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

