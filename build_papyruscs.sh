#!/bin/bash
PROJECT_ROOT=$(realpath "${0%/*}")
if ! cd "$PROJECT_ROOT"; then
    exit 2
fi

BOLD=$(echo -ne "\033[1m")
RESET=$(echo -ne "\033[0m")
COLOUR=$(echo -ne "\033[36m")

if [ -z "$PAPYRUSCS_ROOT" ]; then
    PAPYRUSCS_ROOT="$PROJECT_ROOT/papyruscs"
fi
if ! [ -d "$PAPYRUSCS_ROOT" ]; then
    echo "${BOLD}papyruscs not found at ${RESET}${COLOUR}${PAPYRUSCS_ROOT}${RESET}" 1>&2
    echo "${BOLD}Please set ${RESET}${COLOUR}\$PAPYRUSCS_ROOT${RESET}${BOLD}.${RESET}" 1>&2
    exit 1
fi

PAPYRUSCS_BIN="${PROJECT_ROOT}/papyrusbin"

# test like https://stackoverflow.com/questions/394230/how-to-detect-the-os-from-a-bash-script
case "$OSTYPE" in
    "linux-gnu"*)
        RUNTIME="linux-x64"
        ;; # linux
    "cygwin"|"msys"|"win32")
        RUNTIME="win-x64"
        ;; # cygwin/msys
    "darwin"*|"freebsd"*)
        echo "Not implemented!" 1>&2
        exit 1
        ;;
    *)
        echo "Unknown OS!" 1>&2
        exit 1
        ;;
esac


echo "${BOLD}Using papyruscs in ${RESET}${COLOUR}${PAPYRUSCS_ROOT}${RESET}"
cd "${PAPYRUSCS_ROOT}" || exit 1

echo "${BOLD}Deleting old bin.${RESET}"
rm -r "${PAPYRUSCS_BIN}"
echo "${BOLD}Building to ${RESET}${COLOUR}${PAPYRUSCS_BIN}${RESET}${BOLD}...${RESET}"
dotnet publish PapyrusCs -c Debug --self-contained --runtime "${RUNTIME}" --output "${PAPYRUSCS_BIN}"
echo "${BOLD}Done.${RESET}"
