FROM mwader/postfix-relay:1
RUN apt update \
    && apt install -y sasl2-bin libsasl2-modules s3cmd \
    && rm -rf /var/lib/apt/lists/*
COPY smtpd.conf /etc/postfix/sasl/smtpd.conf
COPY entrypoint cert-sync /smkent-extras/
CMD ["/smkent-extras/entrypoint"]
