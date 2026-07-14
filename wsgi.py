import sys
import os

path = os.path.expanduser('~/student-admissions')
if path not in sys.path:
    sys.path.insert(0, path)

from app import app as application
