from app.bot import texts
from app.enums import DeviceStatus
from app.models import Device


def test_device_name_is_escaped_in_user_messages() -> None:
    device_name = "<b>evil</b>"
    device = Device(
        id=1,
        user_id=1,
        name=device_name,
        identifier="device",
        status=DeviceStatus.ACTIVE,
    )

    rendered = texts.devices_screen([device], limit=3)

    assert "<b>evil</b>" not in rendered
    assert "&lt;b&gt;evil&lt;/b&gt;" in rendered
    assert "&lt;b&gt;evil&lt;/b&gt;" in texts.device_added(device_name)
    assert "&lt;b&gt;evil&lt;/b&gt;" in texts.device_revoked(device_name)


def test_connection_link_escapes_url() -> None:
    rendered = texts.connection_link("https://example.com/s/<bad>", configured=True)

    assert "https://example.com/s/<bad>" not in rendered
    assert "https://example.com/s/&lt;bad&gt;" in rendered
