# --------------------------------------------------------------------------------------------------
# File          : tests/test_transitions.py
#
# SPEC.md B5 elfogadási tesztek — a tiszta állapotgép-logikát (state_machine.py +
# transition_table.py) teszteli, HA futásidő nélkül (nincs homeassistant/pytest függőség
# ebben a fejlesztői környezetben — unittest + asyncio.run-nal fut).
#
# Amit ez a fájl NEM tesztel (mert HA-futásidőt igényel — a docker dev/teszt környezetben
# validáljuk élőben): context-echo suppression (B3.3, HA Context), unavailable-visszatérés
# kizárás (B4/15), button domain service-hívások (B3.4), entitás-huzalozás.
# --------------------------------------------------------------------------------------------------
import asyncio
import importlib.util
import os
import sys
import types
import unittest

# A custom_components/timed_switch/__init__.py a homeassistant csomagot importálja
# (ami ebben a fejlesztői környezetben nincs telepítve) — ezért a const/state_machine/
# transition_table modulokat közvetlenül, fájl alapján töltjük be, egy üres "fake"
# csomag alá regisztrálva, hogy a bennük lévő relatív importok (`from .const import ...`)
# feloldódjanak anélkül, hogy a valódi __init__.py lefutna.
_PKG_DIR = os.path.join(os.path.dirname(__file__), "..", "custom_components", "timed_switch")
_PKG_NAME = "_timed_switch_under_test"

_pkg = types.ModuleType(_PKG_NAME)
_pkg.__path__ = [_PKG_DIR]
sys.modules[_PKG_NAME] = _pkg


def _load(modname: str) -> types.ModuleType:
    full_name = f"{_PKG_NAME}.{modname}"
    spec = importlib.util.spec_from_file_location(full_name, os.path.join(_PKG_DIR, f"{modname}.py"))
    module = importlib.util.module_from_spec(spec)
    module.__package__ = _PKG_NAME
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


const = _load("const")
state_machine = _load("state_machine")
transition_table = _load("transition_table")

AVAIL_AVAILABLE = const.AVAIL_AVAILABLE
AVAIL_UNAVAILABLE = const.AVAIL_UNAVAILABLE
EVT_BECAME_AVAILABLE = const.EVT_BECAME_AVAILABLE
EVT_BECAME_UNAVAILABLE = const.EVT_BECAME_UNAVAILABLE
EVT_MANUAL_CHANGE_OFF = const.EVT_MANUAL_CHANGE_OFF
EVT_MANUAL_CHANGE_ON = const.EVT_MANUAL_CHANGE_ON
EVT_MANUAL_TIMEOUT_EXPIRED = const.EVT_MANUAL_TIMEOUT_EXPIRED
EVT_OVERRIDE_CLEARED = const.EVT_OVERRIDE_CLEARED
EVT_OVERRIDE_SET = const.EVT_OVERRIDE_SET
EVT_SCHEDULE_OFF = const.EVT_SCHEDULE_OFF
EVT_SCHEDULE_ON = const.EVT_SCHEDULE_ON
EVT_STATE_SYNC = const.EVT_STATE_SYNC
STATE_AUTO = const.STATE_AUTO
STATE_MANUAL = const.STATE_MANUAL

StateMachine = state_machine.StateMachine
build_avail_table = transition_table.build_avail_table
build_main_entry_actions = transition_table.build_main_entry_actions
build_main_exit_actions = transition_table.build_main_exit_actions
build_main_table = transition_table.build_main_table


class FakeMain:
    """Egyszerű, HA nélküli MainActions-implementáció teszteléshez."""

    def __init__(self, manual_timeout: int = 600):
        self.manual_timeout = manual_timeout
        self.expected_state = False
        self.timed_state = False
        self.device_state = False
        self.timer_running = False
        self.calls: list[str] = []

    async def noop(self, ctx):
        self.calls.append("noop")

    async def set_timed_on(self, ctx):
        self.timed_state = True
        self.calls.append("timed=on")

    async def set_timed_off(self, ctx):
        self.timed_state = False
        self.calls.append("timed=off")

    async def set_expected_on(self, ctx):
        self.expected_state = True
        self.calls.append("expected=on")

    async def set_expected_off(self, ctx):
        self.expected_state = False
        self.calls.append("expected=off")

    async def sync_device_if_needed(self, ctx):
        if self.device_state != self.expected_state:
            self.device_state = self.expected_state
            self.calls.append(f"device_sync->{self.expected_state}")

    async def restart_manual_timer_if_needed(self, ctx):
        if self.manual_timeout > 0:
            self.timer_running = True
            self.calls.append("timer_restart")
        else:
            self.timer_running = False

    async def start_manual_timer_if_needed(self, ctx):
        await self.restart_manual_timer_if_needed(ctx)

    async def clear_manual_timer(self, ctx):
        self.timer_running = False
        self.calls.append("timer_clear")

    async def resync_expected_from_timed_and_sync_device(self, ctx):
        self.expected_state = self.timed_state
        self.calls.append(f"resync_expected={self.timed_state}")
        await self.sync_device_if_needed(ctx)

    def manual_timeout_is_zero(self, ctx) -> bool:
        return self.manual_timeout == 0


class FakeAvail:
    def __init__(self):
        self.calls: list[str] = []

    async def noop(self, ctx):
        self.calls.append("noop")

    async def mark_unavailable(self, ctx):
        self.calls.append("mark_unavailable")

    async def mark_available(self, ctx):
        self.calls.append("mark_available")


def make_main(manual_timeout: int = 600, initial_state: str = STATE_AUTO):
    fake = FakeMain(manual_timeout)
    machine = StateMachine(
        "FŐ gép", build_main_table(fake), initial_state,
        build_main_entry_actions(fake), build_main_exit_actions(fake),
    )
    return machine, fake


def make_avail(initial_state: str = AVAIL_AVAILABLE):
    fake = FakeAvail()
    machine = StateMachine("ELERHETOSEGI gép", build_avail_table(fake), initial_state)
    return machine, fake


def run(coro):
    return asyncio.run(coro)


class MainMachineTests(unittest.TestCase):
    """SPEC.md B5 — FŐ gép."""

    def test_T1_auto_schedule_on(self):
        m, f = make_main(initial_state=STATE_AUTO)
        f.device_state = False
        f.expected_state = False
        run(m.handle(EVT_SCHEDULE_ON, f))
        self.assertEqual(m.state, STATE_AUTO)
        self.assertTrue(f.expected_state)
        self.assertTrue(f.device_state)

    def test_T2_auto_to_manual_on_manual_change(self):
        m, f = make_main(manual_timeout=600, initial_state=STATE_AUTO)
        f.device_state = True
        f.expected_state = True
        run(m.handle(EVT_MANUAL_CHANGE_OFF, f))
        self.assertEqual(m.state, STATE_MANUAL)
        self.assertFalse(f.expected_state)
        self.assertTrue(f.timer_running)

    def test_T3_manual_timeout_expired_syncs_device(self):
        m, f = make_main(manual_timeout=600, initial_state=STATE_MANUAL)
        f.expected_state = False
        f.timed_state = False
        f.device_state = True  # eltér, a belépő akciónak vissza kell állítania
        run(m.handle(EVT_MANUAL_TIMEOUT_EXPIRED, f))
        self.assertEqual(m.state, STATE_AUTO)
        self.assertFalse(f.device_state)

    def test_T4_manual_schedule_on_only_moves_timed_state(self):
        m, f = make_main(manual_timeout=600, initial_state=STATE_MANUAL)
        f.expected_state = False
        f.timed_state = False
        f.device_state = False
        run(m.handle(EVT_SCHEDULE_ON, f))
        self.assertEqual(m.state, STATE_MANUAL)
        self.assertTrue(f.timed_state)
        self.assertFalse(f.expected_state)  # változatlan
        self.assertFalse(f.device_state)  # nincs service call

    def test_T6_override_cleared_syncs_device(self):
        m, f = make_main(manual_timeout=600, initial_state=STATE_MANUAL)
        f.expected_state = True
        f.timed_state = True
        f.device_state = False
        run(m.handle(EVT_OVERRIDE_CLEARED, f))
        self.assertEqual(m.state, STATE_AUTO)
        self.assertTrue(f.device_state)

    def test_T8_manual_change_on_repeated_with_zero_timeout_never_times_out(self):
        m, f = make_main(manual_timeout=0, initial_state=STATE_MANUAL)
        f.expected_state = False
        run(m.handle(EVT_MANUAL_CHANGE_ON, f))
        self.assertEqual(m.state, STATE_MANUAL)
        self.assertTrue(f.expected_state)
        self.assertFalse(f.timer_running)

    def test_T9_zero_timeout_closed_by_schedule(self):
        m, f = make_main(manual_timeout=0, initial_state=STATE_MANUAL)
        f.expected_state = False
        f.timed_state = False
        f.device_state = False
        run(m.handle(EVT_SCHEDULE_ON, f))
        self.assertEqual(m.state, STATE_AUTO)
        self.assertTrue(f.expected_state)
        self.assertTrue(f.device_state)

    def test_N1_state_sync_idempotent_when_synced(self):
        m, f = make_main(initial_state=STATE_AUTO)
        f.expected_state = True
        f.device_state = True
        run(m.handle(EVT_STATE_SYNC, f))
        self.assertEqual(m.state, STATE_AUTO)
        self.assertNotIn("device_sync->True", f.calls)

    def test_N2_manual_state_sync_is_noop(self):
        m, f = make_main(manual_timeout=600, initial_state=STATE_MANUAL)
        f.expected_state = True
        f.device_state = False  # szándékos eltérés — a pollernek NEM szabad hozzányúlnia
        run(m.handle(EVT_STATE_SYNC, f))
        self.assertEqual(m.state, STATE_MANUAL)
        self.assertFalse(f.device_state)

    def test_N3_override_set_repeated_is_noop(self):
        m, f = make_main(manual_timeout=600, initial_state=STATE_MANUAL)
        run(m.handle(EVT_OVERRIDE_SET, f))
        self.assertEqual(m.state, STATE_MANUAL)
        self.assertEqual(f.calls, ["noop"])

    def test_T17_timed_state_manual_toggle_behaves_like_real_schedule_on(self):
        """switch.<name>_timed_state kézi átbillentése == valódi schedule_on (SPEC.md B2.2/#1)."""
        m, f = make_main(initial_state=STATE_AUTO)
        run(m.handle(EVT_SCHEDULE_ON, f))
        self.assertTrue(f.timed_state)
        self.assertTrue(f.expected_state)
        self.assertTrue(f.device_state)


class AvailMachineTests(unittest.TestCase):
    """SPEC.md B5 — ELERHETOSEGI gép."""

    def test_became_unavailable(self):
        m, f = make_avail(AVAIL_AVAILABLE)
        run(m.handle(EVT_BECAME_UNAVAILABLE, f))
        self.assertEqual(m.state, AVAIL_UNAVAILABLE)
        self.assertIn("mark_unavailable", f.calls)

    def test_became_available(self):
        m, f = make_avail(AVAIL_UNAVAILABLE)
        run(m.handle(EVT_BECAME_AVAILABLE, f))
        self.assertEqual(m.state, AVAIL_AVAILABLE)
        self.assertIn("mark_available", f.calls)

    def test_ignore_repeated_unavailable(self):
        m, f = make_avail(AVAIL_UNAVAILABLE)
        run(m.handle(EVT_BECAME_UNAVAILABLE, f))
        self.assertEqual(m.state, AVAIL_UNAVAILABLE)
        self.assertEqual(f.calls, ["noop"])


class TableCompletenessTests(unittest.TestCase):
    """SPEC.md A2/1 — 'üres cella = garantált hiba': minden (állapot, esemény) párnak
    lennie kell legalább egy, guard=None-nal végződő ágnak."""

    def test_main_table_every_cell_has_fallback(self):
        f = FakeMain()
        table = build_main_table(f)
        events = [
            EVT_SCHEDULE_ON, EVT_SCHEDULE_OFF, EVT_MANUAL_CHANGE_ON, EVT_MANUAL_CHANGE_OFF,
            EVT_MANUAL_TIMEOUT_EXPIRED, EVT_OVERRIDE_CLEARED, EVT_OVERRIDE_SET, EVT_STATE_SYNC,
        ]
        for state in (STATE_AUTO, STATE_MANUAL):
            for event in events:
                cell = table[state][event]
                self.assertTrue(any(t.guard is None for t in cell), f"{state}/{event}: nincs fallback ág")

    def test_avail_table_every_cell_present(self):
        f = FakeAvail()
        table = build_avail_table(f)
        for state in (AVAIL_AVAILABLE, AVAIL_UNAVAILABLE):
            for event in (EVT_BECAME_UNAVAILABLE, EVT_BECAME_AVAILABLE):
                self.assertIn(event, table[state])


if __name__ == "__main__":
    unittest.main()
# --------------------------------------------------------------------------------------------------
# EOF
# --------------------------------------------------------------------------------------------------
