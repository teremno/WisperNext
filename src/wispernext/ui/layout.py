"""Pure multi-monitor placement rules for the floating control."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScreenRect:
    x: int
    y: int
    width: int
    height: int


def visible_button_position(
    stored_x: int | None,
    stored_y: int | None,
    *,
    button_size: int,
    screens: tuple[ScreenRect, ...],
    margin: int = 24,
) -> tuple[int, int]:
    """Keep a logical-DPI button fully visible on the nearest available screen."""
    if not screens:
        return (margin, margin)
    if stored_x is None or stored_y is None:
        primary = screens[0]
        return (
            primary.x + primary.width - button_size - margin,
            primary.y + primary.height - button_size - margin,
        )

    center_x = stored_x + button_size // 2
    center_y = stored_y + button_size // 2
    target = min(
        screens,
        key=lambda screen: _distance_squared(center_x, center_y, screen),
    )
    maximum_x = target.x + max(0, target.width - button_size)
    maximum_y = target.y + max(0, target.height - button_size)
    return (
        min(max(stored_x, target.x), maximum_x),
        min(max(stored_y, target.y), maximum_y),
    )


def _distance_squared(x: int, y: int, screen: ScreenRect) -> int:
    nearest_x = min(max(x, screen.x), screen.x + screen.width)
    nearest_y = min(max(y, screen.y), screen.y + screen.height)
    return (x - nearest_x) ** 2 + (y - nearest_y) ** 2
