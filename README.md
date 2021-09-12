# nsd-api
python3 webservice providing a simple API to change nsd nameserver records<br />
# Setup<br />
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
# Examples
**DynDNS**<br />
```
localhost:8080/mahkey/domain.net/lxd/A/update
localhost:8080/mahkey/domain.net/lxd/AAAA/update
```
Put Nginx or whatever you want in front as reverse proxy to provide TLS connections<br />
Don't forget to add:<br />
```
proxy_set_header X-Real-IP $remote_addr;
```
Because python3 http service can't speak duelstack<br />
