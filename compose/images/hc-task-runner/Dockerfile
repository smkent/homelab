FROM rclone/rclone:1
ARG UID=1000
ARG USER=deploy

RUN apk --no-cache add bash curl jq mailx tini trurl yq
COPY --from=runitor/runitor:v1 /usr/local/bin/runitor /usr/local/bin/runitor

RUN addgroup -g "${UID}" "${USER}" && adduser -S -D -u "${UID}" -G "${USER}" "${USER}"
USER "${USER}"

ENV SMTPHOST=smtp

COPY --chown="${USER}:${USER}" --chmod=0755 entrypoint /entrypoint
ENTRYPOINT ["/sbin/tini", "--", "/entrypoint"]
CMD ["sleep"]
