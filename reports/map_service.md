# Ribby – Kartenalternative und Ausfallschutz

Stand: 21.10.2026. Ausgangscommit `dc29abf2918a43915b3e79480b82b46f8acbff1e`.

Als Standard-Kartenhintergrund verwendet Ribby jetzt [TopPlusOpen des BKG](https://gdz.bkg.bund.de/index.php/default/wmts-topplusopen-wmts-topplus-open.html), über den dort veröffentlichten WMTS-Endpunkt in Pseudo-Mercator. Das BKG bietet den Dienst ohne Entgelt unter dl-de/by-2-0 an. Der sichtbare Quellenvermerk enthält BKG, Bezugsjahr, Lizenz und den Link auf die Datenquellen. Die Kartendaten enthalten je nach Region auch OpenStreetMap-Daten; der Kacheldienst wird unabhängig vom bisherigen OSM-Server bereitgestellt.

Im Ausgangstest antworteten die zwölf angeforderten OSM-Kacheln mit HTTP 200. Ein dauerhafter Ausfall war zu diesem Zeitpunkt nicht reproduzierbar. Nachweisbar fehlte jedoch bei allen Kachelanfragen der Referer, weil das Gateway generell `Referrer-Policy: no-referrer` setzt. Dies entspricht nicht den [Anforderungen des OSM-Kacheldienstes](https://operations.osmfoundation.org/policies/tiles/) und kann zu Zugriffssperren führen. Eine solche Sperre wurde im Ausgangstest nicht als Ursache bewiesen.

Die Karte lädt jetzt zuerst BKG-Kacheln. Schlägt eine davon fehl, wird dieselbe Position genau einmal bei OpenStreetMap angefordert. Für Kartenbilder und die explizite Ortssuche gilt gezielt `strict-origin-when-cross-origin`: Extern wird ausschließlich der tatsächliche Ursprung der App übermittelt, kein URL-Pfad, kein Ticket, kein Sitzungsschlüssel. Die allgemeine Gateway-Regel bleibt bestehen. Beim Ausweichen ergänzt die Karte sichtbar die OSM-Namensnennung. Scheitern beide Dienste, bleiben GPS-Marker und Bedienelemente sichtbar; eine verständliche Fehlermeldung erscheint einmal pro Kartenansicht. Es gibt keine endlose Wiederholung.

Bestehende Marker, gespeicherte Daten, Zoom-Bedienung, Layout und Adminzugang wurden nicht verändert. Es wurde kein Nutzerkonto bei einem Kartendienst angelegt und kein API-Schlüssel benötigt.

## Prüfung

- Echter Edge-Browser über den bestehenden Toolbox-Adminzugang: 20 von 20 BKG-Kacheln geladen, Testmarker sichtbar, Zoom funktioniert.
- BKG-Aufrufe im Testbrowser absichtlich blockiert: 20 von 20 OSM-Ersatzkacheln geladen, Marker erhalten, Quellenvermerk ergänzt.
- Beide Dienste bei einer zuvor nicht geladenen Zoomstufe absichtlich blockiert: Ausfallmeldung sichtbar, Marker erhalten, keine Endlosschleife. Eine neue Zoomstufe verhindert, dass bereits geladene Browserbilder den Ausfalltest verdecken.
- Alle 36 im Ausweich- und Ausfalltest aufgezeichneten OSM-Anfragen enthielten den echten Ursprung `http://localhost:8095/` als Referer.
- Die echte Ortssuche nach Berlin funktioniert. Keine JavaScript-Laufzeitfehler.
- Automatischer Test `tests/test_map.cjs`: Kachel-URL und Zeilen-/Spaltenreihenfolge, Quellenlinks, Ausweichen, endgültiger Ausfall, Datumsgrenze, Marker, leere Ansicht und Identifikation bei der Ortssuche.
- Bestehende JavaScript-Syntax- und Bild-Ranking-Prüfungen bestanden.

Browserprotokoll und Screenshots mit einem ausschließlich temporären Testmarker liegen lokal unter `update_2026-10-21/map_fix`. Keine produktiven GPS-Punkte wurden hinzugefügt oder verändert. Die Verfügbarkeit externer Kartendienste bleibt von deren Betrieb und der Internetverbindung abhängig.
