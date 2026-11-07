FROM healthchecks/healthchecks:v5.0.3
COPY logo.png static-collected/img/
COPY *.py hc/
USER root
RUN pip install "mozilla-django-oidc>=5,<6.0"
USER hc
