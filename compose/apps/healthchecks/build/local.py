# mypy: disable-error-code="import-not-found,import-untyped"

from typing import Any

from hc.accounts.models import Profile
from hc.accounts.views import _make_user
from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class OIDCAuthSubClaimBackend(OIDCAuthenticationBackend):
    def create_user(self, claims: dict[str, str]) -> Any:
        user = _make_user(claims["email"], with_project=False)
        profile = Profile.objects.for_user(user)
        profile.theme = "system"
        profile.save()
        return self.update_user(user, claims)

    def update_user(self, user: Any, claims: dict[str, str]) -> Any:
        if (sub := claims.get("sub")) and user.username != sub:
            user.username = sub
            user.save()
        is_admin = claims.get("healthchecks_role") == "admin"
        if is_admin != user.is_superuser or user.is_staff != user.is_superuser:
            user.is_staff = is_admin
            user.is_superuser = is_admin
            user.save()
        return user

    def filter_users_by_claims(self, claims: dict[str, str]) -> Any:
        if sub := claims.get("sub"):
            query = self.UserModel.objects.filter(username=sub)
            if query.count() > 0:
                return query
        return super().filter_users_by_claims(claims)
