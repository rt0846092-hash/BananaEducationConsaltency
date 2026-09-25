from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class PasswordAwareJWTAuthentication(JWTAuthentication):
    """Rejects tokens issued before the user's last password change.

    Plain JWTs stay valid until they expire, so a stolen token outlived a
    password change by up to eight hours. Now a change or an owner reset in
    the admin signs out every other device immediately.
    """

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        changed = user.password_changed_at
        issued = validated_token.get("iat")
        if changed and issued is not None and int(issued) < int(changed.timestamp()):
            raise AuthenticationFailed("Your password was changed. Please sign in again.",
                                       code="password_changed")
        return user
