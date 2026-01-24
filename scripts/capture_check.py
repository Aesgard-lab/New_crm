import subprocess
import os

with open("check_output.txt", "w") as f:
    try:
        subprocess.run(["python", "manage.py", "check"], stdout=f, stderr=subprocess.STDOUT, check=True)
    except subprocess.CalledProcessError as e:
        pass
