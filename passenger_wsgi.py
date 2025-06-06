import sys
import os

# Add your project directory to the sys.path
sys.path.insert(0, os.path.dirname(__file__))

# Use Flask app instead of FastAPI for better WSGI compatibility
from flask_app import app

# Flask apps are WSGI compatible by default
application = app