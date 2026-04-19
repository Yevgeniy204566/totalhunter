"""
coord_manager.py — 2-point coordinate calibration system.
Replaces window_scaler.py.

Reference resolution: 1920x1080.
Anchor A: minimap center (bottom-left).
Anchor B: silver resource crosshair (top-right).

Math:
    scale_x = (B_user_x - A_user_x) / (B_ref_x - A_ref_x)
    scale_y = (B_user_y - A_user_y) / (B_ref_y - A_ref_y)
    x_screen = A_user_x + (x_ref - A_ref_x) * scale_x
    y_screen = A_user_y + (y_ref - A_ref_y) * scale_y

Dialog offset (dialog_offset_x / dialog_offset_y):
    Extra shift applied to in-game dialog windows (crypt detail dialog).
    In browser the dialog can appear lower than scale alone would predict.
    Set per-profile, default 0.
"""
import json

# Reference anchor points at 1920x1080
REF_A: tuple[int, int] = (90, 925)    # minimap center (bottom-left)
REF_B: tuple[int, int] = (1149, 88)   # silver crosshair (top-right) — верифицировано 2026-04-11

_DX_REF = REF_B[0] - REF_A[0]   # 1059
_DY_REF = REF_B[1] - REF_A[1]   # -837


class CoordinateManager:
    """
    Transforms reference (1920x1080) coordinates to actual screen coordinates.

    Usage:
        from coord_manager import coord_manager
        sx, sy = coord_manager.to_screen(689, 941)
        sx, sy = coord_manager.to_screen_dialog(1137, 785)  # with dialog offset
    """

    def __init__(self):
        self.scale_x: float = 1.0
        self.scale_y: float = 1.0
        self.anchor_x: int = REF_A[0]
        self.anchor_y: int = REF_A[1]
        self._point_a: tuple[int, int] = REF_A
        self._point_b: tuple[int, int] = REF_B
        self.dialog_offset_x: int = 0
        self.dialog_offset_y: int = 0

    def calibrate(self, a_user: tuple[int, int], b_user: tuple[int, int]) -> None:
        """
        Compute scale factors from two user-measured anchor points.

        a_user: pixel position of minimap center on user's screen.
        b_user: pixel position of silver crosshair on user's screen.
        """
        self._point_a = tuple(a_user)
        self._point_b = tuple(b_user)
        self.anchor_x, self.anchor_y = int(a_user[0]), int(a_user[1])
        self.scale_x = (b_user[0] - a_user[0]) / _DX_REF
        self.scale_y = (b_user[1] - a_user[1]) / _DY_REF

    def to_screen(self, x: int, y: int) -> tuple[int, int]:
        """Convert reference coordinate to actual screen pixel."""
        return (
            int(self.anchor_x + (x - REF_A[0]) * self.scale_x),
            int(self.anchor_y + (y - REF_A[1]) * self.scale_y),
        )

    def to_region(self, x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
        """Convert reference region (x, y, w, h) to actual screen region."""
        sx, sy = self.to_screen(x, y)
        return (sx, sy, int(w * self.scale_x), int(h * abs(self.scale_y)))

    def to_screen_dialog(self, x: int, y: int) -> tuple[int, int]:
        """Like to_screen but adds dialog_offset for in-game dialog windows."""
        sx, sy = self.to_screen(x, y)
        return (sx + self.dialog_offset_x, sy + self.dialog_offset_y)

    def to_region_dialog(self, x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
        """Like to_region but adds dialog_offset for in-game dialog windows."""
        sx, sy, sw, sh = self.to_region(x, y, w, h)
        return (sx + self.dialog_offset_x, sy + self.dialog_offset_y, sw, sh)

    def save(self, path: str) -> None:
        """Save calibration to JSON profile."""
        data = {
            "point_a": list(self._point_a),
            "point_b": list(self._point_b),
            "scale_x": self.scale_x,
            "scale_y": self.scale_y,
            "dialog_offset_x": self.dialog_offset_x,
            "dialog_offset_y": self.dialog_offset_y,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str) -> None:
        """Load calibration from JSON profile and re-calibrate."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.calibrate(tuple(data["point_a"]), tuple(data["point_b"]))
        self.dialog_offset_x = int(data.get("dialog_offset_x", 0))
        self.dialog_offset_y = int(data.get("dialog_offset_y", 0))


# Global singleton — import this everywhere instead of window_scaler
coord_manager = CoordinateManager()
