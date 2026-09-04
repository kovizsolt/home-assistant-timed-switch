# --------------------------------------------------------------------------------------------------
# File          : custom_components/timed_switch/binary_sensor.py
#
# SPEC.md B2.3: binary_sensor.<slug>_status — device_class: problem, ON ha az ELERHETOSEGI
# gép UNAVAILABLE.
# --------------------------------------------------------------------------------------------------
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory

from .const import AVAIL_UNAVAILABLE, DOMAIN, SUFFIX_STATUS
from .controller import Controller


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    bucket = hass.data[DOMAIN][entry.entry_id]
    controller: Controller = bucket["controller"]
    slug: str = bucket["slug"]

    async_add_entities([StatusBinarySensor(controller, slug)])


class StatusBinarySensor(BinarySensorEntity):
    """binary_sensor.<slug>_status — SPEC.md B2.3."""

    _attr_should_poll = False
    _attr_has_entity_name = False
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, controller: Controller, slug: str) -> None:
        self._controller = controller
        self.entity_id = f"binary_sensor.{slug}_{SUFFIX_STATUS}"
        self._attr_unique_id = f"{controller.entry.entry_id}_{SUFFIX_STATUS}"
        self._attr_name = f"{controller.name} Status"

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

    @property
    def is_on(self) -> bool:
        return self._controller.avail_state == AVAIL_UNAVAILABLE
# --------------------------------------------------------------------------------------------------
# EOF
# --------------------------------------------------------------------------------------------------
