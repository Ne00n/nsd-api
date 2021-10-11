import socket, json, os, re
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
                    records[zone][parts[3]][parts[0]]['target'] = parts[4]
        return records

    def loadFile(self,file):
        with open(file, 'r') as file: return file.read()

    def saveFile(self,file,data):
        with open(file, "w") as file: file.write(data)

    def do_GET(self):
        if len(self.path) > 200:
            self.response(414,"error","way to fucking long")
            return
        parts = re.split(r'/', self.path)
        if len(parts) < 6 or len(parts) > 7:
            self.response(400,"error","incomplete")
            return
        if len(parts) == 6:
            empty, token, domain, subdomain, type, param = self.path.split('/')
        elif len(parts) == 7:
            empty, token, domain, subdomain, type, param, target = self.path.split('/')
        if token not in self.config["tokens"]:
            self.response(401,"error","token required")
            return
        results = re.findall("^[a-zA-Z0-9]{2,30}\.[a-zA-Z]{2,30}$",domain, re.MULTILINE)
        if not results:
            self.response(400,"error","invalid domain")
            return
        records = self.loadZone(domain)
        if domain not in records or subdomain not in records[domain][type]:
            if param == "add":
                zone = self.loadFile(self.dir+domain)
                if type == "TXT":
                    zone = zone + subdomain + "\t3600\tIN\t"+type+'\t"'+target+'"\n'
                else:
                    zone = zone + subdomain + "\t3600\tIN\t"+type+"\t"+target+"\n"
                self.saveFile(self.dir+domain,zone)
                os.system("sudo /usr/bin/systemctl reload nsd")
                self.response(200,"success","record added")
                return
            else:
                self.response(404,"error","record not found")
                return
        if param == "update":
            zone = self.loadFile(self.dir+domain)
            zone = re.sub(subdomain+'\t*[0-9]+\t*IN\t*'+type+'\t*'+records[domain][type][subdomain]['target'], subdomain+'\t300\tIN\t'+type+'\t'+self.headers.get("X-Real-IP")+"\n", zone)
            self.saveFile(self.dir+domain,zone)
            os.system("sudo /usr/bin/systemctl reload nsd")
            self.response(200,"success","record updated")
        elif param == "delete":
            zone = self.loadFile(self.dir+domain)
            zone = re.sub(subdomain+'\t*[0-9]+\t*IN\t*'+type+'\t*'+records[domain][type][subdomain]['target'], "", zone)
            self.saveFile(self.dir+domain,zone)
            os.system("sudo /usr/bin/systemctl reload nsd")
            self.response(200,"success","record updated")

server = HTTPServer(('127.0.0.1', 8080), MyHandler)
try:
    server.serve_forever()
except KeyboardInterrupt:
    server.socket.close()
