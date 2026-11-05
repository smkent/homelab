FROM --platform=$BUILDPLATFORM caddy:2-builder AS builder

ARG TARGETOS TARGETARCH
RUN GOOS=$TARGETOS GOARCH=$TARGETARCH CGO_ENABLED=0 xcaddy build \
    --with github.com/caddy-dns/linode \
    --with github.com/mholt/caddy-dynamicdns \
    --with github.com/mholt/caddy-l4 \
    --with github.com/ss098/certmagic-s3

FROM caddy:2

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
