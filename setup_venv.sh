#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/torrentdl/.venv"

if [[ -d $VENV_DIR ]]; then
	while true; do
		read -p 'Delete and re-install virtualenv? [y/N]: ' choice
		# Convert $choice to lowercase to keep things clean.
		case "${choice,,}" in
			'y')
				rm -rf "$VENV_DIR"
				# Now we can proceed.
				break
			;;
			''|'n')
				exit
			;;
		esac
	done
# Not sure how this would happen.
# Maybe corruption or an accidental overwrite?
# Might as well plan for the worst.
else if [[ -e $VENV_DIR ]]; then
	     printf '%s\n' 'Broken virtualenv detected. Reinstalling...'
	     # Backup old venv in case it's still of some value.
	     # Won't overwrite files.
	     mv --backup=numbered "$VENV_DIR"{,.bak}
	     printf '%s %s\n\n' 'Created backup of virtualenv at' "$VENV_DIR.bak"
     fi
fi

# Get path of this script, resolving all symlinks.
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
