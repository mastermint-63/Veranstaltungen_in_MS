#!/bin/bash
# Öffnet die Veranstaltungen des aktuellen Monats im Browser
cd "$(dirname "$0")"
JAHR=$(date +%Y)
MONAT=$(date +%m)
open "veranstaltungen_${JAHR}_${MONAT}.html"
