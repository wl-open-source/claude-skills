# Deployment: Docker-Compose-App auf den Server bringen

## App-Layout auf dem Server

```
/srv/apps/<APP>/
├── compose.yaml
└── .env          # Secrets + IMAGE_TAG, chmod 600, NIE ins Git
```

Einmalig pro App anlegen:

```bash
sudo mkdir -p /srv/apps/<APP> && sudo chown deploy:deploy /srv/apps/<APP>
```

Beispiel `compose.yaml` (FastAPI + PostgreSQL):

```yaml
services:
  app:
    image: ghcr.io/<GITHUB_USER>/<APP>:${IMAGE_TAG:-latest}
    restart: unless-stopped
    env_file: .env
    depends_on: [db]
    networks:
      default:
      web:
        aliases: [<APP>]   # eindeutiger Name im web-Netz = Caddy-Target
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - db_data:/var/lib/postgresql/data
volumes:
  db_data:
networks:
  web:
    external: true
```

Wichtig: Nur `app` hängt im `web`-Netz und ist dort unter dem Alias
`<APP>` erreichbar — genau diesen Namen nutzt der Caddyfile-Block
(`reverse_proxy <APP>:8000`). `db` hat keinen `networks:`-Eintrag und
landet damit nur im projektinternen Default-Netz — von Caddy und von
außen nicht erreichbar. Keine `ports:` am App-Container — Caddy ist der
einzige Eingang.

## Deploy-Ablauf

```bash
ssh deploy@<SERVER_IP>
cd /srv/apps/<APP>
# 1. Aktuellen Stand für Rollback merken:
grep IMAGE_TAG .env   # alten Tag notieren
# 2. Neuen Tag setzen (oder git pull bei Build auf dem Server):
sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=<NEUER_TAG>/' .env
docker compose pull
docker compose up -d
# 3. Health-Check:
docker compose ps
docker compose logs --tail 30 app
curl -fsS https://<DOMAIN>/health || echo "FEHLER: App antwortet nicht"
```

## Rollback — sofort, ohne Diskussion

```bash
sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=<ALTER_TAG>/' .env
docker compose up -d
curl -fsS https://<DOMAIN>/health
```

Deshalb: **immer mit Versions-Tags deployen, nie nur `latest`** —
`latest` kann man nicht zurückrollen.

## Caddy an neue App anbinden

Block in `/srv/caddy/Caddyfile` ergänzen, dann:

```bash
cd /srv/caddy && docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```
