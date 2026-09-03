# --------------------------------------------------------------------------------------------------
# File          : custom_components/timed_switch/controller.py
#
# A Controller osztály: a két állapotgép (FŐ, ELERHETOSEGI) tulajdonosa, ő végzi a
# target_entity_id I/O-t, az időzítéseket (manual_timeout, sync_interval), a cron-motort
# (timed_state/next_schedule), a Store-perzisztenciát (SPEC.md B3.2) és az önhivatkozás
# elleni védelmet (SPEC.md B3.3, HA Context.id).
#
# PREVIEW verzió — SPEC.md alapján, első kör, valós HA-ban tesztelve/finomítva.
# --------------------------------------------------------------------------------------------------
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from croniter import croniter
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Context, HomeAssistant, State, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import storage
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

from .const import (
    AVAIL_UNAVAILABLE,
    CONF_SYNC_INTERVAL,
    CONF_DEFAULT_STATE,
    CONF_MANUAL_TIMEOUT,
    CONF_NAME,
    CONF_OFF_CRONS,
    CONF_ON_CRONS,
    CONF_TARGET_ENTITY_ID,
    DEFAULT_SYNC_INTERVAL,
    DEFAULT_DEFAULT_STATE,
    DEFAULT_MANUAL_TIMEOUT,
    DOMAIN,
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
    LEGACY_CONF_CHECK_INTERVAL,
    SIGNAL_UPDATE,
    STATE_AUTO,
    STATE_MANUAL,
    STORE_KEY,
    STORE_VERSION,
    SUFFIX_VIRTUAL,
)
from .helpers import (
    CronFieldCountError,
    PersistedState,
    evaluate_schedule,
    external_schedule_is_active,
    normalize_cron_list,
    parse_cron_list,
    seconds_until_next_minute,
)
from .state_machine import StateMachine
from .transition_table import (
    build_avail_table,
    build_main_entry_actions,
    build_main_exit_actions,
    build_main_table,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN_SERVICE_TURN_ON = {"switch": "turn_on", "input_boolean": "turn_on", "light": "turn_on", "script": "turn_on"}
DOMAIN_SERVICE_TURN_OFF = {"switch": "turn_off", "input_boolean": "turn_off", "light": "turn_off", "script": "turn_off"}


def virtual_entity_id(entry_id_slug: str) -> str:
    return f"switch.{entry_id_slug}_{SUFFIX_VIRTUAL}"


class Controller:
    """SPEC.md Controller — állapottároló + a két állapotgép orchesztrátora."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, slug: str) -> None:
        self.hass = hass
        self.entry = entry
        self.slug = slug
        self.name: str = entry.data.get(CONF_NAME, entry.title)

        data = {**entry.data, **(entry.options or {})}
        configured_target = data.get(CONF_TARGET_ENTITY_ID) or None
        self.target_entity_id: str = configured_target or virtual_entity_id(slug)
        self.is_virtual_target: bool = configured_target is None
        self.target_domain: str = self.target_entity_id.split(".", 1)[0]

        self.on_crons: list[str] = parse_cron_list(data.get(CONF_ON_CRONS, ""))
        self.off_crons: list[str] = parse_cron_list(data.get(CONF_OFF_CRONS, ""))
        self.manual_timeout: int = int(data.get(CONF_MANUAL_TIMEOUT, DEFAULT_MANUAL_TIMEOUT))
        self.sync_interval: int = int(
            data.get(CONF_SYNC_INTERVAL, data.get(LEGACY_CONF_CHECK_INTERVAL, DEFAULT_SYNC_INTERVAL))
        )
        self.default_state: bool = bool(data.get(CONF_DEFAULT_STATE, DEFAULT_DEFAULT_STATE))

        # --- futásidejű állapot (SPEC.md B1/B2.3) ---
        self.expected_state: bool = self.default_state
        self.timed_state: bool = self.default_state
        self.device_state: Optional[bool] = None
        self.manual_until: Optional[datetime] = None
        self.sync_until: Optional[datetime] = None
        self.next_schedule: Optional[datetime] = None
        self.external_schedule_state: Optional[bool] = None
        self.external_schedule_changed_at: Optional[datetime] = None
        self.since_last_change: Optional[datetime] = None
        self.device_last_changed: Optional[datetime] = None
        self._expected_just_changed: bool = False

        self._last_own_context_id: Optional[str] = None
        self._manual_timer_cancel = None
        self._poller_cancel = None
        self._cron_cancel = None
        self._unsub_state_changed = None

        self._store = storage.Store(hass, STORE_VERSION, f"{DOMAIN}/{entry.entry_id}/{STORE_KEY}.json")
        self._signal = f"{SIGNAL_UPDATE}_{entry.entry_id}"

        self.main = StateMachine(
            "FŐ gép", build_main_table(self), STATE_AUTO,
            build_main_entry_actions(self), build_main_exit_actions(self),
        )
        # SPEC.md B2.1b / B3.2 #8: mindig UNAVAILABLE-lel indul, nem perzisztált.
        self.avail = StateMachine("ELERHETOSEGI gép", build_avail_table(self), AVAIL_UNAVAILABLE)

    # ------------------------------------------------------------------ setup / unload -----

    async def async_setup(self) -> None:
        now = dt_util.utcnow()
        # A cron-kifejezéseket a HA-ban konfigurált HELYI időzónában kell kiértékelni (a
        # felhasználó "0 8 * * *"-t helyi 8:00-ra ír, nem UTC-re) — ezért itt szándékosan
        # dt_util.now() (local), NEM dt_util.utcnow(). Minden más (perzisztált abszolút
        # időpontok, since/device_last_changed) továbbra is UTC-ben marad.
        sched = evaluate_schedule(self.on_crons, self.off_crons, dt_util.now())
        self.next_schedule = sched.next_schedule

        persisted = PersistedState.from_dict(await self._store.async_load())
        if persisted is not None:
            self.external_schedule_state = persisted.external_schedule_state
            self.external_schedule_changed_at = _parse_iso(
                persisted.external_schedule_changed_at
            )
        if self.external_schedule_state is not None and external_schedule_is_active(
            self.external_schedule_changed_at, sched.last_schedule
        ):
            self.timed_state = bool(self.external_schedule_state)
        else:
            self.external_schedule_state = None
            self.external_schedule_changed_at = None
            self.timed_state = (
                sched.timed_state
                if sched.timed_state is not None
                else self.default_state
            )
        if persisted is None:
            self.main.state = STATE_AUTO
            self.expected_state = self.default_state
        elif persisted.main_state == STATE_MANUAL:
            manual_until = _parse_iso(persisted.manual_until)
            if manual_until is not None and manual_until <= now:
                # SPEC.md B3.2/#5: a lejárat már elmúlt a kiesés alatt → AUTO
                self.main.state = STATE_AUTO
                self.expected_state = self.timed_state
            else:
                self.main.state = STATE_MANUAL
                self.expected_state = persisted.expected_state
                self.manual_until = manual_until
                if manual_until is not None:
                    self._schedule_manual_expiry()
        else:
            self.main.state = STATE_AUTO
            self.expected_state = self.timed_state

        self.since_last_change = now

        if self.target_domain != "button":
            self._unsub_state_changed = async_track_state_change_event(
                self.hass, [self.target_entity_id], self._on_target_state_changed_event
            )
            self._apply_initial_device_state(self.hass.states.get(self.target_entity_id))
        else:
            # SPEC.md B3.4/#5: a button entitásnak van available/unavailable állapota, ez
            # független a device_state megfigyeléstől — csak az elérhetőséget figyeljük.
            self._unsub_state_changed = async_track_state_change_event(
                self.hass, [self.target_entity_id], self._on_target_availability_only_event
            )
            self._apply_initial_availability_only(self.hass.states.get(self.target_entity_id))

        self._start_cron_ticker()
        self._start_poller()

        if self.main.state == STATE_AUTO:
            await self.sync_device_if_needed(self)

        await self.async_save()

    async def async_unload(self) -> None:
        if self._unsub_state_changed:
            self._unsub_state_changed()
        for cancel in (
            self._manual_timer_cancel,
            self._poller_cancel,
            self._cron_cancel,
        ):
            if cancel:
                cancel()

    async def async_save(self) -> None:
        manual_until_iso = self.manual_until.isoformat() if self.manual_until else None
        external_changed_at_iso = (
            self.external_schedule_changed_at.isoformat()
            if self.external_schedule_changed_at
            else None
        )
        await self._store.async_save(
            PersistedState(
                self.main.state,
                self.expected_state,
                manual_until_iso,
                self.external_schedule_state,
                external_changed_at_iso,
            ).to_dict()
        )

    # ------------------------------------------------------------------ MainActions --------

    async def noop(self, ctx) -> None:
        return

    async def set_timed_on(self, ctx) -> None:
        self.timed_state = True

    async def set_timed_off(self, ctx) -> None:
        self.timed_state = False

    async def set_expected_on(self, ctx) -> None:
        self._set_expected(True)

    async def set_expected_off(self, ctx) -> None:
        self._set_expected(False)

    def _set_expected(self, value: bool) -> None:
        changed = value != self.expected_state
        self.expected_state = value
        self._expected_just_changed = changed
        if changed:
            self.since_last_change = dt_util.utcnow()

    async def resync_expected_from_timed_and_sync_device(self, ctx) -> None:
        """SPEC.md B3.1 — AUTO belépéskor: expected_state := pillanatnyi timed_state."""
        self._set_expected(self.timed_state)
        await self.sync_device_if_needed(ctx)

    async def sync_device_if_needed(self, ctx) -> None:
        """[guard: device_state != expected_state] → kapcsoló beállítása. Button célnál a
        SPEC.md B3.4 speciális szabálya: csak akkor press, ha expected_state EBBEN az
        eseményben ténylegesen változott (a poller sosem vált ki akciót, lásd B3.4/#3)."""
        if self.target_domain == "button":
            if self._expected_just_changed:
                await self._call_service_press()
            return
        if self.device_state != self.expected_state:
            await self._call_service_turn(self.expected_state)

    async def restart_manual_timer_if_needed(self, ctx) -> None:
        if self.manual_timeout > 0:
            self.manual_until = dt_util.utcnow() + timedelta(seconds=self.manual_timeout)
            self._schedule_manual_expiry()
        else:
            self.manual_until = None
            self._cancel_manual_timer()

    async def start_manual_timer_if_needed(self, ctx) -> None:
        await self.restart_manual_timer_if_needed(ctx)

    async def clear_manual_timer(self, ctx) -> None:
        self._cancel_manual_timer()
        self.manual_until = None

    def manual_timeout_is_zero(self, ctx) -> bool:
        return self.manual_timeout == 0

    # ------------------------------------------------------------------ AvailActions -------

    async def mark_unavailable(self, ctx) -> None:
        _LOGGER.info("[%s] ELERHETOSEGI: AVAILABLE -> UNAVAILABLE (%s)", self.name, self.target_entity_id)

    async def mark_available(self, ctx) -> None:
        _LOGGER.info("[%s] ELERHETOSEGI: UNAVAILABLE -> AVAILABLE (%s)", self.name, self.target_entity_id)

    # ------------------------------------------------------------------ platform entitások hívják --

    async def async_toggle_timed_state(self, value: bool) -> None:
        self.external_schedule_state = value
        self.external_schedule_changed_at = dt_util.utcnow()
        await self.main.handle(EVT_SCHEDULE_ON if value else EVT_SCHEDULE_OFF, self)
        await self.async_save()
        await self._notify()

    async def async_toggle_expected(self, value: bool) -> None:
        await self.main.handle(EVT_MANUAL_CHANGE_ON if value else EVT_MANUAL_CHANGE_OFF, self)
        await self.sync_device_if_needed(self)
        await self.async_save()
        await self._notify()

    async def async_toggle_device(self, value: bool) -> None:
        await self.main.handle(EVT_MANUAL_CHANGE_ON if value else EVT_MANUAL_CHANGE_OFF, self)
        await self.sync_device_if_needed(self)
        await self.async_save()
        await self._notify()

    async def async_toggle_manual_mode(self, value: bool) -> None:
        await self.main.handle(EVT_OVERRIDE_SET if value else EVT_OVERRIDE_CLEARED, self)
        await self.async_save()
        await self._notify()

    async def async_set_manual_timeout(self, seconds: int) -> None:
        self.manual_timeout = max(0, int(seconds))
        await self._notify()

    async def async_set_sync_interval(self, seconds: int) -> None:
        self.sync_interval = max(0, int(seconds))
        self._start_poller()
        await self._notify()

    # ------------------------------------------------------------------ target_entity_id I/O -----

    async def _call_service_turn(self, on: bool) -> None:
        ctx = Context()
        self._last_own_context_id = ctx.id
        service = DOMAIN_SERVICE_TURN_ON[self.target_domain] if on else DOMAIN_SERVICE_TURN_OFF[self.target_domain]
        await self.hass.services.async_call(
            self.target_domain, service, {"entity_id": self.target_entity_id}, blocking=False, context=ctx
        )

    async def _call_service_press(self) -> None:
        ctx = Context()
        self._last_own_context_id = ctx.id
        await self.hass.services.async_call(
            "button", "press", {"entity_id": self.target_entity_id}, blocking=False, context=ctx
        )
        self.device_last_changed = dt_util.utcnow()

    def _apply_initial_device_state(self, state: Optional[State]) -> None:
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return
        self.device_state = state.state == STATE_ON
        self.device_last_changed = dt_util.utcnow()
        self.hass.async_create_task(self.avail.handle(EVT_BECAME_AVAILABLE, self))

    def _apply_initial_availability_only(self, state: Optional[State]) -> None:
        if state is not None and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self.hass.async_create_task(self.avail.handle(EVT_BECAME_AVAILABLE, self))

    @callback
    def _on_target_state_changed_event(self, event) -> None:
        self.hass.async_create_task(self._async_on_target_state_changed(event))

    async def _async_on_target_state_changed(self, event) -> None:
        old: Optional[State] = event.data.get("old_state")
        new: Optional[State] = event.data.get("new_state")
        if new is None:
            return

        old_unavail = old is None or old.state in (STATE_UNAVAILABLE, STATE_UNKNOWN)
        new_unavail = new.state in (STATE_UNAVAILABLE, STATE_UNKNOWN)

        if new_unavail:
            if not old_unavail:
                await self.avail.handle(EVT_BECAME_UNAVAILABLE, self)
                await self._notify()
            return

        new_bool = new.state == STATE_ON
        self.device_state = new_bool
        self.device_last_changed = dt_util.utcnow()

        if old_unavail:
            # SPEC.md B2.2/#3-4 kizárás + B4/15: visszakapcsolódás sosem manual_change.
            await self.avail.handle(EVT_BECAME_AVAILABLE, self)
            await self._notify()
            return

        if new.context is not None and new.context.id == self._last_own_context_id:
            # SPEC.md B3.3: saját service call echója, elnyelve.
            await self._notify()
            return

        await self.main.handle(EVT_MANUAL_CHANGE_ON if new_bool else EVT_MANUAL_CHANGE_OFF, self)
        await self.async_save()
        await self._notify()

    @callback
    def _on_target_availability_only_event(self, event) -> None:
        old: Optional[State] = event.data.get("old_state")
        new: Optional[State] = event.data.get("new_state")
        if new is None:
            return
        old_unavail = old is None or old.state in (STATE_UNAVAILABLE, STATE_UNKNOWN)
        new_unavail = new.state in (STATE_UNAVAILABLE, STATE_UNKNOWN)
        if new_unavail and not old_unavail:
            self.hass.async_create_task(self.avail.handle(EVT_BECAME_UNAVAILABLE, self))
            self.hass.async_create_task(self._notify())
        elif old_unavail and not new_unavail:
            self.hass.async_create_task(self.avail.handle(EVT_BECAME_AVAILABLE, self))
            self.hass.async_create_task(self._notify())

    # ------------------------------------------------------------------ időzítők -----------------

    def _start_poller(self) -> None:
        if self._poller_cancel:
            self._poller_cancel()
            self._poller_cancel = None
        self.sync_until = None
        if self.sync_interval > 0:
            self.sync_until = dt_util.utcnow() + timedelta(seconds=self.sync_interval)
            self._poller_cancel = async_track_time_interval(
                self.hass, self._async_poll, timedelta(seconds=self.sync_interval)
            )

    async def _async_poll(self, _now) -> None:
        self.sync_until = dt_util.utcnow() + timedelta(seconds=self.sync_interval)
        self._expected_just_changed = False
        await self.main.handle(EVT_STATE_SYNC, self)
        await self._notify()

    def _start_cron_ticker(self) -> None:
        if self._cron_cancel:
            self._cron_cancel()
            self._cron_cancel = None
        self._schedule_next_cron_tick()

    def _schedule_next_cron_tick(self) -> None:
        """Use a monotonic delay, recalculated from the current wall clock each minute."""
        self._cron_cancel = async_call_later(
            self.hass,
            seconds_until_next_minute(dt_util.now()),
            self._async_cron_timer_fired,
        )

    async def _async_cron_timer_fired(self, now) -> None:
        # Rearm before evaluation so an exception cannot permanently stop the ticker.
        # Recalculating from the current wall clock also recovers from clock jumps in
        # at most one monotonic interval instead of waiting for an obsolete timestamp.
        self._cron_cancel = None
        self._schedule_next_cron_tick()
        await self._async_cron_tick(now)

    async def _async_cron_tick(self, _now) -> None:
        if not self.on_crons and not self.off_crons:
            # SPEC.md B2.4: üres lista → nincs időzítés, timed_state sosem változik.
            # Korábbi hiba volt: ilyenkor default_state-re "korrigáltuk" volna vissza,
            # ami hamis schedule_on/off eseményt generált minden tick-nél.
            self.next_schedule = None
            await self._notify()
            return
        # ld. async_setup megjegyzését: a cron-kiértékelés helyi időben fut, nem UTC-ben.
        sched = evaluate_schedule(self.on_crons, self.off_crons, dt_util.now())
        self.next_schedule = sched.next_schedule
        if sched.timed_state is None:
            return
        external_was_active = self.external_schedule_changed_at is not None
        external_is_active = external_schedule_is_active(
            self.external_schedule_changed_at, sched.last_schedule
        )
        if external_is_active:
            await self._notify()
            return
        if external_was_active:
            self.external_schedule_state = None
            self.external_schedule_changed_at = None
        if external_was_active or sched.timed_state != self.timed_state:
            self._expected_just_changed = False
            await self.main.handle(EVT_SCHEDULE_ON if sched.timed_state else EVT_SCHEDULE_OFF, self)
            await self.async_save()
        await self._notify()

    async def async_set_cron_list(self, key: str, value: str) -> None:
        """Apply and persist an ON/OFF cron list edited through its text entity."""
        schedule_name = "ON" if key == CONF_ON_CRONS else "OFF"
        try:
            normalized_value = normalize_cron_list(value)
        except CronFieldCountError as err:
            expression = str(err)
            line_number = next(
                (number for number, line in enumerate(value.splitlines(), start=1)
                 if expression in line.split("#", maxsplit=1)[0]),
                1,
            )
            raise ServiceValidationError(
                f'Hibás {schedule_name} időzítés a(z) {line_number}. sorban: '
                f'"{expression}". A cron-kifejezés legfeljebb 5 mezőt tartalmazhat; '
                "az extra mezők csak * értékűek lehetnek."
            ) from err
        parsed = parse_cron_list(normalized_value)
        for line_number, line in enumerate(normalized_value.splitlines(), start=1):
            uncommented = line.split("#", maxsplit=1)[0]
            for expression in (part.strip() for part in uncommented.split(",")):
                if not expression:
                    continue
                try:
                    croniter(expression, dt_util.now())
                except Exception as err:
                    raise ServiceValidationError(
                        f'Hibás {schedule_name} időzítés a(z) {line_number}. sorban: '
                        f'"{expression}". {err}'
                    ) from err
        if key == CONF_ON_CRONS:
            self.on_crons = parsed
        elif key == CONF_OFF_CRONS:
            self.off_crons = parsed
        else:
            raise ValueError(f"Unsupported cron-list key: {key}")

        options = {**(self.entry.options or {}), key: normalized_value}
        self.hass.config_entries.async_update_entry(self.entry, options=options)
        await self._async_cron_tick(dt_util.now())

    def _schedule_manual_expiry(self) -> None:
        self._cancel_manual_timer()
        if self.manual_until is None:
            return
        delay = max(0, (self.manual_until - dt_util.utcnow()).total_seconds())
        self._manual_timer_cancel = async_call_later(self.hass, delay, self._async_manual_expiry)

    async def _async_manual_expiry(self, _now) -> None:
        self._manual_timer_cancel = None
        self._expected_just_changed = False
        await self.main.handle(EVT_MANUAL_TIMEOUT_EXPIRED, self)
        await self.async_save()
        await self._notify()

    def _cancel_manual_timer(self) -> None:
        if self._manual_timer_cancel:
            self._manual_timer_cancel()
            self._manual_timer_cancel = None

    # ------------------------------------------------------------------ derived / notify ---------

    @property
    def is_manual(self) -> bool:
        return self.main.state == STATE_MANUAL

    @property
    def avail_state(self) -> str:
        return self.avail.state

    @property
    def manual_remaining_seconds(self) -> Optional[int]:
        if self.main.state != STATE_MANUAL or self.manual_until is None:
            return None
        return max(0, int((self.manual_until - dt_util.utcnow()).total_seconds()))

    @property
    def sync_remaining_seconds(self) -> Optional[int]:
        if self.sync_interval <= 0 or self.sync_until is None:
            return None
        return max(0, int((self.sync_until - dt_util.utcnow()).total_seconds()))

    async def _notify(self) -> None:
        # async_dispatcher_send ebben a HA verzióban @callback (szinkron), nem awaitolható.
        async_dispatcher_send(self.hass, self._signal)


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
# --------------------------------------------------------------------------------------------------
# EOF
# --------------------------------------------------------------------------------------------------
