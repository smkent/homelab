FROM instantlinux/nut-upsd:2.8.0-r2
RUN apk add tini s-nail
COPY entrypoint /smkent-extras/
COPY upssched.conf /etc/nut/upssched.conf
COPY upssched-cmd /usr/bin/upssched-cmd
ENTRYPOINT ["/sbin/tini", "-g", "--"]
CMD ["/smkent-extras/entrypoint"]
