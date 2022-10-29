FROM alpine:latest
RUN apk add tini cronie openssh-client rsync
ENV CRON_SCHEDULE "*/10 * * * *"
COPY backup-apps cron-wrap entrypoint /smkent-extras/
ENTRYPOINT ["/sbin/tini", "-g", "--"]
CMD ["/smkent-extras/entrypoint"]
