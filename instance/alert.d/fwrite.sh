#! /usr/bin/env bash
set -eu

# Arguments:
#   filename
# stdin: message
# Simply writes its input to the file

message=$(cat)
filename=$1

echo "$message" > $filename
