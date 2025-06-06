"""
WSGI entry point for cPanel Python application
"""
import sys
import os

# Add the application directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import from app.py to avoid recursion
from app import application

# Alternative entry points for cPanel compatibility
app = application