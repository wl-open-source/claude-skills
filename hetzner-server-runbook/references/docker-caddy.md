# Docker + Caddy Reverse Proxy (Auto-HTTPS)

Als `deploy@<SERVER_IP>`.

## 1. Docker installieren (offizielles Apt-Repo)

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker deploy
# neu einloggen, dann:
docker run --rm hello-world
```

## 2. Gemeinsames Netz + Caddy

```bash
docker network create web
sudo mkdir -p /srv/caddy && sudo chown deploy:deploy /srv/caddy
```

`/srv/caddy/compose.yaml`:

```yaml
services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports: ["80:80", "443:443"]
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    networks: [web]
volumes:
  caddy_data:
  caddy_config:
networks:
  web:
    external: true
```

Hinweis: Es wird bewusst nur TCP gemappt — HTTP/3 (QUIC, 443/udp) ist
nicht konfiguriert; HTTP/1.1 und HTTP/2 decken alles ab.

`/srv/caddy/Caddyfile` (pro App ein Block; `<APP>` = Netz-Alias des App-Containers im `web`-Netz, siehe `deployment.md`):

```
<DOMAIN> {
    reverse_proxy <APP>:8000
}
```

Ohne eigene Domain (Tests): `<SERVER_IP mit Bindestrichen>.sslip.io`,
z. B. `203-0-113-10.sslip.io` — löst automatisch auf die IP auf,
Caddy holt dafür ein echtes Zertifikat.

```bash
cd /srv/caddy && docker compose up -d
```

## 3. Verifikation

```bash
docker compose -f /srv/caddy/compose.yaml ps   # caddy: running
curl -sI http://localhost | head -1            # HTTP-Antwort von Caddy
curl -sI -H "Host: <DOMAIN>" http://localhost | head -1   # trifft der Site-Block?
```

Config-Änderungen laden: `docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile`
