"""
Script to fix Gym creation in tests
"""
import re

# Read the file
with open('activities/tests_reviews.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all occurrences
content = re.sub(
    r'Gym\.objects\.create\(\s*name="Test Gym",\s*slug="test-gym"\s*\)',
    'Gym.objects.create(name="Test Gym")',
    content
)

# Write back
with open('activities/tests_reviews.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed all Gym creation statements")
