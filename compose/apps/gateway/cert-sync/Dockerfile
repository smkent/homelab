FROM alpine:latest
RUN apk add --no-cache bash inotify-tools openssl tini
COPY sync.sh /
ENTRYPOINT ["/sbin/tini", "--", "/sync.sh"]
