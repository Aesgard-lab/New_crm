import os
import django
import traceback
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

print("\n--- Testing Imports ---")
try:
    print("Importing finance.models...")
    from finance import models as fm
    print("Success finance.models")
except Exception:
    traceback.print_exc()

try:
    print("Importing sales.api...")
    from sales import api
    print("Success sales.api")
except Exception:
    traceback.print_exc()
