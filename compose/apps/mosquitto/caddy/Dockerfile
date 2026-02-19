FROM caddy:2-builder AS builder

RUN xcaddy build \
    --with github.com/caddy-dns/linode \
    --with github.com/mholt/caddy-dynamicdns \
    --with github.com/mholt/caddy-l4

FROM caddy:2

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
