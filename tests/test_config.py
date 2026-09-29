from app.config import Settings


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        telegram_bot_token="test-token",
        telegram_channel_id="@my_channel",
        admin_telegram_ids="111",
    )
    defaults.update(overrides)
    return Settings(**defaults)


def test_channel_link_derived_from_username():
    settings = _make_settings(telegram_channel_id="@my_channel")
    assert settings.channel_link == "https://t.me/my_channel"


def test_channel_link_explicit_override_wins():
    settings = _make_settings(
        telegram_channel_id="-1001234567890",
        telegram_channel_link="https://t.me/+invitecode",
    )
    assert settings.channel_link == "https://t.me/+invitecode"


def test_channel_link_falls_back_to_raw_id_when_numeric_and_unset():
    settings = _make_settings(telegram_channel_id="-1001234567890")
    assert settings.channel_link == "-1001234567890"
