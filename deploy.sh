#!/usr/bin/env bash
# --------------------------------------------------------------------------------------------------
# deploy.sh — a custom_components/timed_switch preview deployolása a docker dev/teszt HA-ba.
#
# A host /mnt/3-Data/docker.data/home-assistant root-tulajdonú (a "homeassistant" docker
# container /config mountja), a hívó user nincs benne a "root" csoportban — ezért NEM sima
# rsync-kel írunk a host útvonalra, hanem a docker daemonon (a hívó "docker" csoporttagsága
# elég hozzá, sudo nélkül) keresztül, `docker exec`/`docker cp`-vel, ami a konténerben root-
# ként fut.
#
# Minden deploynál emeli a build-számot (feedback_version_bump_convention memória:
# v1.0.0000 -> v1.0.0001), a manifest.json "version" mezőjét is frissíti, és alapértelmezetten
# újraindítja a "homeassistant" konténert, majd kiírja a friss logot.
#
# Használat:
#   ./deploy.sh              # verzió emelés + deploy + restart + log
#   ./deploy.sh --no-restart # csak deploy + verzió emelés, konténer-restart nélkül
# --------------------------------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/custom_components/timed_switch"
VERSION_FILE="$SCRIPT_DIR/VERSION"
MANIFEST="$SRC_DIR/manifest.json"
CONTAINER="homeassistant"
DEST_IN_CONTAINER="/config/custom_components/timed_switch"

RESTART=1
if [[ "${1:-}" == "--no-restart" ]]; then
  RESTART=0
fi

# --- verziószám emelés (build szám: utolsó szegmens, 4 számjegyre paddelve) -----------------------
current="$(cat "$VERSION_FILE")"
major_minor="${current%.*}"
build="${current##*.}"
new_build="$(printf "%04d" $((10#$build + 1)))"
new_version="${major_minor}.${new_build}"
echo "$new_version" > "$VERSION_FILE"

python3 - "$MANIFEST" "$new_version" <<'PYEOF'
import json
import sys

path, version = sys.argv[1], sys.argv[2]
with open(path) as f:
    data = json.load(f)
data["version"] = version
with open(path, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
PYEOF

echo "== Verzió: $new_version =="

# --- deploy a docker daemonon keresztül (root a konténerben, sudo nélkül a hoston) -----------------
find "$SRC_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

docker exec "$CONTAINER" rm -rf "$DEST_IN_CONTAINER"
docker cp "$SRC_DIR" "$CONTAINER:$DEST_IN_CONTAINER"
echo "== Deployolva: $CONTAINER:$DEST_IN_CONTAINER =="

if [[ "$RESTART" -eq 1 ]]; then

	echo "== Konténer újraindítása: $CONTAINER =="
	docker restart "$CONTAINER" >/dev/null
	echo "== Várakozás az induláshoz... =="

	for _ in $(seq 1 30); do

		sleep 2

		if docker logs --tail 5 "$CONTAINER" 2>&1 | grep -q "Home Assistant"; then
			break
		fi
	done

	sleep 3
	echo "== Friss log (utolsó 80 sor) =="
	docker logs --tail 80 "$CONTAINER"
else
	echo "== --no-restart: a konténer nem lett újraindítva, a régi kód fut még memóriában =="
fi
# --------------------------------------------------------------------------------------------------
# EOF
# --------------------------------------------------------------------------------------------------
