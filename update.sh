#!/bin/bash
# Veranstaltungen Münsterland - Automatische Aktualisierung mit GitHub Push

cd "$(dirname "$0")"
LOGFILE="$(pwd)/launchd.log"
DATUM=$(date +%Y-%m-%d)

echo "=========================================="
echo "Aktualisierung gestartet: $(date)"
echo "=========================================="

# Alte Event-Anzahl aus bestehenden HTML-Dateien auslesen
ALTE_ANZAHL=0
for html in veranstaltungen_*.html; do
    if [ -f "$html" ]; then
        # Extrahiere "<span id="termine-count">XXX</span>" aus HTML
        ANZAHL=$(grep -o '<span id="termine-count">[0-9]*</span>' "$html" | grep -o '[0-9]*' | head -1)
        ALTE_ANZAHL=$((ALTE_ANZAHL + ANZAHL))
    fi
done

# Veranstaltungen abrufen
OUTPUT=$(/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 app.py --no-browser 2>&1)
echo "$OUTPUT"

# Prüfe auf Fehler (Timeouts, Connection-Errors)
FEHLER_COUNT=$(echo "$OUTPUT" | grep -c "Fehler beim Abrufen")

# Neue Event-Anzahl aus Output extrahieren (z.B. "→ 467 Veranstaltungen")
NEUE_ANZAHL=0
while IFS= read -r line; do
    ANZAHL=$(echo "$line" | grep -o '[0-9]* Veranstaltungen' | grep -o '[0-9]*' | head -1)
    if [ -n "$ANZAHL" ]; then
        NEUE_ANZAHL=$((NEUE_ANZAHL + ANZAHL))
    fi
done <<< "$OUTPUT"

# Differenz berechnen
DIFF=$((NEUE_ANZAHL - ALTE_ANZAHL))

# Alte Monatsdateien aufräumen (Puffer: Vormonat bleibt, alles davor wird gelöscht)
CUTOFF_JAHR=$(date +%Y)
CUTOFF_MONAT=$(date +%-m)
if [ "$CUTOFF_MONAT" -eq 1 ]; then
    CUTOFF_JAHR=$((CUTOFF_JAHR - 1))
    CUTOFF_MONAT=12
else
    CUTOFF_MONAT=$((CUTOFF_MONAT - 1))
fi
CUTOFF=$(printf "%04d_%02d" "$CUTOFF_JAHR" "$CUTOFF_MONAT")
GELOESCHT=()
for html in veranstaltungen_*.html; do
    [ -f "$html" ] || continue
    DATEI_KEY=$(echo "$html" | grep -o '[0-9]\{4\}_[0-9]\{2\}')
    if [[ "$DATEI_KEY" < "$CUTOFF" ]]; then
        echo "Lösche veraltete Datei: $html (älter als Vormonat)"
        git rm "$html" 2>/dev/null && GELOESCHT+=("$html")
    fi
done

# Zu GitHub pushen (nur wenn Änderungen vorhanden)
PUSH_STATUS=""
HAT_AENDERUNGEN=false
git diff --quiet veranstaltungen_*.html 2>/dev/null || HAT_AENDERUNGEN=true
[ -n "$(git ls-files -o --exclude-standard veranstaltungen_*.html 2>/dev/null)" ] && HAT_AENDERUNGEN=true
git diff --cached --quiet 2>/dev/null || HAT_AENDERUNGEN=true

if [ "$HAT_AENDERUNGEN" = false ]; then
    echo "Keine Änderungen - kein Push nötig"
    PUSH_STATUS="Keine Änderungen"
else
    echo "Änderungen gefunden - pushe zu GitHub..."
    git add veranstaltungen_*.html index.html 2>/dev/null
    COMMIT_MSG="Veranstaltungen aktualisiert $DATUM"
    [ ${#GELOESCHT[@]} -gt 0 ] && COMMIT_MSG="$COMMIT_MSG (${#GELOESCHT[@]} alte Datei(en) gelöscht)"
    git commit -m "$COMMIT_MSG" 2>&1

    # Rebase auf Remote-Stand, falls divergiert (generierte HTML → kein Merge-Risiko)
    git pull --rebase 2>&1

    if git push 2>&1; then
        echo "Push erfolgreich!"
        PUSH_STATUS="GitHub aktualisiert"
    else
        echo "Push fehlgeschlagen!"
        PUSH_STATUS="Push fehlgeschlagen!"
    fi
fi

# Benachrichtigungs-Text erstellen
if [ $FEHLER_COUNT -gt 0 ]; then
    TITEL="⚠️ Update mit Fehlern"
    TEXT="$NEUE_ANZAHL Events (${FEHLER_COUNT}× Timeout)"
    SOUND="Basso"
elif [ $DIFF -gt 0 ]; then
    TITEL="✅ Veranstaltungen aktualisiert"
    TEXT="$NEUE_ANZAHL Events (+${DIFF} neu)"
    SOUND="Glass"
elif [ $DIFF -lt 0 ]; then
    TITEL="✅ Veranstaltungen aktualisiert"
    TEXT="$NEUE_ANZAHL Events (${DIFF} weniger)"
    SOUND="Glass"
else
    TITEL="✅ Veranstaltungen aktualisiert"
    TEXT="$NEUE_ANZAHL Events (unverändert)"
    SOUND="Glass"
fi

# Push-Status anhängen
if [ -n "$PUSH_STATUS" ]; then
    TEXT="$TEXT | $PUSH_STATUS"
fi

# Gelöschte Dateien anhängen
if [ ${#GELOESCHT[@]} -gt 0 ]; then
    TEXT="$TEXT | 🗑 ${#GELOESCHT[@]} alte Datei(en) gelöscht"
fi

# Klickbare macOS Benachrichtigung mit terminal-notifier
/opt/homebrew/bin/terminal-notifier \
    -title "$TITEL" \
    -subtitle "Veranstaltungen Münsterland" \
    -message "$TEXT - Klicke zum Log" \
    -sound "$SOUND" \
    -execute "osascript -e 'tell application \"Terminal\" to do script \"tail -30 \\\"$LOGFILE\\\"\"'"

echo ""
echo "Fertig: $(date)"
