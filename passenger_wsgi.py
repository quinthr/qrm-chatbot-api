import sys
import os

# Add your project directory to the sys.path
sys.path.insert(0, os.path.dirname(__file__))

from main import app

# Create the application object for Passenger
application = app