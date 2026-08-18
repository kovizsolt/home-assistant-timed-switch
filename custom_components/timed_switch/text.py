"""Editable ON/OFF cron-list entities for the Timed Switch dashboard card."""
from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory

from .const import (
    CONF_OFF_CRONS,
    CONF_ON_CRONS,
    DOMAIN,
    SUFFIX_OFF_CRONS,
    SUFFIX_ON_CRONS,
)
from .controller import Controller


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    bucket = hass.data[DOMAIN][entry.entry_id]
    controller: Controller = bucket["controller"]
    slug: str = bucket["slug"]
    async_add_entities(
        [
            CronListText(controller, slug, CONF_ON_CRONS, SUFFIX_ON_CRONS, "ON Schedule"),
            CronListText(controller, slug, CONF_OFF_CRONS, SUFFIX_OFF_CRONS, "OFF Schedule"),
        ]
    )


class CronListText(TextEntity):
    """A persisted, live-editable multi-expression cron list."""

    _attr_should_poll = False
    _attr_has_entity_name = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = 255
    _attr_icon = "mdi:calendar-edit"

    def __init__(
        self, controller: Controller, slug: str, key: str, suffix: str, name_suffix: str
    ) -> None:
        self._controller = controller
        self._key = key
        self.entity_id = f"text.{slug}_{suffix}"
        self._attr_unique_id = f"{controller.entry.entry_id}_{suffix}"
        self._attr_name = f"{controller.name} {name_suffix}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._controller.entry.entry_id)},
            name=self._controller.name,
        )

    @property
    def native_value(self) -> str:
        data = {**self._controller.entry.data, **(self._controller.entry.options or {})}
        return str(data.get(self._key, ""))

    async def async_set_value(self, value: str) -> None:
        await self._controller.async_set_cron_list(self._key, value)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._controller._signal, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
