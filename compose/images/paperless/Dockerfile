FROM ghcr.io/paperless-ngx/paperless-ngx:2.20

RUN apt update \
    && apt install -y git \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -vp /opt/postprocessor/rulesets \
    && chown -Rc paperless: /opt/postprocessor

USER paperless

RUN cd /opt/postprocessor \
    && git clone \
        --branch v2.0.2 \
        https://github.com/jgillula/paperless-ngx-postprocessor src \
    && ./src/setup_venv.sh

USER root

ENV PAPERLESS_POST_CONSUME_SCRIPT=/opt/postprocessor/src/post_consume_script.sh \
    PNGX_POSTPROCESSOR_RULESETS_DIR=/opt/postprocessor/rulesets
