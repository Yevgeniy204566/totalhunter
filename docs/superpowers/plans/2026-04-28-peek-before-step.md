# Peek-Before-Step Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Before every joystick click in DIVING/RETURNING, read the minimap — jump over water channels with a scaled step, stop at ocean/coast boundary.

**Architecture:** New `_peek_step(direction)` method reads minimap at 3 radii (30/60/90px = 1/2/3 screens) and returns a step multiplier (1.0/1.5/2.0) or None for ocean. `_move_perpendicular` gets a `multiplier` param. DIVING and RETURNING use peek before each click.

**Tech Stack:** Python 3.13, pytest, unittest.mock

---

## File Map

| File | Changes |
|------|---------|
| `C:\BattleBot\navigator.py` | `_peek_step()`, `_move_perpendicular(multiplier)`, DIVING phase, RETURNING phase |
| `C:\BattleBot\test_coastal_snake.py` | 9 new tests across 2 new classes |

---

### Task 1: `_peek_step()` method

**Files:**
- Modify: `C:\BattleBot\navigator.py`
- Modify: `C:\BattleBot\test_coastal_snake.py`

- [ ] **Step 1: Write failing tests**

Add new class at end of `test_coastal_snake.py`:

```python
class TestPeekStep:
    def _nav(self):
        nav = make_navigator()
        nav._inland_vec = (1.0, 0.0)
        return nav

    def test_land_immediate_returns_1x(self):
        """radius=30 has land → 1.0 (normal step)."""
        nav = self._nav()
        land_info  = {'land_px': 50, 'water_px': 0, 'is_ocean': False, 'land_ratio': 0.5}
        with patch('minimap_reader.analyze_forward_zone', return_value=land_info):
            result = nav._peek_step((1.0, 0.0))
        assert result == 1.0

    def test_water_then_land_mid_returns_1_5x(self):
        """radius=30 water, radius=60 has land → 1.5 (jump 1 screen)."""
        nav = self._nav()
        water_info = {'land_px': 0, 'water_px': 600, 'is_ocean': False, 'land_ratio': 0.0}
        land_info  = {'land_px': 30, 'water_px': 600, 'is_ocean': False, 'land_ratio': 0.3}
        with patch('minimap_reader.analyze_forward_zone', side_effect=[water_info, land_info]):
            result = nav._peek_step((1.0, 0.0))
        assert result == 1.5

    def test_water_then_land_far_returns_2x(self):
        """radius=30 water, radius=60 water, radius=90 has land → 2.0 (jump 2 screens)."""
        nav = self._nav()
        water_info = {'land_px': 0, 'water_px': 600, 'is_ocean': False, 'land_ratio': 0.0}
        land_far   = {'land_px': 20, 'water_px': 600, 'is_ocean': False, 'land_ratio': 0.2}
        with patch('minimap_reader.analyze_forward_zone', side_effect=[water_info, water_info, land_far]):
            result = nav._peek_step((1.0, 0.0))
        assert result == 2.0

    def test_all_water_returns_none(self):
        """All 3 radii no land, water present → None (ocean / coast boundary)."""
        nav = self._nav()
        water_info = {'land_px': 0, 'water_px': 600, 'is_ocean': True, 'land_ratio': 0.0}
        with patch('minimap_reader.analyze_forward_zone', return_value=water_info):
            result = nav._peek_step((1.0, 0.0))
        assert result is None

    def test_no_significant_water_returns_1x(self):
        """radius=30 no land but water_px <= min_water_px → 1.0 (safe to step)."""
        nav = self._nav()
        dry_info = {'land_px': 0, 'water_px': 5, 'is_ocean': False, 'land_ratio': 0.0}
        with patch('minimap_reader.analyze_forward_zone', return_value=dry_info):
            result = nav._peek_step((1.0, 0.0))
        assert result == 1.0
```

- [ ] **Step 2: Run — confirm 5 FAILED**

```
cd C:\BattleBot && python -m pytest test_coastal_snake.py::TestPeekStep -v
```
Expected: `AttributeError: '_peek_step'` or similar.

- [ ] **Step 3: Implement `_peek_step` in navigator.py**

Find the `_is_at_coast_now` method (~line 640). Add new method BEFORE it:

```python
    def _peek_step(self, direction_vec: tuple) -> float | None:
        """
        Read minimap in direction_vec at 3 depths (1/2/3 screens).
        Returns step multiplier to jump over water, or None if ocean/coast boundary.
        """
        from minimap_reader import analyze_forward_zone
        mm = self._grab_minimap()

        near = analyze_forward_zone(mm, direction_vec, radius=30,
                                    ocean_land_ratio=self.ocean_land_ratio,
                                    min_water_px=self.min_water_px)
        if near['land_px'] > 0 or near['water_px'] <= self.min_water_px:
            return 1.0

        mid = analyze_forward_zone(mm, direction_vec, radius=60,
                                   ocean_land_ratio=self.ocean_land_ratio,
                                   min_water_px=self.min_water_px)
        if mid['land_px'] > 0:
            return 1.5

        far = analyze_forward_zone(mm, direction_vec, radius=90,
                                   ocean_land_ratio=self.ocean_land_ratio,
                                   min_water_px=self.min_water_px)
        if far['land_px'] > 0:
            return 2.0

        return None  # ocean (DIVING) or coast boundary (RETURNING)
```

- [ ] **Step 4: Run — confirm 5 PASSED**

```
cd C:\BattleBot && python -m pytest test_coastal_snake.py::TestPeekStep -v
```
Expected: **5 PASSED**

- [ ] **Step 5: Commit**

```
cd C:\BattleBot && git add navigator.py test_coastal_snake.py && git commit -m "feat: add _peek_step() — read minimap before each joystick step"
```

---

### Task 2: `_move_perpendicular` multiplier + DIVING/RETURNING integration

**Files:**
- Modify: `C:\BattleBot\navigator.py`
- Modify: `C:\BattleBot\test_coastal_snake.py`

- [ ] **Step 1: Write failing tests**

Add new class at end of `test_coastal_snake.py`:

```python
class TestPeekIntegration:
    def _nav_diving(self):
        nav = make_navigator(max_inland=5)
        nav._state       = 'DIVING'
        nav._inland_steps = 2
        nav._inland_vec  = (1.0, 0.0)
        nav._shift_vec   = (0.0, 1.0)
        return nav

    def _nav_returning(self):
        nav = make_navigator(max_inland=5)
        nav._state        = 'RETURNING'
        nav._return_steps = 10
        nav._inland_vec   = (1.0, 0.0)
        nav._shift_vec    = (0.0, 1.0)
        return nav

    def test_diving_normal_step(self):
        """DIVING: peek=1.0 → _move_perpendicular(toward_water=False, multiplier=1.0)."""
        nav = self._nav_diving()
        with patch.object(nav, '_peek_step', return_value=1.0):
            with patch.object(nav, '_move_perpendicular') as mock_move:
                nav.step()
        mock_move.assert_called_once_with(toward_water=False, multiplier=1.0)
        assert nav._state == 'DIVING'

    def test_diving_jump_step(self):
        """DIVING: peek=1.5 → multiplier=1.5 passed to _move_perpendicular."""
        nav = self._nav_diving()
        with patch.object(nav, '_peek_step', return_value=1.5):
            with patch.object(nav, '_move_perpendicular') as mock_move:
                nav.step()
        mock_move.assert_called_once_with(toward_water=False, multiplier=1.5)

    def test_diving_aborts_on_ocean(self):
        """DIVING: peek=None (ocean ahead) → shift and start RETURNING."""
        nav = self._nav_diving()
        with patch.object(nav, '_peek_step', return_value=None):
            with patch.object(nav, '_shift_click') as mock_shift:
                nav.step()
        mock_shift.assert_called_once()
        assert nav._state == 'RETURNING'
        assert nav._return_steps == nav._inland_steps + 15

    def test_returning_normal_step(self):
        """RETURNING: peek=1.0 → _move_perpendicular(toward_water=True, multiplier=1.0)."""
        nav = self._nav_returning()
        with patch.object(nav, '_peek_step', return_value=1.0):
            with patch.object(nav, '_move_perpendicular') as mock_move:
                nav.step()
        mock_move.assert_called_once_with(toward_water=True, multiplier=1.0)
        assert nav._state == 'RETURNING'

    def test_returning_jump_step(self):
        """RETURNING: peek=1.5 → multiplier=1.5 passed to _move_perpendicular."""
        nav = self._nav_returning()
        with patch.object(nav, '_peek_step', return_value=1.5):
            with patch.object(nav, '_move_perpendicular') as mock_move:
                nav.step()
        mock_move.assert_called_once_with(toward_water=True, multiplier=1.5)

    def test_returning_stops_at_coast(self):
        """RETURNING: peek=None (coast boundary) → shift + HOMING."""
        nav = self._nav_returning()
        with patch.object(nav, '_peek_step', return_value=None):
            with patch.object(nav, '_shift_click') as mock_shift:
                nav.step()
        mock_shift.assert_called_once()
        assert nav._state == 'HOMING'
```

- [ ] **Step 2: Run — confirm 6 FAILED**

```
cd C:\BattleBot && python -m pytest test_coastal_snake.py::TestPeekIntegration -v
```
Expected: **6 FAILED**

- [ ] **Step 3: Add `multiplier` param to `_move_perpendicular`**

Find `_move_perpendicular` in `navigator.py`. Change signature and body:

```python
    def _move_perpendicular(self, toward_water: bool, multiplier: float = 1.0) -> None:
        """
        ЗАПРЕТ на движение вдоль берега.
        Движение ТОЛЬКО по ±inland_vec — строго перпендикулярно воде.

        toward_water=True  → клик в сторону воды  (-inland_vec = seaward)
        toward_water=False → клик вглубь суши      (+inland_vec = inland)
        multiplier         → масштаб шага (1.0 норм, 1.5/2.0 перепрыгнуть воду)
        """
        iv = self._inland_vec
        if toward_water:
            dx, dy = -iv[0], -iv[1]
        else:
            dx, dy = iv[0], iv[1]
        self._click_vec(dx * multiplier, dy * multiplier,
                        label='return' if toward_water else 'dive')
```

- [ ] **Step 4: Replace DIVING movement in `step()`**

Find in `step()` (~line 813):
```python
            self._move_perpendicular(toward_water=False)   # нырок вглубь суши
            self._inland_steps += 1
            return True
```

Replace with:
```python
            mult = self._peek_step(self._inland_vec)
            if mult is None:
                # Ocean ahead mid-dive → abort, return proportionally
                self._shift_click()
                self._state             = 'RETURNING'
                self._return_steps      = self._inland_steps + 15
                self._steps_since_shift = 0
                return True
            self._move_perpendicular(toward_water=False, multiplier=mult)
            self._inland_steps += 1
            return True
```

- [ ] **Step 5: Replace RETURNING movement in `step()`**

Find in `step()` the RETURNING block. Replace the current body (after the force_shift_after check) with:

```python
            seaward = (-self._inland_vec[0], -self._inland_vec[1])
            mult    = self._peek_step(seaward)
            cap_hit = self._return_steps <= 0
            if mult is None or cap_hit:
                # Coast boundary reached or safety cap → shift + HOMING
                self._shift_click()
                self._state        = 'HOMING'
                self._inland_steps = 0
                self._homing_steps = 0
                return True
            self._return_steps -= 1
            self._move_perpendicular(toward_water=True, multiplier=mult)
            return True
```

- [ ] **Step 6: Run new tests — confirm 6 PASSED**

```
cd C:\BattleBot && python -m pytest test_coastal_snake.py::TestPeekIntegration -v
```
Expected: **6 PASSED**

- [ ] **Step 7: Full regression**

```
cd C:\BattleBot && python -m pytest test_coastal_snake.py -v
```
Expected: **58 passed** (47 old + 5 TestPeekStep + 6 TestPeekIntegration), 0 failed.

> Note: `test_returning_stops_on_water` and `test_returning_continues_on_land` from `TestOceanColumnCheck` may need updating since RETURNING now uses `_peek_step` instead of `is_water`. If they fail, patch `_peek_step` instead of `_is_at_coast_now`.

- [ ] **Step 8: Fix any regression failures**

If `test_returning_stops_on_water` fails — update it:
```python
def test_returning_stops_on_water(self):
    """RETURNING: peek=None (coast) → shift + HOMING."""
    nav = make_navigator()
    nav._state = 'RETURNING'
    nav._return_steps = 10
    nav._inland_vec = (1.0, 0.0)
    with patch.object(nav, '_peek_step', return_value=None):
        with patch.object(nav, '_shift_click') as mock_shift:
            nav.step()
    mock_shift.assert_called_once()
    assert nav._state == 'HOMING'

def test_returning_continues_on_land(self):
    """RETURNING: peek=1.0 (land ahead) → continues."""
    nav = make_navigator()
    nav._state = 'RETURNING'
    nav._return_steps = 10
    nav._inland_vec = (1.0, 0.0)
    with patch.object(nav, '_peek_step', return_value=1.0):
        with patch.object(nav, '_move_perpendicular'):
            nav.step()
    assert nav._state == 'RETURNING'
```

- [ ] **Step 9: Commit**

```
cd C:\BattleBot && git add navigator.py test_coastal_snake.py && git commit -m "feat: peek-before-step in DIVING and RETURNING — jump water, stop at ocean/coast"
```
