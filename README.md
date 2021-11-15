# nsd-api
python3 webservice providing a simple API to change nsd nameserver records<br />

**Dependencies**<br />
simple_acme_dns

# Setup<br />
```
apt-get install python3 pip3 -y
adduser nsd-api --disabled-login
su nsd-api
cd; git clone https://github.com/Ne00n/nsd-api.git
pip3 install simple_acme_dns
cd nsd-api
```
Rename and edit the tokens in config.json
```
cp configs/config.example.json configs/config.json
cp configs/nsd-api.service /etc/systemd/system/
```
Give the nsd-api user permissions to modify the zones you want<br />
```
cd /etc/nsd/nsd.conf.d/
chgrp nsd-api domain.com
chmod 664 domain.com
```
Give the nsd-api user pemissions to reload nsd<br />
```
echo "nsd-api ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nsd" >> /etc/sudoers
```
Put Nginx or whatever you want in front as reverse proxy to provide TLS connections<br />
Don't forget to add:<br />
```
proxy_set_header X-Real-IP $remote_addr;
```
Because python3 http service can't speak duelstack<br />

#Nginx
Edit you must
```
cp /home/nsd-api/nsd-api/configs/nginx.example /etc/nginx/sites-enabled/nsd-api
systemctl restart nginx
```

#Systemd
```
cp /home/nsd-api/nsd-api/configs/nsd-api.service /etc/systemd/system/
systemctl enable nsd-api
systemctl start nsd-api
```

# Examples
**DynDNS**<br />
```
localhost:8080/mahkey/domain.net/lxd/A/update
v6.localhost:8080/mahkey/domain.net/lxd/AAAA/update
```
**Request Cert**<br />
```
curl localhost:8080/mahkey/domain.net/lxd/request/cert
```
**Add Record**<br />
```
localhost:8080/mahkey/domain.net/lxd/A/add/127.0.0.1
localhost:8080/mahkey/domain.net/lxd/AAAA/add/::1
```
**Delete Record**<br />
```
localhost:8080/mahkey/domain.net/lxd/A/delete
localhost:8080/mahkey/domain.net/lxd/AAAA/delete
```
