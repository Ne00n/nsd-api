import socket, json, os, re
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

class MyHandler(SimpleHTTPRequestHandler):
    dir = "/etc/nsd/nsd.conf.d/"
    print("Loading config")
    with open('configs/config.json') as f:
        config = json.load(f)
    print("Ready")

    def response(self,key,msg):
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
        with open(file, 'r') as file:
            return file.read()

    def saveFile(self,file,data):
        with open(file, "w") as file:
            file.write(data)

    def do_GET(self):
        if len(self.path) > 200:
            self.send_response(414)
            self.response("error","way to fucking long")
            return
        parts = re.split(r'/', self.path)
        if len(parts) < 6 or len(parts) > 7:
            self.send_response(400)
            self.response("error","incomplete")
            return
        if len(parts) == 6:
            empty, token, domain, subdomain, type, param = self.path.split('/')
        elif len(parts) == 7:
            emtpy, token, domain, subdomain, type, param, target = self.path.split('/')
        if token not in self.config["tokens"]:
            self.send_response(401)
            self.response("error","token required")
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
                self.send_response(200)
                self.response("success","record added")
            else:
                self.send_response(404)
                self.response("error","record not found")
                return
        if param == "update":
            zone = self.loadFile(self.dir+domain)
            zone = re.sub(subdomain+'\t*[0-9]+\t*IN\t*'+type+'\t*'+records[domain][type][subdomain]['target'], subdomain+'\t300\tIN\t'+type+'\t'+self.headers.get("X-Real-IP")+"\n", zone)
            self.saveFile(self.dir+domain,zone)
            os.system("sudo /usr/bin/systemctl reload nsd")
            self.send_response(200)
            self.response("success","record updated")
        elif param == "delete":
            zone = self.loadFile(self.dir+domain)
            zone = re.sub(subdomain+'\t*[0-9]+\t*IN\t*'+type+'\t*'+records[domain][type][subdomain]['target'], "", zone)
            self.saveFile(self.dir+domain,zone)
            os.system("sudo /usr/bin/systemctl reload nsd")
            self.send_response(200)
            self.response("success","record updated")

server = HTTPServer(('127.0.0.1', 8080), MyHandler)
try:
    server.serve_forever()
except KeyboardInterrupt:
    server.socket.close()
