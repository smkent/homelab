FROM olbat/cupsd:stable

RUN apt update \
    && apt install tini
RUN printf "Listen *:631\nServerAlias *\n" >> /etc/cups/cupsd.conf \
    && sed -i /etc/cups/cupsd.conf -e 's:^DefaultAuthType.*$:DefaultAuthType none:g' \
    && echo "ServerRoot /data/cups" >> /etc/cups/cups-files.conf \
    && echo "RequestRoot /data/cups/spool" >> /etc/cups/cups-files.conf \
    && echo "TempDir /data/cups/spool/tmp" >> /etc/cups/cups-files.conf
COPY entrypoint /smkent-extras/

VOLUME /data/cups
ENTRYPOINT ["/usr/bin/tini", "-g", "--"]
CMD ["/smkent-extras/entrypoint"]
