#! /usr/bin/env bash
set -eu

# Simply logs its input to a file
# Arguments:
#   - filename: file to append the input to
# stdin: message

message=$(cat)
filename=$1

echo "$message" >> $filename
