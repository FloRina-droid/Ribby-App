# Ribby auf Koyeb hosten

Diese Version ist die bereinigte Koyeb-Web-App. Sie enthaelt nur die Dateien, die fuer das kostenlose Koyeb-Deployment gebraucht werden.

## Inhalt

```text
ribby_server.py   Python-Server und API
ribby_app.html    Ribby-App-Oberflaeche
Dockerfile        Container-Build fuer Koyeb
.env.example      Beispiel fuer Environment Variables
.dockerignore     Dateien, die nicht in den Container sollen
.gitignore        verhindert Upload von .env, Daten und Cachedateien
```

## 1. GitHub vorbereiten

1. Neues GitHub-Repository erstellen, z.B. `ribby`.
2. Den Inhalt dieses Ordners in das Repository hochladen.
3. `.env` nicht hochladen. Nutze `.env.example` nur als Vorlage.

## 2. Koyeb App erstellen

1. Bei Koyeb anmelden.
2. `Create App` waehlen.
3. GitHub-Repository verbinden.
4. Deployment-Methode: Dockerfile.
5. Service-Port: `7432`.

## 3. Environment Variables setzen

In Koyeb unter Environment Variables:

```text
RIBBY_PUBLIC_URL=https://DEINE-KOYEB-URL.koyeb.app
RIBBY_ADMIN_EMAIL=deine-mail@example.org
RIBBY_ADMIN_PASSWORD=ein-langes-zufaelliges-passwort
RIBBY_HOST=0.0.0.0
RIBBY_PORT=7432
RIBBY_DATA_DIR=/data/ribby_data
RIBBY_MAX_UPLOAD_MB=80
```

Nach dem ersten Login das Admin-Passwort in Ribby aendern.

## 4. Daten und Backups

Wenn Koyeb ein persistentes Volume fuer deine kostenlose Instanz erlaubt, mounte es auf:

```text
/data
```

Falls kein persistentes Volume aktiv ist, koennen Daten bei Redeploys verloren gehen. Dann regelmaessig in Ribby unter `Verwaltung -> Datenspeicherung` exportieren.

## 5. Link teilen

Nach erfolgreichem Deployment kannst du die Koyeb-HTTPS-URL verschicken. Nutzer brauchen dann von dir angelegte Login-Daten.

## Grenzen der kostenlosen Variante

- geeignet fuer Demo, Testbetrieb und kleine Nutzergruppen
- begrenzter Speicher fuer Audiodateien
- regelmaessige Backups sind wichtig
