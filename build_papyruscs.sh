#!/bin/bash
PROJECT_ROOT=$(realpath "${0%/*}")
if ! cd "$PROJECT_ROOT"; then
    exit 2
fi

BOLD=$(echo -ne "\033[1m")
RESET=$(echo -ne "\033[0m")
COLOUR=$(echo -ne "\033[36m")


# test like https://stackoverflow.com/questions/394230/how-to-detect-the-os-from-a-bash-script
case "$OSTYPE" in
    "linux-gnu"*)
        RUNTIME="linux-x64"
        ;; # linux
    "cygwin"|"msys"|"win32")
        RUNTIME="win-x64"
        ;; # cygwin/msys
    "darwin"*|"freebsd"*)
        echo "Not implemented!" 2&>1 /dev/null
        exit 1
        ;;
    *)
        echo "Unknown OS!" 2&>1 /dev/null
        exit 1
        ;;
esac


echo "${BOLD}Remember to update the submodule!${RESET}"
echo "${COLOUR}git submodule update --remote papyruscs${RESET}"
sleep 1


cd "$PROJECT_ROOT/papyruscs"

echo "${BOLD}Deleting old bin${RESET}"
rm -r "$PROJECT_ROOT/papyrusbin"
echo "${BOLD}Building${RESET}"
dotnet publish PapyrusCs -c Debug --self-contained --runtime "$RUNTIME" --output "$PROJECT_ROOT/papyrusbin"
echo "${BOLD}Done.${RESET}"
