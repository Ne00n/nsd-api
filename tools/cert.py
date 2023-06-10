import simple_acme_dns, requests, json, time, sys, os
from random import randint
from datetime import datetime

path = os.path.realpath(__file__).replace("cert.py","")

print(f"Loading {path}domains.json")
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

def fetchUrl(remote,url):
    print(f"Running {url}")
    try:
        r = requests.get(url,verify=True, timeout=10)
        print(f"Got {r.status_code} from {remote}")
        return 0
    except Exception as e:
        print(e)
        return 1

def getCert(config,fullDomain,path):
    print(f"Getting Certificate for {fullDomain}")
    subdomain,domain = splitDomain(fullDomain)
    #Lets Encrypt
    directory = "https://acme-v02.api.letsencrypt.org/directory"
    #directory = "https://acme-staging-v02.api.letsencrypt.org/directory"
    acmeSubdomain = ""
    if subdomain != "": acmeSubdomain = "."+subdomain
    if subdomain != "": subdomain = subdomain+"."
    print(f"Getting ACME tokens for {subdomain}{domain}")
    try:
        client = simple_acme_dns.ACMEClient(domains=[subdomain+domain],email=config["email"],directory=directory,nameservers=["8.8.8.8", "1.1.1.1"],new_account=True,generate_csr=True)
    except Exception as e:
        print(e)
        return False

    tokens,errors = [],0
    for acmeDomain, token in client.request_verification_tokens().items():
        print("adding {domain} --> {token}".format(domain=acmeDomain, token=token))
        tokens.append(token[0])
        for remote in config['remote']: errors += fetchUrl(remote,f"https://{remote}/{config['token']}/{domain}/_acme-challenge{acmeSubdomain}/TXT/add/{token[0]}")
        if errors == len(config['remote']): exit("Aborting, could not reach a single remote")

        print("Waiting for dns propagation (1200s)")
        try:
            if client.check_dns_propagation(timeout=1200):
                print("Requesting certificate")
                client.request_certificate()
                fullchain = client.certificate.decode()
                privkey = client.private_key.decode()
            else:
                client.deactivate_account()
                print("Failed to issue certificate for " + str(client.domains))
                return False
        except Exception as e:
            print(f"Failed to get Certificate for {fullDomain}")
            return False
        finally:
            for token in tokens:
                for remote in config['remote']: fetchUrl(remote,f"https://{remote}/{config['token']}/{domain}/_acme-challenge{acmeSubdomain}/TXT/del/{token}")

        print(f"Saving Certificate for {fullDomain}")
        with open(f"{path}certs/{fullDomain}-fullchain.pem", 'w') as out:
            out.write(fullchain)
        with open(f"{path}certs/{fullDomain}-privkey.pem", 'w') as out:
            out.write(privkey)
        return True

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
            resp = getCert(domains,fullDomain,path)
            if not resp: exit()
        else:
            print(f"Skipping {fullDomain}")
    time.sleep(randint(60,120))
