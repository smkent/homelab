FROM runitor/runitor:v1 AS runitor
FROM rclone/rclone:1
ARG UID=1000
ARG USER=rclone
COPY --from=runitor /usr/local/bin/runitor /usr/local/bin/runitor
RUN apk --no-cache add jq shadow tini \
    && { deluser rclone; delgroup rclone; }; \
    useradd -b /home -m -U -u "${UID}" -s /bin/sh "${USER}"

COPY --chown="${USER}:${USER}" --chmod=0755 entrypoint /entrypoint

USER "${USER}"
ENTRYPOINT ["/sbin/tini", "--", "/entrypoint"]
CMD ["sleep"]
