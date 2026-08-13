# --------------------------------------------------------------------------------------------------
# File          : custom_components/timed_switch/__init__.py
#
# Entry point: Controller létrehozása, platformok előreküldése, majd a Controller
# indítása (ebben a sorrendben, hogy a target_entity_id — akár a saját switch.<slug>_virtual
# is — már létező entitás legyen, mire a Controller az induló szinkront elvégzi).
#
# SPEC.md B2.4: on_crons/off_crons/manual_timeout/check_interval élőben szerkeszthető —
# ezért az options-update listener NEM reload-ol, hanem közvetlenül frissíti a Controllert.
# --------------------------------------------------------------------------------------------------
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from .const import (
    CONF_CHECK_INTERVAL,
    CONF_MANUAL_TIMEOUT,
    CONF_OFF_CRONS,
    CONF_ON_CRONS,
    DOMAIN,
    PLATFORMS,
)
from .controller import Controller
from .helpers import parse_cron_list

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    slug = slugify(entry.title)
    controller = Controller(hass, entry, slug)
    hass.data[DOMAIN][entry.entry_id] = {"controller": controller, "slug": slug}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # a target_entity_id (pl. a saját switch.<slug>_virtual) ekkorra már regisztrált entitás
    await controller.async_setup()

    async def _update_listener(hass: HomeAssistant, updated_entry: ConfigEntry) -> None:
        """SPEC.md B2.4: cron-listák/manual_timeout/check_interval élőben, reload nélkül."""
        data = {**updated_entry.data, **(updated_entry.options or {})}
        controller.on_crons = parse_cron_list(data.get(CONF_ON_CRONS, ""))
        controller.off_crons = parse_cron_list(data.get(CONF_OFF_CRONS, ""))
        await controller.async_set_manual_timeout(int(data.get(CONF_MANUAL_TIMEOUT, controller.manual_timeout)))
        await controller.async_set_check_interval(int(data.get(CONF_CHECK_INTERVAL, controller.check_interval)))
        _LOGGER.info("[%s] beállítások frissítve, élőben (reload nélkül)", controller.name)

    entry.async_on_unload(entry.add_update_listener(_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if data:
        await data["controller"].async_unload()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
# --------------------------------------------------------------------------------------------------
# EOF
# --------------------------------------------------------------------------------------------------
