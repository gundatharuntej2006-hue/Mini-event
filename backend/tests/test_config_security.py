import pytest
from pydantic import ValidationError
from app.core.config import Settings


def test_short_secret_key_raises_validation_error():
    with pytest.raises((ValueError, ValidationError)) as exc_info:
        Settings(SECRET_KEY="short_key_under_32_chars")
    assert "SECRET_KEY must be explicitly configured" in str(exc_info.value) or "at least 32 characters" in str(exc_info.value)


def test_empty_secret_key_raises_validation_error():
    with pytest.raises((ValueError, ValidationError)) as exc_info:
        Settings(SECRET_KEY="")
    assert "SECRET_KEY must be explicitly configured" in str(exc_info.value) or "at least 32 characters" in str(exc_info.value)


def test_valid_secret_key_passes():
    valid_key = "a_very_strong_and_secure_secret_key_with_over_32_characters!"
    s = Settings(SECRET_KEY=valid_key)
    assert s.SECRET_KEY == valid_key