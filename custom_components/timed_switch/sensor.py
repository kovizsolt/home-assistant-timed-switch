# --------------------------------------------------------------------------------------------------
# File          : custom_components/timed_switch/sensor.py
#
# SPEC.md B2.3 sensor entitások: a visszaszámlálások stabil céldátumai, valamint az
# _since_last_change és _device_last_changed abszolút időpontok.
# --------------------------------------------------------------------------------------------------
from __future__ import annotations

from datetime import datetime
from typing import Optional

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory

from .const import (
    DOMAIN,
    SUFFIX_DEVICE_LAST_CHANGED,
    SUFFIX_MANUAL_REMAINING,
    SUFFIX_SYNC_REMAINING,
    SUFFIX_SINCE_LAST_CHANGE,
)
from .controller import Controller


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    bucket = hass.data[DOMAIN][entry.entry_id]
    controller: Controller = bucket["controller"]
    slug: str = bucket["slug"]

    async_add_entities(
        [
            ManualRemainingSensor(controller, slug),
            SyncRemainingSensor(controller, slug),
            SinceLastChangeSensor(controller, slug),
            DeviceLastChangedSensor(controller, slug),
        ]
    )


class _BaseSensor(SensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = False

    def __init__(self, controller: Controller, slug: str, suffix: str, name_suffix: str) -> None:
        self._controller = controller
        self.entity_id = f"sensor.{slug}_{suffix}"
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


class ManualRemainingSensor(_BaseSensor):
    """Expose the manual deadline; the dashboard renders the live countdown."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:timer-sand"

    def __init__(self, controller: Controller, slug: str) -> None:
        super().__init__(controller, slug, SUFFIX_MANUAL_REMAINING, "Manual Remaining")

    @property
    def native_value(self) -> Optional[datetime]:
        if not self._controller.is_manual:
            return None
        return self._controller.manual_until


class SyncRemainingSensor(_BaseSensor):
    """Expose the sync deadline; the dashboard renders the live countdown."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:timer-sync"

    def __init__(self, controller: Controller, slug: str) -> None:
        super().__init__(controller, slug, SUFFIX_SYNC_REMAINING, "Sync Remaining")

    @property
    def native_value(self) -> Optional[datetime]:
        if self._controller.sync_interval <= 0:
            return None
        return self._controller.sync_until


class SinceLastChangeSensor(_BaseSensor):
    """sensor.<slug>_since_last_change — az expected_state utolsó váltásának abszolút
    időpontja (SPEC.md B2.3, device_class: timestamp)."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:history"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, controller: Controller, slug: str) -> None:
        super().__init__(controller, slug, SUFFIX_SINCE_LAST_CHANGE, "Since Last Change")

    @property
    def native_value(self) -> Optional[datetime]:
        return self._controller.since_last_change


class DeviceLastChangedSensor(_BaseSensor):
    """sensor.<slug>_device_last_changed — a target_entity_id utolsó ténylegesen észlelt
    állapotváltásának abszolút időpontja (SPEC.md B2.3, device_class: timestamp)."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:history"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, controller: Controller, slug: str) -> None:
        super().__init__(controller, slug, SUFFIX_DEVICE_LAST_CHANGED, "Device Last Changed")

    @property
    def native_value(self) -> Optional[datetime]:
        return self._controller.device_last_changed
# --------------------------------------------------------------------------------------------------
# EOF
# --------------------------------------------------------------------------------------------------
