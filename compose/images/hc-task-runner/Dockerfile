FROM rclone/rclone:1
ARG UID=1000
ARG USER=deploy

RUN addgroup -g "${UID}" "${USER}" \
    && adduser -S -D -u "${UID}" -G "${USER}" "${USER}" \
    && mkdir -vp /config && chown -Rc "${UID}:${UID}" /config \
    && apk --no-cache add \
        bash ca-certificates curl git gnupg isync jq mailx \
        nodejs npm python3 py3-pip rsync tini trurl yq \
    && pip install --no-cache-dir --break-system-packages pipx \
    && pipx install --global linode-cli vdirsyncer \
    && npm install -g @bitwarden/cli
COPY --from=runitor/runitor:v1 /usr/local/bin/runitor /usr/local/bin/
COPY --from=ghcr.io/gabrie30/ghorg:latest /usr/local/bin/ghorg /usr/local/bin/

USER "${USER}"
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV SMTPHOST=smtp

COPY --chown="${USER}:${USER}" --chmod=0755 entrypoint /entrypoint
ENTRYPOINT ["/sbin/tini", "--", "/entrypoint"]
CMD ["sleep"]
