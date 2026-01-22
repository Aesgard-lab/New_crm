import os
import django
import traceback

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
try:
    django.setup()
    print("Django setup success")
except Exception:
    traceback.print_exc()
