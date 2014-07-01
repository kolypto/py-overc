#! /usr/bin/env bash
set -eu

# Always fails with an error (for testing)
# stdin: message

echo 'Failure'
echo 'Failed' >&2

exit 1
