FROM mwader/postfix-relay:1
RUN apt update && apt install -y sasl2-bin libsasl2-modules
COPY smtpd.conf /etc/postfix/sasl/smtpd.conf
COPY entrypoint /smkent-extras/
CMD ["/smkent-extras/entrypoint"]
