FROM caddy:2-builder AS builder

RUN xcaddy build \
    --with github.com/caddy-dns/linode

FROM caddy:2

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
