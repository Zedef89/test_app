"""
WSGI config for backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys
import pathlib

# Add /app/libs to sys.path
LIBS_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "libs" # Adjusted path for wsgi.py
sys.path.insert(0, str(LIBS_DIR))

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

application = get_wsgi_application()
