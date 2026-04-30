# HTTPS-Setup via Cloudflare Origin Certificate

Diese Anleitung zeigt wie man SysIntro hinter Cloudflare mit echtem End-to-End-TLS betreibt — komplett ohne certbot, ohne Auto-Renewal-Ärger, mit einem 15-Jahre-Cert von Cloudflare.

## Architektur

```
Browser  ──HTTPS──►  Cloudflare Edge  ──HTTPS──►  nginx (Port 443)  ──HTTP──►  uvicorn (127.0.0.1:8080)
            ↑                  ↑                            ↑
            └ CF Edge-Cert     └ Cloudflare TLS-Term.       └ CF Origin-Cert (von dir installiert)
```

- Browser ↔ Cloudflare: TLS mit CF-Edge-Zertifikat (von CF automatisch)
- Cloudflare ↔ Origin: TLS mit Cloudflare Origin Certificate (15 Jahre, von dir installiert)
- nginx ↔ uvicorn: HTTP auf localhost (kein TLS nötig, single-host)

## Voraussetzung

- Domain läuft über Cloudflare (DNS in CF, „orange cloud" / proxied)
- A-Record zeigt auf den Server (z. B. `sep.deinedomain.de` → `<Server-IP>`)
- SysIntro läuft bereits via `bash deploy/install.sh`

## Schritt 1 — Cloudflare Origin Certificate erstellen

1. https://dash.cloudflare.com → deine Domain auswählen
2. **SSL/TLS → Origin Server → Create Certificate**
3. Defaults verwenden:
   - **Private key type:** RSA (2048) — kompatibel mit allem; ECC alternativ
   - **Hostnames:** `*.deinedomain.de` und `deinedomain.de` (Wildcard deckt Subdomains ab)
   - **Validity:** 15 years
4. Klick **Create**
5. Cloudflare zeigt:
   - **Origin Certificate** (kopieren — beginnt mit `-----BEGIN CERTIFICATE-----`)
   - **Private Key** (kopieren — beginnt mit `-----BEGIN PRIVATE KEY-----`)

⚠️ **Den Private Key zeigt CF nur jetzt einmal an.** Wenn die Seite verlassen wird ohne zu kopieren, muss das Cert neu erstellt werden.

## Schritt 2 — Cert + Key auf den Server kopieren

Auf dem Server:

```bash
sudo install -d -m 700 -o root -g root /etc/nginx/ssl
sudo nano /etc/nginx/ssl/origin.pem  # Cert einfügen
sudo nano /etc/nginx/ssl/origin.key  # Private Key einfügen
sudo chmod 644 /etc/nginx/ssl/origin.pem
sudo chmod 600 /etc/nginx/ssl/origin.key
```

## Schritt 3 — nginx-Config erweitern

Die Datei `/etc/nginx/sites-available/sysintro` enthält bereits den Port-80-Block. Den Redirect aktivieren UND einen 443-Block dazu:

```bash
sudo nano /etc/nginx/sites-available/sysintro
```

a) Im Port-80-Block: das auskommentierte `return 301` aktivieren:

```nginx
if ($http_x_forwarded_proto != "https") {
    return 301 https://$host$request_uri;       # ← Kommentar entfernen
}
```

b) Am Ende der Datei den HTTPS-Block ergänzen:

```nginx
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name sep.deinedomain.de;

    client_max_body_size 25m;

    ssl_certificate     /etc/nginx/ssl/origin.pem;
    ssl_certificate_key /etc/nginx/ssl/origin.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305';
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    # Same security headers as port 80
    add_header X-Content-Type-Options  "nosniff"                           always;
    add_header X-Frame-Options         "DENY"                              always;
    add_header Referrer-Policy         "strict-origin-when-cross-origin"   always;
    add_header Permissions-Policy      "geolocation=(), microphone=(), camera=()" always;
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://cdn.tailwindcss.com https://unpkg.com 'unsafe-inline'; style-src 'self' https://cdn.tailwindcss.com 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'" always;

    location /static/ {
        alias /opt/sysintro/app/app/static/;
        expires 1d;
        add_header Cache-Control "public, max-age=86400";
    }

    location / {
        proxy_pass         http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto https;
        proxy_set_header   CF-Connecting-IP  $http_cf_connecting_ip;
        proxy_connect_timeout 60s;
        proxy_send_timeout    60s;
        proxy_read_timeout    60s;
        proxy_set_header   Upgrade    $http_upgrade;
        proxy_set_header   Connection "upgrade";
    }
}
```

Validieren + Reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Schritt 4 — `SECURE_COOKIES=1` setzen

```bash
sudo sed -i 's/^SECURE_COOKIES=0/SECURE_COOKIES=1/' /opt/sysintro/.env
sudo systemctl restart sysintro
```

Jetzt setzt die App das `Secure`-Flag auf allen Cookies — Browser senden sie nur noch über HTTPS.

## Schritt 5 — Cloudflare-Modus auf „Full (strict)" stellen

**Das ist der entscheidende Schritt** — wenn ihn jemand vergisst, läuft Browser-zu-Cloudflare zwar verschlüsselt, aber Cloudflare-zu-Origin entweder gar nicht (Mode „Off") oder unverschlüsselt (Mode „Flexible"):

1. Cloudflare Dashboard → Domain auswählen
2. **SSL/TLS → Overview**
3. Encryption mode: **Full (strict)**

Optional ergänzend:
- **SSL/TLS → Edge Certificates → Always Use HTTPS = ON** (CF redirectet jeden HTTP-Request am Edge auf HTTPS)
- **SSL/TLS → Edge Certificates → Minimum TLS Version = 1.2**
- **SSL/TLS → Edge Certificates → HTTP Strict Transport Security (HSTS)** aktivieren (max-age 12 Monate, include subdomains)

## Verifikation

```bash
# Lokal auf dem Server
curl -ks --resolve <DOMAIN>:443:127.0.0.1 https://<DOMAIN>/login -o /dev/null -w '%{http_code}\n'
# erwartet: 200

# Cert-Chain prüfen
echo | openssl s_client -connect 127.0.0.1:443 -servername <DOMAIN> 2>/dev/null | openssl x509 -noout -subject -issuer -dates
# subject sollte "CloudFlare Origin Certificate" sein
```

Von außen:

```bash
curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://<DOMAIN>/login   # erwartet: 301 → HTTPS
curl -s -o /dev/null -w 'HTTP %{http_code}\n' https://<DOMAIN>/login  # erwartet: 200
```

Browser:
- `https://<DOMAIN>` → grünes Schloss, „Verbindung sicher"
- Cert-Details: ausgestellt von Cloudflare Inc. (am Edge)
- HTTP-URLs werden via 301/307 automatisch auf HTTPS umgeleitet

## Wichtige Punkte / Fallstricke

| Cloudflare-Mode | Browser↔CF | CF↔Origin | Nutzbar? |
|---|---|---|---|
| Off | HTTP | HTTP | ⚠️ kein HTTPS |
| Flexible | HTTPS | HTTP | ⚠️ MITM-Risiko zwischen CF und Origin |
| Full | HTTPS | HTTPS (jeder Cert) | ⚠️ akzeptiert auch falsche/abgelaufene Origin-Certs |
| **Full (strict)** | HTTPS | HTTPS (validiert Cert) | ✅ **gewünscht** |

- Loop-Schutz: `if ($http_x_forwarded_proto != "https")` verhindert Endlos-Redirects im Übergang von „Flexible" zu „Full strict"
- Cloudflare Origin Cert ist ungültig für Browser-Direktzugriff — er ist nur von Cloudflare-IPs aus vertrauenswürdig (Browser kennen die CF-Origin-CA nicht). Das ist Absicht.
- Renewal in 15 Jahren — kein Cron-Job nötig

## Troubleshooting

### Browser zeigt „Error 525" oder „SSL handshake failed"

- CF kann den Origin-Cert nicht validieren
- Prüfe: Cert in `/etc/nginx/ssl/origin.pem` korrekt? Pfad in nginx-Config?
- Prüfe: `nginx -t` syntax ok?
- Prüfe: `openssl s_client -connect <SERVER-IP>:443 -servername <DOMAIN>` zeigt das richtige Cert?

### Browser zeigt 502 Bad Gateway

- nginx läuft, aber kann zu uvicorn nicht durchschalten
- Prüfe: `systemctl status sysintro`
- Prüfe: `journalctl -u sysintro -n 30`

### Endlos-Redirect (ERR_TOO_MANY_REDIRECTS)

- Cloudflare im Modus „Flexible" UND nginx-Redirect aktiv ohne XFP-Guard
- Lösung: entweder CF auf „Full (strict)" oder nginx-Config mit dem `if ($http_x_forwarded_proto != "https")`-Guard wie oben
