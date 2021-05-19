#!/usr/bin/env bash
PS1B=$PS1

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
elif [[ -e $VENV_DIR ]]; then
	printf '%s\n' 'Broken virtualenv detected. Reinstalling...'
	# Backup old venv in case it's still of some value.
	# Won't overwrite existing files.
	mv --backup=numbered "$VENV_DIR"{,.bak}
	printf '%s %s\n\n' 'Created backup of virtualenv at' "$VENV_DIR.bak"
fi

# Get path of this script, resolving all symlinks.
SOURCE="${BASH_SOURCE[0]}"
while [[ -h $SOURCE ]]; do
	SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" > /dev/null 2>&1 && pwd)"
	SOURCE="$(readlink "$SOURCE")"
	[[ $SOURCE = /* ]] || SOURCE="$SCRIPT_DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" > /dev/null 2>&1 && pwd)"

PYTHON_VERSION=$(python3 -V | awk '{print $2}' | sed 's/\.//g')
PYTHON_VERSION=${PYTHON_VERSION:0:2}

if [ $PYTHON_VERSION == "38" ] || [ $PYTHON_VERSION == "39" ]; then
  PYTHON_BIN="python3"
else
  if [ "$(which python3.8)" != "" ]; then
    PYTHON_BIN="python3.8"
  else
    if [ "$(which python3.9)" != "" ]; then
      PYTHON_BIN="python3.9"
    else
      echo "Tordl needs python3.8 or python3.9 installed. Please install it (on debian based systems: \$ sudo apt-get install python3.8)"
      exit 1
    fi
  fi
fi

virtualenv -p $PYTHON_BIN "$VENV_DIR"
PS1=$PS1B

. "$VENV_DIR/bin/activate"
pip3 install -r "$SCRIPT_DIR/requirements.txt"

while true; do
  read -p 'Do You want to link tordl.sh to /usr/local/bin/tordl ? [y/N]: ' choice
	# Convert $choice to lowercase to keep things clean.
	case "${choice,,}" in
		'y')
		  if [[ -d $VENV_DIR ]]; then
		    echo "Deleting current /usr/local/bin/tordl ..."
		    sudo rm /usr/local/bin/tordl
		  fi

			sudo ln -s "$SCRIPT_DIR/tordl.sh" /usr/local/bin/tordl
			# Now we can proceed.
			break
		;;
		''|'n')
			exit 0
		;;
	esac
done
