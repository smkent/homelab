#!/bin/sh

set -eu

CADDY_DATA="${CADDY_DATA-/data/caddy}"
DEST="${DEST-/data/certs}"

find_cert_dirs() {
    find "${CADDY_DATA}" \
        -type d \
        -path "*/certificates/acme-*" -and -name 'acme-*'
}

copy_certs() {
    echo "[$(date "+%Y-%m-%dT%H:%M:%S")] Checking certs"
    find_cert_dirs | while read -r search_dir; do
        find "${search_dir}" -mindepth 1 -type d | while read -r cert_dir; do
            bn=$(basename "${cert_dir}")
            mtime=$(stat -c %Y "${search_dir}")
            echo "${bn} ${mtime} ${cert_dir}";
        done
    done | sort -k1,1 -k2,2nr | awk '!seen[$1]++ {print $3}' | (
        while read -r nd; do
            copy_cert "${nd}"
        done
    )
}

copy_cert() {
    dir="${1?Certificate directory is required}"
    shift
    crt=$(find "${dir}" -name '*.crt' | head -n 1)
    key=$(find "${dir}" -name '*.key' | head -n 1)
    crt_cn=$(
        openssl x509 -in "${crt}" -noout -subject \
            | sed -ne 's/\*/_/g' -e 's/.*CN=\(.*\)/\1/p'
    )
    crt_dest="${DEST}/${crt_cn}/x509.crt"
    key_dest="${DEST}/${crt_cn}/x509.key"
    if [ -n "${crt_cn}" ] && [ -f "${crt}" ] && [ -f "${key}" ]; then
        if (
                diff -q "${crt}" "${crt_dest}" \
                && diff -q "${key}" "${key_dest}"
        ) 2>/dev/null; then
            echo "Unchanged: $(basename "${dir}")"
            return
        fi
        echo "Updated: $(basename "${dir}")"
        mkdir -vp "$(dirname "${crt_dest}")"
        cp -v "${crt}" "${crt_dest}.temp"
        cp -v "${key}" "${key_dest}.temp"
        mv -v "${crt_dest}.temp" "${crt_dest}"
        mv -v "${key_dest}.temp" "${key_dest}"
        chown -c 0:0 "${crt_dest}" "${key_dest}"
        chmod -c 0600 "${key_dest}"
    fi
}

copy_certs
while true; do
    inotifywait -t 86400 -e create -e modify -r "${CADDY_DATA}"
    sleep 5
    copy_certs
done
