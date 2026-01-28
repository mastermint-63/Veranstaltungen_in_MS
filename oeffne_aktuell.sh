#!/bin/bash
# Öffnet die Veranstaltungen des aktuellen Monats im Browser
JAHR=$(date +%Y)
MONAT=$(date +%m)
open "/Users/fs/claude/Veranstaltungen_in_MS/veranstaltungen_${JAHR}_${MONAT}.html"
