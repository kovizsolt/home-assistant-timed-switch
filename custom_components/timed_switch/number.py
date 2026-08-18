# --------------------------------------------------------------------------------------------------
# File          : custom_components/timed_switch/number.py
#
# SPEC.md B2.3 number entitások: _manual_timeout, _sync_interval (mindkettő mp, futásidőben
# felülbírálja a config alapértéket).
# --------------------------------------------------------------------------------------------------
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory

from .const import DOMAIN, SUFFIX_SYNC_INTERVAL, SUFFIX_MANUAL_TIMEOUT
from .controller import Controller


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    bucket = hass.data[DOMAIN][entry.entry_id]
    controller: Controller = bucket["controller"]
    slug: str = bucket["slug"]

    async_add_entities(
        [
            ManualTimeoutNumber(controller, slug),
            SyncIntervalNumber(controller, slug),
        ]
    )


class _BaseNumber(NumberEntity):
    _attr_should_poll = False
    _attr_has_entity_name = False
    _attr_native_min_value = 0
    _attr_native_max_value = 86400
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = "s"

    def __init__(self, controller: Controller, slug: str, suffix: str, name_suffix: str) -> None:
        self._controller = controller
        self.entity_id = f"number.{slug}_{suffix}"
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


class ManualTimeoutNumber(_BaseNumber):
    """number.<slug>_manual_timeout — SPEC.md B2.3/B2.4."""

    _attr_icon = "mdi:timer-cog"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, controller: Controller, slug: str) -> None:
        super().__init__(controller, slug, SUFFIX_MANUAL_TIMEOUT, "Manual Timeout")

    @property
    def native_value(self) -> float:
        return float(self._controller.manual_timeout)

    async def async_set_native_value(self, value: float) -> None:
        await self._controller.async_set_manual_timeout(int(value))


class SyncIntervalNumber(_BaseNumber):
    """number.<slug>_sync_interval — SPEC.md B2.3/B2.4 (0 = poller kikapcsolva)."""

    _attr_icon = "mdi:timer-refresh"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, controller: Controller, slug: str) -> None:
        super().__init__(controller, slug, SUFFIX_SYNC_INTERVAL, "Sync Interval")

    @property
    def native_value(self) -> float:
        return float(self._controller.sync_interval)

    async def async_set_native_value(self, value: float) -> None:
        await self._controller.async_set_sync_interval(int(value))
# --------------------------------------------------------------------------------------------------
# EOF
# --------------------------------------------------------------------------------------------------
