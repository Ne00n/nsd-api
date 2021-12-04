import requests, json, time, sys, os
from random import randint
from datetime import datetime

path = ""
if len(sys.argv) == 2:
    path = sys.argv[1]

print("Loading domains.json")
with open(f"{path}domains.json") as f:
    domains = json.load(f)

if not os.path.isdir("certs"): os.mkdir('certs')

def fetch(domain,url):
    print(f"Fetching {url}")
    r = requests.get(url,allow_redirects=False)
    print(f"Got {r.status_code}")
    if (r.status_code == 200): return r.json()
    return False

def splitDomain(domain):
    parts = domain.split(".")
    if len(parts) == 2:
        return "",domain
    else:
        return ".".join(parts[0:len(parts)-2]),".".join(parts[len(parts)-2:])

def getCert(domains,fullDomain,path):
    print(f"Getting Certificate for {fullDomain}")
    endpoint = domains['remote'][0]
    subdomain,domain = splitDomain(fullDomain)
    url = f"https://{endpoint}/{domains['token']}/{domain}/{subdomain}/request/cert"
    cert = fetch(domain,url)
    if cert:
        print(f"Saving Certificate for {fullDomain}")
        with open(f"{path}certs/{fullDomain}-fullchain.pem", 'w') as out:
            out.write(cert['success']['fullchain'])
        with open(f"{path}certs/{fullDomain}-privkey.pem", 'w') as out:
            out.write(cert['success']['privkey'])
        os.system("sudo /bin/systemctl reload nginx")
    else:
        print(f"Failed to get Certificate for {fullDomain}")

for fullDomain in domains['domains']:
    print(f"Checking {fullDomain}")
    if not os.path.isfile(f"{path}certs/{fullDomain}-fullchain.pem") or not os.path.isfile(f"{path}certs/{fullDomain}-privkey.pem"):
        print(f"Certificate not found for {fullDomain}")
        getCert(domains,fullDomain,path)
    else:
        print(f"Certificate found for {fullDomain}")
        print(f"Checking Certificate age for {fullDomain}")
        if os.path.getmtime(f"{path}certs/{fullDomain}-fullchain.pem") + (86400 * 30) < datetime.now().timestamp():
            print(f"Certificate for {fullDomain} is older than 30 Days, renewing")
            getCert(domains,fullDomain,path)
        else:
            print(f"Skipping {fullDomain}")
    time.sleep(randint(60,120))
