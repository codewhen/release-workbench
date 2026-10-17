import json, sys
payload = json.load(sys.stdin)
print(json.dumps({"name": sys.argv[1], "inputs": payload["inputs"]}))
