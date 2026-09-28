import re
import subprocess
import sys

name = "tiny-sd"
result = subprocess.run(["flash", "deploy", "--name", name], capture_output=True, text=True)
if result.returncode != 0:
    print(result.stderr, file=sys.stderr)
    sys.exit(1)

match = re.search(r'endpoint[_\s-]?id[:\s]+(\w+)', result.stderr, re.IGNORECASE)
endpoint_id = match.group(1) if match else name
with open(".flash_endpoint_id", "w") as f:
    f.write(endpoint_id)
