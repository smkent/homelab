FROM ghcr.io/garethgeorge/backrest:latest

ARG UID=1000
ARG USER=backrest
RUN apk --no-cache add libcap shadow
RUN setcap cap_dac_read_search+ep /bin/restic
RUN addgroup --gid 200 docker \
    && useradd -b /opt -m -U -u "${UID}" -G docker -s /bin/sh "${USER}"
COPY --chown="${USER}:${USER}" --chmod=0755 entrypoint /entrypoint-wrapper

USER "${USER}"
ENTRYPOINT ["/sbin/tini", "--", "/entrypoint-wrapper", "/docker-entrypoint"]
CMD ["/backrest"]
