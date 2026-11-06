#!/usr/bin/env bash
# ffmpeg fuer die Videolaeufe ueber apt; haengt apt, die Ubuntu-Pakete eines frueheren Laufs aus dem GitHub-Cache.
# GEMESSEN 06.11.2026 (Business-Lauf 42200475499): apt hing 3x 240 s - auch auf dem Ubuntu-Hauptserver -,
# der Lauf fiel nach 13 Min. ohne Bau aus. Keine fremden Binaerdateien: nur die offiziellen Ubuntu-.deb,
# die ein erfolgreicher Lauf selbst geladen hat (Workflow: actions/cache auf ~/apt-debs).
# Schriften: Montserrat liegt im Projekt (bauen.SCHRIFT), fonts-dejavu-core ist nur Zugabe.
# CF_APT_AUS=1 ueberspringt apt (nur werkzeugprobe.yml, damit der Cache-Weg echt geprueft wird).
set -u
DEBS="$HOME/apt-debs"
NEU=/tmp/apt-debs
QUELLEN=/tmp/ubuntu-quellen
if [ "${CF_APT_AUS:-}" != "1" ]; then
  mkdir -p "$NEU/partial"
  ls /etc/apt/sources.list.d/
  for i in 1 2; do
    # Nur die Ubuntu-Quellen aktualisieren: die Zusatzquellen des Runners (Microsoft, Git LFS ...) braucht
    # ffmpeg nicht, und eine einzelne haengende Quelle blockiert sonst das ganze Update.
    rm -rf "$QUELLEN" && mkdir -p "$QUELLEN"
    cp /etc/apt/sources.list.d/ubuntu.sources "$QUELLEN"/ 2>/dev/null || cp /etc/apt/sources.list "$QUELLEN"/ubuntu.list
    timeout 240 sudo apt-get -o Acquire::Retries=3 -o Dir::Etc::sourcelist=/dev/null \
      -o Dir::Etc::sourceparts="$QUELLEN" update > /tmp/apt.log 2>&1 && \
    timeout 240 sudo apt-get -o Acquire::Retries=3 -o Dir::Cache::archives="$NEU" \
      -o APT::Keep-Downloaded-Packages=true install -y -qq ffmpeg fonts-dejavu-core >> /tmp/apt.log 2>&1 && \
    command -v ffmpeg && {
      # nur ein vollstaendiger Satz kommt in den Cache (ein leerer Ordner wird nicht gespeichert)
      if ls "$NEU"/*.deb > /dev/null 2>&1 && [ ! -d "$DEBS" ]; then
        mkdir -p "$DEBS" && sudo cp "$NEU"/*.deb "$DEBS"/ && sudo chown -R "$(id -u)" "$DEBS"
      fi
      exit 0
    }
    echo "apt-Versuch $i fehlgeschlagen:"
    tail -15 /tmp/apt.log
    # GEMESSEN 24.10.2026 (Lauf 40108829296): Azure-Spiegel hing; zweiter Versuch ueber den Ubuntu-Hauptserver.
    sudo sed -i 's#http://azure.archive.ubuntu.com#http://archive.ubuntu.com#g' \
      /etc/apt/sources.list /etc/apt/sources.list.d/*.sources 2>/dev/null || true
    sleep 10
  done
fi
if ls "$DEBS"/*.deb > /dev/null 2>&1; then
  echo "Ersatzweg: $(ls "$DEBS"/*.deb | wc -l) Ubuntu-Pakete aus dem GitHub-Cache"
  sudo dpkg -i "$DEBS"/*.deb > /dev/null 2>&1
  command -v ffmpeg && ffmpeg -hide_banner -version | head -1 && exit 0
fi
echo "ffmpeg nicht installierbar (apt haengt, kein Paket-Cache)"
exit 1
