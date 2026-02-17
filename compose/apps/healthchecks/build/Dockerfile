FROM healthchecks/healthchecks:v4.0
COPY logo.png static-collected/img/
COPY *.py hc/
USER root
RUN pip install mozilla-django-oidc
USER hc
