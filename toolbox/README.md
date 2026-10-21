# Ribby in der Naturgutachter Toolbox

Das Ribby-Logo wird als Favicon eingebettet. `ribby-logo.png` enthält dasselbe
Originalbild ohne Beschnitt oder Farbänderung als verlustfreie PNG-Datei für die Toolbox-Kachel.

Die zusätzliche Ribby-Anmeldung kann für eine bestehende, ausschließlich Admins
zugängliche Toolbox-Bereitstellung entfallen. Der normale eigenständige Start
behält seine bisherige Anmeldung.

## Interner Einstieg

Am Ribby-Server `RIBBY_TOOLBOX_AUTH=1` und
`RIBBY_TOOLBOX_SECRET_FILE=/run/ribby-toolbox/key` setzen. Die Schlüsseldatei muss
mindestens 64 Zeichen enthalten und ausschließlich dem App-Benutzer lesbar sein.
Denselben zufälligen Schlüssel über ein separates, nur lesbar eingebundenes
Volume auch dem Ribby-Gateway unter diesem Pfad bereitstellen. Schlüssel niemals
in Git, HTML, Browser-Speicher oder Protokolle übernehmen.

`ribby_gateway.py` ersetzt nur das Gateway des Ribby-Zugangs. Es verwendet die
vorhandenen Toolbox-Module, Datenbank und Sitzungen. Jeder Aufruf verlangt einen
aktiven Toolbox-Admin und die bestehende App-Berechtigung. Erst dann wird der
interne Schlüssel gesetzt; entsprechende Client-Header werden verworfen.
Der Ribby-Container darf keinen direkten Host-Port veröffentlichen.

`Dockerfile.gateway` ergänzt ein vorhandenes Toolbox-Gateway-Basisimage; dieses
kann über das Buildargument `TOOLBOX_GATEWAY_IMAGE` gewählt werden. Der Buildkontext
ist dieses Verzeichnis. Die übrige Toolbox bleibt unverändert.

Der Server verwendet die bestehende Ribby-Adminidentität für die vorhandenen
Daten und Referenzen. Die HTML-Datei aktiviert den direkten Einstieg nur bei
einer serverseitigen Toolbox-Freigabe. Die Datenschutzeinwilligung bleibt bestehen.
Abmelden widerruft die Toolbox-App-Sitzung und führt zur Toolbox zurück.

## Prüfung

`python -m unittest discover -s tests -p test_toolbox_auth.py` prüft den
Schlüsselzugriff, direkte und gefälschte Aufrufe, deaktivierten Passwort-Login
im Toolbox-Modus und die ausschließliche Ausgabe öffentlicher Profildaten.
Die übrigen Bild- und JavaScript-Prüfungen bleiben unverändert anwendbar.
