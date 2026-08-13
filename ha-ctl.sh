#!/usr/bin/env bash
# --------------------------------------------------------------------------------------------------
# ha-ctl.sh — kis segédeszköz a docker dev/teszt HA REST API-jának szkriptelt hívásához
# (pl. entitás-állapot szimulálása: unavailable/available, ld. SPEC.md B2.1b/B4/15 tesztelése).
#
# Használat:
#   ./ha-ctl.sh --token                                     token beolvasása és mentése (.ha-ctl.env)
#   ./ha-ctl.sh --set --entity <entity_id> --state <state>  állapot beállítása
#   ./ha-ctl.sh --get --entity <entity_id> [--state]        állapot lekérdezése
#                                                            (--state: csak az állapot-mező, nem a teljes JSON)
#
# Env:
#   HA_URL   HA API alap URL (alapértelmezett: http://localhost:8123 — a konténer
#            network_mode: host-tal fut, a hostról közvetlenül elérhető, ld. CLAUDE.md 10.)
#
# A token SOHA nem kerül parancssori argumentumba/git-be — a --token interaktívan (rejtett
# beolvasással) kéri, és a .ha-ctl.env fájlba menti (600 jogosultsággal, .gitignore-olva).
# --------------------------------------------------------------------------------------------------
set -euo pipefail

HA_URL="${HA_URL:-http://localhost:8123}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.ha-ctl.env"

usage() {
  sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

load_token() {
  if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
  fi
  if [[ -z "${HA_TOKEN:-}" ]]; then
    echo "Nincs mentett token. Futtasd előbb: ./ha-ctl.sh --token" >&2
    exit 1
  fi
}

cmd_token() {
  echo "Hozz létre egy 'Hosszú élettartamú hozzáférési token'-t a HA-ban, ha még nincs:" >&2
  echo "  Profil (bal alsó felhasználó-ikon) -> legalul 'Hosszú élettartamú hozzáférési tokenek' -> 'Token létrehozása'" >&2
  echo >&2
  read -rsp "Illeszd be a tokent (nem jelenik meg a képernyőn): " token
  echo >&2
  if [[ -z "$token" ]]; then
    echo "Üres token, megszakítva." >&2
    exit 1
  fi
  printf 'HA_TOKEN=%q\n' "$token" > "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "Elmentve: $ENV_FILE (jogosultság: 600)"
}

json_string() {
  python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"
}

format_json() {
  python3 -m json.tool 2>/dev/null || cat
}

cmd_set() {
  local entity="" state=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --entity) entity="$2"; shift 2 ;;
      --state) state="$2"; shift 2 ;;
      *) echo "Ismeretlen kapcsoló: $1" >&2; usage; exit 1 ;;
    esac
  done
  [[ -n "$entity" && -n "$state" ]] || { echo "Kell: --entity <entity_id> --state <state>" >&2; exit 1; }
  load_token
  curl -sS -X POST \
    -H "Authorization: Bearer $HA_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"state\": $(json_string "$state")}" \
    "$HA_URL/api/states/$entity" | format_json
}

cmd_get() {
  local entity="" only_state=0
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --entity) entity="$2"; shift 2 ;;
      --state) only_state=1; shift ;;
      *) echo "Ismeretlen kapcsoló: $1" >&2; usage; exit 1 ;;
    esac
  done
  [[ -n "$entity" ]] || { echo "Kell: --entity <entity_id>" >&2; exit 1; }
  load_token
  local resp
  resp="$(curl -sS -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/$entity")"
  if [[ "$only_state" -eq 1 ]]; then
    echo "$resp" | python3 -c 'import json,sys; print(json.load(sys.stdin)["state"])'
  else
    echo "$resp" | format_json
  fi
}

case "${1:-}" in
  --token) shift; cmd_token "$@" ;;
  --set) shift; cmd_set "$@" ;;
  --get) shift; cmd_get "$@" ;;
  -h|--help|"") usage ;;
  *) echo "Ismeretlen parancs: $1" >&2; usage; exit 1 ;;
esac
# --------------------------------------------------------------------------------------------------
# EOF
# --------------------------------------------------------------------------------------------------
