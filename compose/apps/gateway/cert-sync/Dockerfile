FROM alpine:latest
RUN apk add --no-cache bash inotify-tools openssl tini
COPY sync.sh /
# RUN chmod +x /sync.sh
ENTRYPOINT ["/sbin/tini", "--", "/sync.sh"]
