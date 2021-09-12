import socket, json, os, re
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

class MyHandler(SimpleHTTPRequestHandler):
    dir = "/etc/nsd/nsd.conf.d/"
    tokens = ["mahkey"]

    def response(self,key,msg):
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(json.dumps({key: msg}).encode()))

    def loadZone(self,zone):
        records = {}
        if Path(zone).is_file():
            records[zone] = {}
            with open(zone) as f:
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

    def do_GET(self):
        parts = re.split(r'/', self.path)
        if len(parts) < 6:
            self.send_response(400)
            self.response("error","incomplete")
            return
        empty, token, domain, subdomain, type, param = self.path.split('/')
        if token not in self.tokens:
            self.send_response(401)
            self.response("error","token required")
            return
        records = self.loadZone(self.dir+domain)
        if domain not in records or subdomain not in records[domain][type]:
            self.send_response(404)
            self.response("error","record not found")
            return
        if param == "update":
            with open(self.dir+domain, 'r') as file:
                zone = file.read()
            zone = re.sub(subdomain+'\t*[0-9]+\t*IN\t*'+type+'\t*'+records[domain][type][subdomain]['target'], subdomain+'\t300\tIN\t'+type+'\t'+self.client_address[0]+"\n", zone)
            with open(self.dir+domain, "w") as file:
                file.write(zone)

server = HTTPServer(('127.0.0.1', 8080), MyHandler)
try:
    server.serve_forever()
except KeyboardInterrupt:
    server.socket.close()
