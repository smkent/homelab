FROM rclone/rclone:1
ARG UID=1000
ARG USER=deploy

RUN apk --no-cache add \
    bash ca-certificates curl git jq mailx python3 py3-pip tini trurl yq
RUN pip install --no-cache-dir --break-system-packages linode-cli
COPY --from=runitor/runitor:v1 /usr/local/bin/runitor /usr/local/bin/
COPY --from=ghcr.io/gabrie30/ghorg:latest /usr/local/bin/ghorg /usr/local/bin/

RUN addgroup -g "${UID}" "${USER}" && adduser -S -D -u "${UID}" -G "${USER}" "${USER}"
USER "${USER}"

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV SMTPHOST=smtp

COPY --chown="${USER}:${USER}" --chmod=0755 entrypoint /entrypoint
ENTRYPOINT ["/sbin/tini", "--", "/entrypoint"]
CMD ["sleep"]
