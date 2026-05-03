import sys
sys.path.insert(0, '.')
from src.app import app
print('OK:', app.title)