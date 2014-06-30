#! /usr/bin/env bash
set -eu

# Arguments:
#   filename
# stdin: message
# Simply appends its input to the file

message=$(cat)
filename=$1

echo "$message" >> $filename
