#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/env.sh"
exec /usr/bin/python3 "$ROOT/scripts/follow_manage.py" "$@"
