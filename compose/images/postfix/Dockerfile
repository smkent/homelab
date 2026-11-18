FROM mwader/postfix-relay:1.2.17@sha256:3ff7e7cb535f17570faabd9df3036ea65e69e3507c491e4ff8938189225a3382
RUN apt update \
    && DEBIAN_FRONTEND=noninteractive apt-get -y dist-upgrade \
    && apt-get install -y --no-install-recommends sasl2-bin libsasl2-modules s3cmd \
    && apt-get -y autoremove --purge \
    && rm -rf /var/lib/apt/lists/*
COPY smtpd.conf /etc/postfix/sasl/smtpd.conf
COPY entrypoint cert-sync /smkent-extras/
CMD ["/smkent-extras/entrypoint"]
