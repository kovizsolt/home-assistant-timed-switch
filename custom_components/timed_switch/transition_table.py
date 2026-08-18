# --------------------------------------------------------------------------------------------------
# File          : custom_components/timed_switch/transition_table.py
#
# A SPEC.md B3.A (FŐ gép) és B3.B (ELERHETOSEGI gép) átmeneti táblái ADATKÉNT, valamint a
# B3.1 entry/exit akciók. Szándékosan a SPEC.md táblák sorrendjét/celláit követi 1:1, hogy a
# kettő egymás mellé tehető legyen (SPEC.md A2/5).
#
# A tényleges akció-implementációkat (mit jelent "kapcsoló BE", "timer indítása" stb.) a
# Controller adja meg egy MainActions / AvailActions objektumon keresztül — ez a fájl csak a
# (állapot, esemény) -> (célállapot, [akciók], guard) VÁZAT rögzíti, hogy elkerüljük a
# controller.py <-> transition_table.py körkörös importot.
# --------------------------------------------------------------------------------------------------
from __future__ import annotations

from typing import Protocol

from .const import (
    AVAIL_AVAILABLE,
    AVAIL_UNAVAILABLE,
    EVT_BECAME_AVAILABLE,
    EVT_BECAME_UNAVAILABLE,
    EVT_MANUAL_CHANGE_OFF,
    EVT_MANUAL_CHANGE_ON,
    EVT_MANUAL_TIMEOUT_EXPIRED,
    EVT_OVERRIDE_CLEARED,
    EVT_OVERRIDE_SET,
    EVT_SCHEDULE_OFF,
    EVT_SCHEDULE_ON,
    EVT_STATE_SYNC,
    STATE_AUTO,
    STATE_MANUAL,
)
from .state_machine import StateActions, Transition, TransitionTable


class MainActions(Protocol):
    """A FŐ gép (B3.A/B3.1) akcióinak szerződése — a Controller implementálja."""

    async def noop(self, ctx) -> None: ...
    async def set_timed_on(self, ctx) -> None: ...
    async def set_timed_off(self, ctx) -> None: ...
    async def set_expected_on(self, ctx) -> None: ...
    async def set_expected_off(self, ctx) -> None: ...
    async def sync_device_if_needed(self, ctx) -> None: ...
    async def restart_manual_timer_if_needed(self, ctx) -> None: ...
    async def start_manual_timer_if_needed(self, ctx) -> None: ...
    async def clear_manual_timer(self, ctx) -> None: ...
    async def resync_expected_from_timed_and_sync_device(self, ctx) -> None: ...

    def manual_timeout_is_zero(self, ctx) -> bool: ...


class AvailActions(Protocol):
    """Az ELERHETOSEGI gép (B3.B) akcióinak szerződése."""

    async def noop(self, ctx) -> None: ...
    async def mark_unavailable(self, ctx) -> None: ...
    async def mark_available(self, ctx) -> None: ...


def build_main_table(a: MainActions) -> TransitionTable:
    """SPEC.md B3.A — FŐ gép átmeneti tábla."""
    return {
        STATE_AUTO: {
            EVT_SCHEDULE_ON: [
                Transition(STATE_AUTO, (a.set_timed_on, a.set_expected_on, a.sync_device_if_needed)),
            ],
            EVT_SCHEDULE_OFF: [
                Transition(STATE_AUTO, (a.set_timed_off, a.set_expected_off, a.sync_device_if_needed)),
            ],
            EVT_MANUAL_CHANGE_ON: [
                Transition(STATE_MANUAL, (a.set_expected_on,)),
            ],
            EVT_MANUAL_CHANGE_OFF: [
                Transition(STATE_MANUAL, (a.set_expected_off,)),
            ],
            EVT_MANUAL_TIMEOUT_EXPIRED: [
                Transition(STATE_AUTO, (a.noop,), label="ignore, nincs aktív felülbírálás"),
            ],
            EVT_OVERRIDE_CLEARED: [
                Transition(STATE_AUTO, (a.noop,), label="ignore, nincs aktív felülbírálás"),
            ],
            EVT_OVERRIDE_SET: [
                Transition(STATE_MANUAL, (a.noop,), label="expected_state és timed_state változatlan"),
            ],
            EVT_STATE_SYNC: [
                Transition(STATE_AUTO, (a.sync_device_if_needed,)),
            ],
        },
        STATE_MANUAL: {
            EVT_SCHEDULE_ON: [
                Transition(
                    STATE_AUTO, (a.set_timed_on,),
                    guard=a.manual_timeout_is_zero,
                    label="manual_timeout==0 → a 0-timeout override lezárul",
                ),
                Transition(STATE_MANUAL, (a.set_timed_on,)),
            ],
            EVT_SCHEDULE_OFF: [
                Transition(
                    STATE_AUTO, (a.set_timed_off,),
                    guard=a.manual_timeout_is_zero,
                    label="manual_timeout==0 → a 0-timeout override lezárul",
                ),
                Transition(STATE_MANUAL, (a.set_timed_off,)),
            ],
            EVT_MANUAL_CHANGE_ON: [
                Transition(STATE_MANUAL, (a.set_expected_on, a.restart_manual_timer_if_needed)),
            ],
            EVT_MANUAL_CHANGE_OFF: [
                Transition(STATE_MANUAL, (a.set_expected_off, a.restart_manual_timer_if_needed)),
            ],
            EVT_MANUAL_TIMEOUT_EXPIRED: [
                Transition(STATE_AUTO, (a.noop,), label="csak manual_timeout>0 esetén fordulhat elő"),
            ],
            EVT_OVERRIDE_CLEARED: [
                Transition(STATE_AUTO, (a.noop,)),
            ],
            EVT_OVERRIDE_SET: [
                Transition(STATE_MANUAL, (a.noop,), label="ignore, már MANUAL"),
            ],
            EVT_STATE_SYNC: [
                Transition(STATE_MANUAL, (a.noop,), label="ignore, felülbírálás alatt a poller nem nyúl a kapcsolóhoz"),
            ],
        },
    }


def build_main_entry_actions(a: MainActions) -> StateActions:
    """SPEC.md B3.1 — belépéskor (entry)."""
    return {
        STATE_AUTO: (a.resync_expected_from_timed_and_sync_device,),
        STATE_MANUAL: (a.start_manual_timer_if_needed,),
    }


def build_main_exit_actions(a: MainActions) -> StateActions:
    """SPEC.md B3.1 — kilépéskor (exit)."""
    return {
        STATE_AUTO: (),
        STATE_MANUAL: (a.clear_manual_timer,),
    }


def build_avail_table(a: AvailActions) -> TransitionTable:
    """SPEC.md B3.B — ELERHETOSEGI gép átmeneti tábla (a FŐ géptől független)."""
    return {
        AVAIL_AVAILABLE: {
            EVT_BECAME_UNAVAILABLE: [
                Transition(AVAIL_UNAVAILABLE, (a.mark_unavailable,)),
            ],
            EVT_BECAME_AVAILABLE: [
                Transition(AVAIL_AVAILABLE, (a.noop,), label="ignore"),
            ],
        },
        AVAIL_UNAVAILABLE: {
            EVT_BECAME_UNAVAILABLE: [
                Transition(AVAIL_UNAVAILABLE, (a.noop,), label="ignore"),
            ],
            EVT_BECAME_AVAILABLE: [
                Transition(AVAIL_AVAILABLE, (a.mark_available,)),
            ],
        },
    }
# --------------------------------------------------------------------------------------------------
# EOF
# --------------------------------------------------------------------------------------------------
