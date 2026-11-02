"""
Vercel API Entrypoint for Studio Pro
"""

import os
import sys

# Add parent directory to path so app.py can be imported
curr_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(curr_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app import app, handler
