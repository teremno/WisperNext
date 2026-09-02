from wispernext.ui.layout import (
    ScreenRect,
    button_position_is_visible,
    visible_button_position,
)

SCREENS = (
    ScreenRect(0, 0, 1920, 1040),
    ScreenRect(-1280, 0, 1280, 984),
)


def test_default_position_uses_primary_bottom_right_margin() -> None:
    assert visible_button_position(None, None, button_size=64, screens=SCREENS) == (1832, 952)


def test_valid_negative_multi_monitor_position_is_preserved() -> None:
    assert visible_button_position(-500, 200, button_size=64, screens=SCREENS) == (-500, 200)


def test_offscreen_position_is_clamped_to_nearest_screen() -> None:
    assert visible_button_position(4000, 2000, button_size=64, screens=SCREENS) == (1856, 976)


def test_no_screen_has_deterministic_safe_fallback() -> None:
    assert visible_button_position(None, None, button_size=64, screens=()) == (24, 24)


def test_visibility_requires_the_whole_button_to_fit_on_one_screen() -> None:
    assert button_position_is_visible(-64, 300, button_size=64, screens=SCREENS)
    assert not button_position_is_visible(-32, 300, button_size=64, screens=SCREENS)
    assert not button_position_is_visible(1900, 300, button_size=64, screens=SCREENS)
