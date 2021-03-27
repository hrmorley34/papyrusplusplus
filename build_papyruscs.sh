#!/bin/bash
PROJECT_ROOT=$(realpath "${0%/*}")
if ! cd "$PROJECT_ROOT"; then
    exit 2
fi


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


cd "$PROJECT_ROOT/papyruscs"

rm -r "$PROJECT_ROOT/papyrusbin"
dotnet publish PapyrusCs -c Debug --self-contained --runtime "$RUNTIME" --output "$PROJECT_ROOT/papyrusbin"
