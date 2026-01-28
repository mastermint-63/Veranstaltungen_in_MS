#!/bin/bash
# Veranstaltungen Münsterland - Automatische Aktualisierung

cd "$(dirname "$0")"

# Veranstaltungen abrufen
OUTPUT=$(/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 app.py --no-browser 2>&1)

# Anzahl Dateien aus Output extrahieren
DATEIEN=$(echo "$OUTPUT" | grep -o '[0-9]* Dateien generiert' | grep -o '[0-9]*')

# macOS Benachrichtigung anzeigen
osascript -e "display notification \"$DATEIEN Monate aktualisiert\" with title \"Veranstaltungen Münsterland\" sound name \"Glass\""

echo "Aktualisiert: $(date)"
echo "$OUTPUT"
