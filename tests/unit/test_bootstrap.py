from pathlib import Path

from wispernext.bootstrap import build_application_services
from wispernext.domain import ApplicationState


def test_composition_root_is_side_effect_free_and_returns_fresh_services(tmp_path: Path) -> None:
    settings_path = tmp_path / "data" / "settings.json"

    first = build_application_services(settings_path=settings_path, environ={})
    second = build_application_services(settings_path=settings_path, environ={})

    assert first.state_machine.snapshot().state is ApplicationState.STARTING
    assert first.state_machine is not second.state_machine
    assert first.microphone_catalog is not second.microphone_catalog
    assert first.audio_session is not second.audio_session
    assert first.settings_store.path == settings_path
    assert first.secret_provider.get_groq_api_key() is None
    assert first.transcription is not second.transcription
    assert first.clipboard_delivery is not second.clipboard_delivery
    assert first.auto_paste is not second.auto_paste
    assert not settings_path.parent.exists()
