#!/bin/sh

if [ "${USER}" != "root" ]; then
    set -x
    exec sudo "${0}" "${@}"
    exit 1
fi

set -ex

for d in . db slapd.d; do
    dir="data/${d}"
    sudo mkdir -vp "${dir}"
    sudo chown -v 1001:0 "${dir}"
done
