from identity_service.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher


def test_hash_and_verify_roundtrip() -> None:
    hasher = Argon2PasswordHasher()
    password_hash = hasher.hash("Str0ngPassword")
    assert password_hash != "Str0ngPassword"
    assert password_hash.startswith("$argon2")
    assert hasher.verify("Str0ngPassword", password_hash)


def test_verify_rejects_wrong_password() -> None:
    hasher = Argon2PasswordHasher()
    password_hash = hasher.hash("Str0ngPassword")
    assert not hasher.verify("WrongPassword1", password_hash)


def test_verify_rejects_garbage_hash() -> None:
    hasher = Argon2PasswordHasher()
    assert not hasher.verify("Str0ngPassword", "not-a-hash")


def test_hashes_are_salted() -> None:
    hasher = Argon2PasswordHasher()
    assert hasher.hash("Str0ngPassword") != hasher.hash("Str0ngPassword")
