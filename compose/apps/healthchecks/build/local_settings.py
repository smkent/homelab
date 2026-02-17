# mypy: disable-error-code="import-not-found,import-untyped"
# ruff: noqa N811

import os
import sys
from collections.abc import Sequence
from types import ModuleType
from typing import Any

import requests
from django.urls import URLPattern, URLResolver, include, path
from django.views.generic.base import RedirectView

from .settings import AUTHENTICATION_BACKENDS as _auth_backends
from .settings import INSTALLED_APPS as _installed_apps
from .settings import MIDDLEWARE as _middleware
from .settings import ROOT_URLCONF as _root_urlconf
from .settings import envbool, envsecret

_oidc_provider_url = os.environ["OIDC_PROVIDER_URL"].removesuffix("/")
_oidc_conf = requests.get(
    f"{_oidc_provider_url}/.well-known/openid-configuration", timeout=5
).json()

OIDC_RP_CLIENT_ID = envsecret("OIDC_CLIENT_ID")
OIDC_RP_CLIENT_SECRET = envsecret("OIDC_CLIENT_SECRET")
OIDC_OP_AUTHORIZATION_ENDPOINT = _oidc_conf["authorization_endpoint"]
OIDC_OP_TOKEN_ENDPOINT = _oidc_conf["token_endpoint"]
OIDC_OP_USER_ENDPOINT = _oidc_conf["userinfo_endpoint"]
OIDC_OP_JWKS_ENDPOINT = _oidc_conf["jwks_uri"]
OIDC_RP_SIGN_ALGO = os.getenv("OIDC_RP_SIGN_ALGO", "RS256")
OIDC_RP_SCOPES = os.getenv("OIDC_RP_SCOPES", "openid email")
OIDC_TOKEN_USE_BASIC_AUTH = envbool("OIDC_TOKEN_USE_BASIC_AUTH", "False")
OIDC_CREATE_USER = envbool("OIDC_CREATE_USER", "True")

LOGIN_REDIRECT_URL = "/"


def _insert(src: Sequence[Any], val: Any, after: Any = None) -> tuple[Any]:
    src_list = list(src)
    where = (src_list.index(after) + 1) if after else len(src_list)
    src_list.insert(where, val)
    return tuple(src_list)


AUTHENTICATION_BACKENDS = _auth_backends + [
    "mozilla_django_oidc.auth.OIDCAuthenticationBackend"
]
INSTALLED_APPS = _insert(
    _installed_apps, "mozilla_django_oidc", "django.contrib.auth"
)
MIDDLEWARE = _insert(
    _middleware,
    "mozilla_django_oidc.middleware.SessionRefresh",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
)


class _URLPatternsWithOIDC(ModuleType):
    @property
    def urlpatterns(self) -> list[URLResolver | URLPattern]:
        return [
            path("oidc/", include("mozilla_django_oidc.urls")),
            path(
                "accounts/login/",
                RedirectView.as_view(url="/oidc/authenticate", permanent=True),
            ),
            path("", include(_root_urlconf)),
        ]


ROOT_URLCONF = "hc.url_patterns_with_oidc"
sys.modules[ROOT_URLCONF] = _URLPatternsWithOIDC(ROOT_URLCONF)
