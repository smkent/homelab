FROM ghcr.io/garethgeorge/backrest:latest

ARG UID=1000
ARG USER=backrest
RUN apk --no-cache add libcap shadow
RUN setcap cap_dac_read_search+ep /bin/restic
COPY --chown="${USER}:${USER}" --chmod=0755 entrypoint /entrypoint-wrapper
RUN useradd -b /opt -m -U -u "${UID}" -s /bin/sh "${USER}"

USER "${USER}"
ENTRYPOINT ["/sbin/tini", "--", "/entrypoint-wrapper", "/docker-entrypoint"]
CMD ["/backrest"]
