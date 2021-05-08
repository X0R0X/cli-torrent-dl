#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="$HOME/.torrent_dl/.venv"

# get path of this script, resolving all symlinks.
SOURCE="${BASH_SOURCE[0]}"
while [[ -h $SOURCE ]]; do
	SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" > /dev/null 2>&1 && pwd)"
	SOURCE="$(readlink "$SOURCE")"
	[[ $SOURCE = /* ]] || SOURCE="$SCRIPT_DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" > /dev/null 2>&1 && pwd)"

mkdir -p "$VENV_DIR"
virtualenv "$VENV_DIR"
. "$VENV_DIR/bin/activate"
pip3 install -r "$SCRIPT_DIR/requirements.txt"
