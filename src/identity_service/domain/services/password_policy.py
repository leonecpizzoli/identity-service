from identity_service.domain.exceptions.errors import ValidationError


class PasswordPolicy:
    minimum_length = 10
    maximum_length = 128

    @classmethod
    def ensure_strong(cls, raw_password: str) -> None:
        if len(raw_password) < cls.minimum_length:
            raise ValidationError(
                f"password must have at least {cls.minimum_length} characters",
                field="password",
            )
        if len(raw_password) > cls.maximum_length:
            raise ValidationError(
                f"password must have at most {cls.maximum_length} characters",
                field="password",
            )
        if not any(character.islower() for character in raw_password):
            raise ValidationError("password must contain a lowercase letter", field="password")
        if not any(character.isupper() for character in raw_password):
            raise ValidationError("password must contain an uppercase letter", field="password")
        if not any(character.isdigit() for character in raw_password):
            raise ValidationError("password must contain a digit", field="password")
