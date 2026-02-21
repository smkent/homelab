FROM alpine:latest

RUN apk add --no-cache tini nfs-utils \
    && mkdir -p /var/lib/nfs/v4recovery

COPY entrypoint /smkent-extras/
COPY exports /etc/exports

EXPOSE 2049/tcp

ENTRYPOINT ["/sbin/tini", "-g", "--", "/smkent-extras/entrypoint"]
