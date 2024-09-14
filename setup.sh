#!/usr/bin/env bash

PS1B=$PS1

set -euo pipefail

C_RED="\033[0;31m"
C_GREEN="\033[0;32m"
C_YEllOW="\033[1;33m"
C_NONE="\033[0m"

# Get path of this script, resolving all symlinks.
SOURCE="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" > /dev/null 2>&1 && pwd)"
LN_CMD=('ln' '-sf' "$SCRIPT_DIR/tordl.sh")
CMD_BIN_PATH="$HOME/.local/bin"

while [[ -h $SOURCE ]]; do
	SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" > /dev/null 2>&1 && pwd)"
	SOURCE="$(readlink "$SOURCE")"
	[[ $SOURCE = /* ]] || SOURCE="$SCRIPT_DIR/$SOURCE"
done

if [[ $PATH =~ "$CMD_BIN_PATH" ]]; then
	if [ ! -d "$CMD_BIN_PATH" ]; then
	  printf "${C_YEllOW}You Have $CMD_BIN_PATH in your PATH environment variable but directory does not exist. We will create it.${C_NONE}\n"
	  mkdir "$CMD_BIN_PATH"
  fi
  BIN_DIR="$HOME/.local/bin/tordl"
	LN_CMD+=("$BIN_DIR")
	BIN_DIR_SUDO=0
else
  BIN_DIR='/usr/local/bin/tordl'
	LN_CMD=('sudo' "${LN_CMD[@]}" "$BIN_DIR")
  BIN_DIR_SUDO=1
fi


XDG_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/torrentdl"
VENV_DIR="$XDG_CONFIG_DIR/.venv"
PYTHON_LATEST_VERSION=12
PYTHON_MIN_VERSION=8
PYTHON_DEFAULT_VERSION="$(python3 -V | tr -d '[A-Za-z]' | awk -F . '{print $2}')"
UNINSTALL=0
TORDL_BIN_PATH="${LN_CMD[${#LN_CMD[@]}-1]}"

function print_help {
    printf "${C_GREEN}-h   | --help${C_NONE}      : Print this help\n"
    printf "${C_GREEN}-p=* | --python=*${C_NONE}  : Use specific python3 minor version (8,9,10,11) [example: setup.sh -p=11]\n"
    printf "${C_GREEN}-u   | --uninstall${C_NONE} : Uninstall tordl from the System\n [example: setup.sh -u]"
}

for i in "$@"; do
  case $i in
    -p=*|--python=*)
      PYTHON_DEFAULT_VERSION=""
      PYTHON_LATEST_VERSION="${i#*=}"
      if [[ -z $(which "python3.$PYTHON_LATEST_VERSION") ]]; then
        printf "${C_RED}User set python3.$PYTHON_LATEST_VERSION not found on the System${C_NONE}"
        exit 1
      fi
      ;;
    -u|--uninstall)
      UNINSTALL=1
      ;;
    -h|--help)
      print_help
      exit 0
      ;;
    *)
      echo "Unknown Argument $i"
      exit 1
      ;;
   esac
done

# Uninstall tordl from the System
if (( $UNINSTALL == 1 )); then
  printf "${C_GREEN}Uninstalling tordl from the System...${C_NONE}\n"

  echo "Removing $XDG_CONFIG_DIR..."
  if [[ -e $XDG_CONFIG_DIR ]]; then
    rm -rf "$XDG_CONFIG_DIR"
    printf "${C_GREEN}${XDG_CONFIG_DIR} Removed ${C_NONE}\n"
  else
    printf "${C_RED}Unable to remove Config Dir $XDG_CONFIG_DIR, does not exist${C_NONE}\n"
  fi

  `echo` "Removing Binary Link $TORDL_BIN_PATH..."
  if [[ -e $TORDL_BIN_PATH ]]; then
    if (( "$BIN_DIR_SUDO" == 0 )); then
      rm $TORDL_BIN_PATH
    printf "${C_GREEN}${TORDL_BIN_PATH} Removed ${C_NONE}\n"
    else
      sudo rm $TORDL_BIN_PATH
    fi
  else
    printf "${C_RED}Unable to remove tordl bin Link $TORDL_BIN_PATH, does not exist${C_NONE}\n"
  fi

  exit 0
fi

printf ${C_GREEN}
if [[ -z "$PYTHON_DEFAULT_VERSION" ]]; then
  printf "Using Python Version 3.$PYTHON_LATEST_VERSION\n"
else
  printf "Using Python Version 3.$PYTHON_DEFAULT_VERSION\n"
fi
printf ${C_NONE}

if [[ -d $VENV_DIR ]]; then
	while true; do
	    printf ${C_GREEN}
		read -p 'Delete and re-install virtualenv? [y/N]: ' choice
		printf ${C_NONE}
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
	printf '${C_GREEN}%s %s\n\n' 'Created backup of virtualenv at' "$VENV_DIR.bak${C_NONE}"
fi

if [[ $PYTHON_DEFAULT_VERSION -ge $PYTHON_MIN_VERSION ]]; then
  # if possible, use default system python version
	PYTHON_BIN='python3'
else
  # Default python version too low (or not found) try to find specific version
  for (( i="$PYTHON_LATEST_VERSION"; i >= "$PYTHON_MIN_VERSION"; i--)); do
    if [[ -n "$(which python3."$i")" ]]; then
      PYTHON_BIN="python3.$i"
      break
    fi
  done
  if [[ -z $PYTHON_BIN ]]; then
    # No suitable python version was found, inform user and exit
    printf '${C_RED}%s\n' 'tordl requires Python 3.8 or higher.' \
      'Please install it (on debian based systems: $ sudo apt-get install python3.8)${C_NONE}'
    exit 1
  fi
fi

printf "${C_GREEN}Using Python $PYTHON_BIN, located here: $(which $PYTHON_BIN)${C_NONE}\n"

virtualenv -p $PYTHON_BIN "$VENV_DIR"

PS1=$PS1B

. "$VENV_DIR/bin/activate"
pip3 install -r "$SCRIPT_DIR/requirements.txt"

while true; do
	# This ugly expansion is to get the last elem of $LN_CMD in a more compatible way.
	printf ${C_GREEN}
	read -p "Do you want to link tordl.sh to $TORDL_BIN_PATH ? [Y/n]: " choice
	printf ${C_NONE}
	case "${choice,,}" in
		''|'y')
			"${LN_CMD[@]}"
			printf "${C_GREEN}tordl successfully linked 'tordl' or 'tordl SEARCH_TERM'${C_NONE}\n"
			break
		;;
		'n')
			break
		;;
	esac
done
