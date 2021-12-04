import simple_acme_dns, requests, socket, time, json, os, re
#from Class import simple_acme_dns
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

class MyHandler(SimpleHTTPRequestHandler):
    dir = "/etc/nsd/nsd.conf.d/"
    print("Loading config")
    with open('configs/config.json') as f:
        config = json.load(f)
    print("Ready")

    def response(self,httpCode,key,msg):
        self.send_response(httpCode)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(json.dumps({key: msg}).encode()))

    def call(self,url):
        for run in range(2):
            try:
                r = requests.get(url)
                if (r.status_code == 200): return True
            except Exception as e:
                print(e)
            time.sleep(3)
        return False

    def loadZone(self,zone):
        records = {}
        if Path(self.dir+zone).is_file():
            records[zone] = {}
            with open(self.dir+zone) as f:
                lines = f.readlines()
            for line in lines:
                #sub ttl IN type target/ttl
                parts = re.split(r'\t+', line)
                if len(parts) > 3 and "IN" in parts[2]:
                    if not parts[3] in records[zone]: records[zone][parts[3]] = {}
                    records[zone][parts[3]][parts[0]] = {}
                    records[zone][parts[3]][parts[0]]['ttl'] = parts[1]
                    records[zone][parts[3]][parts[0]]['target'] = parts[4].replace("\n","")
        return records

    def loadFile(self,file):
        try:
            with open(file, 'r') as file: return file.read()
        except Exception as e:
            return False

    def saveFile(self,file,data):
        try:
            with open(file, "w") as file: file.write(data)
        except Exception as e:
            return False
        return True

    def addRecord(self,subdomain,domain,type,target,ttl=3600):
        zone = self.loadFile(self.dir+domain)
        if subdomain == "_acme-challenge": ttl = 1
        if not zone: return False
        if type == "TXT":
            zone = zone + subdomain + f'\t{ttl}\tIN\t{type}\t"{target}"\n'
        else:
            zone = zone + subdomain + f"\t{ttl}\tIN\t{type}\t{target}\n"
        response = self.saveFile(self.dir+domain,zone)
        if not response: return False
        os.system("sudo /bin/systemctl reload nsd")
        return True

    def delRecord(self,subdomain,domain,type,target):
        zone = self.loadFile(self.dir+domain)
        if not zone: return False
        key = '"'+target+'"' if type == "TXT" else target
        zone = re.sub(subdomain+'\t*[0-9]+\t*IN\t*'+type+'\t*'+key+"\n", "", zone)
        response = self.saveFile(self.dir+domain,zone)
        if not response: return False
        os.system("sudo /bin/systemctl reload nsd")
        return True

    def getCert(self,subdomain,domain,authToken):
        directory = "https://acme-v02.api.letsencrypt.org/directory"
        #directory = "https://acme-staging-v02.api.letsencrypt.org/directory"
        try:
            client = simple_acme_dns.ACMEClient(domains=[subdomain+"."+domain],email=self.config["email"],directory=directory,nameservers=["8.8.8.8", "1.1.1.1"],new_account=True,generate_csr=True)
        except Exception as e:
            print(e)
            return False

        tokens = []
        for acmeDomain, token in client.request_verification_tokens():
            print("adding {domain} --> {token}".format(domain=acmeDomain, token=token))
            tokens.append(token)
            response = self.addRecord("_acme-challenge",domain,"TXT",token)
            if not response: return False
            for remote in self.config['remote']:
                response = self.call(f"https://{remote}/{authToken}/{domain}/_acme-challenge/TXT/add/{token}")
                if not response:
                    self.delRecord("_acme-challenge",domain,"TXT",token)
                    return False

        print("Waiting for dns propagation")
        try:
            if client.check_dns_propagation(timeout=290):
                print("Requesting certificate")
                client.request_certificate()
                fullchain = client.certificate.decode()
                privkey = client.private_key.decode()
            else:
                client.deactivate_account()
                print("Failed to issue certificate for " + str(client.domains))
                return False
        except Exception as e:
            print(e)
            return False
        finally:
            for token in tokens:
                response = self.delRecord("_acme-challenge",domain,"TXT",token)
                if not response: return False
                for remote in self.config['remote']:
                    response = self.call(f"https://{remote}/{authToken}/{domain}/_acme-challenge/TXT/del/{token}")
                    if not response: return False

        return fullchain,privkey

    def do_GET(self):
        if len(self.path) > 200:
            self.response(414,"error","way to fucking long")
            return
        parts = re.split(r'/', self.path)

        #If request to short or to long, abort
        if len(parts) < 6 or len(parts) > 7:
            self.response(400,"error","incomplete")
            return

        #Split based on length
        if len(parts) == 6:
            empty, token, domain, subdomain, type, param = self.path.split('/')
        elif len(parts) == 7:
            empty, token, domain, subdomain, type, param, target = self.path.split('/')

        #Check if token matches
        if token not in self.config["tokens"]:
            self.response(401,"error","token required")
            return

        #Check if domain has a valid format
        results = re.findall("^[a-zA-Z0-9]{2,30}\.[a-zA-Z]{2,30}$",domain, re.MULTILINE)
        if not results:
            self.response(400,"error","invalid domain")
            return

        #Check if zone file exists
        records = self.loadZone(domain)
        if not records:
            self.response(404,"error","zone file not found")
            return

        if param == "add":
            #Check if record requested to add already exists or not
            if type not in records[domain] or subdomain not in records[domain][type] or records[domain][type][subdomain]['target'] != target:
                response = self.addRecord(subdomain,domain,type,target)
                if response:
                    self.response(200,"success","record added")
                else:
                    self.response(500,"error","could not edit zone file, likely permission error")
            else:
                self.response(400,"error","record already exists")

        elif param == "update":
            zone = self.loadFile(self.dir+domain)
            zone = re.sub(subdomain+'\t*[0-9]+\t*IN\t*'+type+'\t*'+records[domain][type][subdomain]['target'], subdomain+'\t300\tIN\t'+type+'\t'+self.headers.get("X-Real-IP")+"\n", zone)
            self.saveFile(self.dir+domain,zone)
            os.system("sudo /bin/systemctl reload nsd")
            self.response(200,"success","record updated")

        elif param == "cert":
            response = self.getCert(subdomain,domain,token)
            if response:
                self.response(200,"success",{"fullchain":response[0],'privkey':response[1]})
            else:
                self.response(500,"error","could get cert, likely permission error")

        elif param == "del":
            response = self.delRecord(subdomain,domain,type,target)
            if response:
                self.response(200,"success","record updated")
            else:
                self.response(500,"error","could not edit zone file, likely permission error")

server = HTTPServer(('127.0.0.1', 8080), MyHandler)
try:
    server.serve_forever()
except KeyboardInterrupt:
    server.socket.close()
