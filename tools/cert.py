#python3 cert.py <url>
import requests, sys

r = requests.get(sys.argv[1],allow_redirects=False)
print(f"Got {r.status_code}")
if (r.status_code == 200):
    json = r.json()
    print(json)
