# --------------------------------------------------------------------------------------------------
# File          : custom_components/timed_switch/switch.py
#
# SPEC.md B2.3 switch entitások: _expected, _timed_state, _is_manual_mode, _device, _virtual.
# --------------------------------------------------------------------------------------------------
from __future__ import annotations

from typing import Any, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory

from .const import (
    AVAIL_AVAILABLE,
    ATTR_DEVICE_AVAILABLE,
    ATTR_EXTERNAL_SCHEDULE_ACTIVE,
    ATTR_NEXT_SCHEDULE,
    DOMAIN,
    SUFFIX_DEVICE,
    SUFFIX_EXPECTED,
    SUFFIX_IS_MANUAL_MODE,
    SUFFIX_TIMED_STATE,
    SUFFIX_VIRTUAL,
)
from .controller import Controller


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    bucket = hass.data[DOMAIN][entry.entry_id]
    controller: Controller = bucket["controller"]
    slug: str = bucket["slug"]

    entities: list[SwitchEntity] = [
        ExpectedSwitch(controller, slug),
        TimedStateSwitch(controller, slug),
        IsManualModeSwitch(controller, slug),
    ]

    if controller.is_virtual_target:
        entities.append(VirtualSwitch(controller, slug))

    if controller.target_domain != "button":
        entities.append(DeviceSwitch(controller, slug))

    async_add_entities(entities)


class _BaseControllerSwitch(SwitchEntity):
    """Közös alap: fix entity_id, dispatcher-alapú frissítés (SPEC.md B2.3 saját entitások)."""

    _attr_should_poll = False
    _attr_has_entity_name = False

    def __init__(self, controller: Controller, slug: str, suffix: str, name_suffix: str) -> None:
        self._controller = controller
        self.entity_id = f"switch.{slug}_{suffix}"
        self._attr_unique_id = f"{controller.entry.entry_id}_{suffix}"
        self._attr_name = f"{controller.name} {name_suffix}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._controller.entry.entry_id)}, name=self._controller.name)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._controller._signal, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class ExpectedSwitch(_BaseControllerSwitch):
    """switch.<slug>_expected — SPEC.md B2.3."""

    def __init__(self, controller: Controller, slug: str) -> None:
        super().__init__(controller, slug, SUFFIX_EXPECTED, "Expected")
        self._attr_icon = "mdi:target"

    @property
    def is_on(self) -> bool:
        return self._controller.expected_state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {ATTR_DEVICE_AVAILABLE: self._controller.avail_state == AVAIL_AVAILABLE}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._controller.async_toggle_expected(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._controller.async_toggle_expected(False)


class TimedStateSwitch(_BaseControllerSwitch):
    """switch.<slug>_timed_state — SPEC.md B2.3."""

    def __init__(self, controller: Controller, slug: str) -> None:
        super().__init__(controller, slug, SUFFIX_TIMED_STATE, "Timed State")
        self._attr_icon = "mdi:calendar-clock"

    @property
    def is_on(self) -> bool:
        return self._controller.timed_state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        next_schedule = self._controller.next_schedule
        # ISO marad a transport formátum; a dashboard-kártya a felhasználó HA locale-,
        # dátum-, idő- és időzóna-beállítása szerint jeleníti meg.
        return {
            ATTR_NEXT_SCHEDULE: next_schedule.isoformat() if next_schedule else "--",
            ATTR_EXTERNAL_SCHEDULE_ACTIVE: (
                self._controller.external_schedule_changed_at is not None
            ),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._controller.async_toggle_timed_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._controller.async_toggle_timed_state(False)


class IsManualModeSwitch(_BaseControllerSwitch):
    """switch.<slug>_is_manual_mode — SPEC.md B2.3."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, controller: Controller, slug: str) -> None:
        super().__init__(controller, slug, SUFFIX_IS_MANUAL_MODE, "Manual Mode")
        self._attr_icon = "mdi:hand-back-right"

    @property
    def is_on(self) -> bool:
        return self._controller.is_manual

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._controller.async_toggle_manual_mode(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._controller.async_toggle_manual_mode(False)


class DeviceSwitch(_BaseControllerSwitch):
    """switch.<slug>_device — a target_entity_id kétirányú tükre (SPEC.md B2.3)."""

    def __init__(self, controller: Controller, slug: str) -> None:
        super().__init__(controller, slug, SUFFIX_DEVICE, "Device")
        self._attr_icon = "mdi:power-plug"

    @property
    def is_on(self) -> Optional[bool]:
        return self._controller.device_state

    @property
    def available(self) -> bool:
        return self._controller.avail_state == AVAIL_AVAILABLE

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._controller.async_toggle_device(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._controller.async_toggle_device(False)


class VirtualSwitch(SwitchEntity):
    """switch.<slug>_virtual — valódi, önálló HA switch, ha nincs külső target_entity_id
    megadva (SPEC.md B2.3). Szándékosan NEM a Controlleren keresztül él — úgy viselkedik,
    mintha fizikai eszköz lenne, a Controller passzívan, state_changed-en át figyeli."""

    _attr_should_poll = False
    _attr_has_entity_name = False
    _attr_is_on = False

    def __init__(self, controller: Controller, slug: str) -> None:
        self._entry_id = controller.entry.entry_id
        self._device_name = controller.name
        self.entity_id = f"switch.{slug}_{SUFFIX_VIRTUAL}"
        self._attr_unique_id = f"{controller.entry.entry_id}_{SUFFIX_VIRTUAL}"
        self._attr_name = f"{controller.name} Virtual Device"
        self._attr_icon = "mdi:chip"

    @property
    def device_info(self) -> "DeviceInfo":
        return DeviceInfo(identifiers={(DOMAIN, self._entry_id)}, name=self._device_name)

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self.async_write_ha_state()
# --------------------------------------------------------------------------------------------------
# EOF
# --------------------------------------------------------------------------------------------------
