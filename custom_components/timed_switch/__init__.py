# --------------------------------------------------------------------------------------------------
# File          : custom_components/timed_switch/__init__.py
#
# Entry point: Controller létrehozása, platformok előreküldése, majd a Controller
# indítása (ebben a sorrendben, hogy a target_entity_id — akár a saját switch.<slug>_virtual
# is — már létező entitás legyen, mire a Controller az induló szinkront elvégzi).
#
# SPEC.md B2.4: on_crons/off_crons/manual_timeout/sync_interval élőben szerkeszthető —
# ezért az options-update listener NEM reload-ol, hanem közvetlenül frissíti a Controllert.
# --------------------------------------------------------------------------------------------------
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.loader import async_get_integration
from homeassistant.util import slugify

from homeassistant.helpers import storage

from .const import (
    CONF_SYNC_INTERVAL,
    CONF_MANUAL_TIMEOUT,
    CONF_OFF_CRONS,
    CONF_ON_CRONS,
    CARD_FILENAME,
    CARD_URL,
    DOMAIN,
    LEGACY_CONF_CHECK_INTERVAL,
    PLATFORMS,
    SUFFIX_SYNC_INTERVAL,
    SUFFIX_DEVICE,
    SUFFIX_DEVICE_LAST_CHANGED,
    SUFFIX_EXPECTED,
    SUFFIX_IS_MANUAL_MODE,
    SUFFIX_MANUAL_REMAINING,
    SUFFIX_SYNC_REMAINING,
    SUFFIX_MANUAL_TIMEOUT,
    SUFFIX_ON_CRONS,
    SUFFIX_OFF_CRONS,
    SUFFIX_PROBLEM,
    SUFFIX_SINCE_LAST_CHANGE,
    SUFFIX_TIMED_STATE,
    STORE_KEY,
    STORE_VERSION,
)
from .controller import Controller
from .helpers import parse_cron_list

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    card_path = Path(__file__).parent / "www" / CARD_FILENAME
    integration = await async_get_integration(hass, DOMAIN)
    card_version = integration.version
    card_resource_url = f"{CARD_URL}?v={card_version}"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card_path), False)]
    )
    resources = hass.data[LOVELACE_DATA].resources
    if isinstance(resources, ResourceStorageCollection):
        await resources.async_get_info()
        existing = next(
            (item for item in resources.async_items() if item.get("url", "").split("?", 1)[0] == CARD_URL),
            None,
        )
        if existing is None:
            await resources.async_create_item({"res_type": "module", "url": card_resource_url})
        elif existing.get("url") != card_resource_url:
            await resources.async_update_item(
                existing["id"], {"res_type": "module", "url": card_resource_url}
            )
    else:
        _LOGGER.warning(
            "Lovelace YAML resource mode is active; add %s as a module resource",
            CARD_URL,
        )
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    slug = slugify(entry.title)
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="Timed Switch",
        model="Scheduled entity controller",
    )
    if device.manufacturer != "Timed Switch" or device.model != "Scheduled entity controller":
        device_registry.async_update_device(
            device.id,
            manufacturer="Timed Switch",
            model="Scheduled entity controller",
        )
    controller = Controller(hass, entry, slug)
    hass.data[DOMAIN][entry.entry_id] = {"controller": controller, "slug": slug}

    _migrate_sync_interval_entity(hass, entry.entry_id, slug)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _migrate_entity_categories(hass, slug)

    # a target_entity_id (pl. a saját switch.<slug>_virtual) ekkorra már regisztrált entitás
    await controller.async_setup()

    async def _update_listener(hass: HomeAssistant, updated_entry: ConfigEntry) -> None:
        """SPEC.md B2.4: cron-listák/manual_timeout/sync_interval élőben, reload nélkül."""
        data = {**updated_entry.data, **(updated_entry.options or {})}
        controller.on_crons = parse_cron_list(data.get(CONF_ON_CRONS, ""))
        controller.off_crons = parse_cron_list(data.get(CONF_OFF_CRONS, ""))
        await controller.async_set_manual_timeout(int(data.get(CONF_MANUAL_TIMEOUT, controller.manual_timeout)))
        await controller.async_set_sync_interval(
            int(data.get(CONF_SYNC_INTERVAL, data.get(LEGACY_CONF_CHECK_INTERVAL, controller.sync_interval)))
        )
        _LOGGER.info("[%s] beállítások frissítve, élőben (reload nélkül)", controller.name)

    entry.async_on_unload(entry.add_update_listener(_update_listener))
    return True


def _migrate_entity_categories(hass: HomeAssistant, slug: str) -> None:
    """Keep existing registry entries aligned with SPEC.md B2.3.

    Home Assistant preserves a previously registered category when an integration later
    changes it. Explicit migration is therefore required for already installed entries.
    """
    registry = er.async_get(hass)
    categories = {
        f"switch.{slug}_{SUFFIX_EXPECTED}": None,
        f"switch.{slug}_{SUFFIX_TIMED_STATE}": None,
        f"switch.{slug}_{SUFFIX_DEVICE}": None,
        f"sensor.{slug}_{SUFFIX_MANUAL_REMAINING}": None,
        f"sensor.{slug}_{SUFFIX_SYNC_REMAINING}": None,
        f"switch.{slug}_{SUFFIX_IS_MANUAL_MODE}": EntityCategory.CONFIG,
        f"number.{slug}_{SUFFIX_MANUAL_TIMEOUT}": EntityCategory.CONFIG,
        f"number.{slug}_{SUFFIX_SYNC_INTERVAL}": EntityCategory.CONFIG,
        f"text.{slug}_{SUFFIX_ON_CRONS}": EntityCategory.CONFIG,
        f"text.{slug}_{SUFFIX_OFF_CRONS}": EntityCategory.CONFIG,
        f"binary_sensor.{slug}_{SUFFIX_PROBLEM}": EntityCategory.DIAGNOSTIC,
        f"sensor.{slug}_{SUFFIX_SINCE_LAST_CHANGE}": EntityCategory.DIAGNOSTIC,
        f"sensor.{slug}_{SUFFIX_DEVICE_LAST_CHANGED}": EntityCategory.DIAGNOSTIC,
    }
    for entity_id, category in categories.items():
        if (entry := registry.async_get(entity_id)) is not None and entry.entity_category != category:
            registry.async_update_entity(entity_id, entity_category=category)


def _migrate_sync_interval_entity(hass: HomeAssistant, entry_id: str, slug: str) -> None:
    """Rename the former Check Interval registry entry without creating a duplicate."""
    registry = er.async_get(hass)
    old_unique_id = f"{entry_id}_check_interval"
    old_entity_id = registry.async_get_entity_id("number", DOMAIN, old_unique_id)
    new_entity_id = f"number.{slug}_{SUFFIX_SYNC_INTERVAL}"
    if old_entity_id is not None and registry.async_get(new_entity_id) is None:
        registry.async_update_entity(
            old_entity_id,
            new_entity_id=new_entity_id,
            new_unique_id=f"{entry_id}_{SUFFIX_SYNC_INTERVAL}",
        )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if data:
        await data["controller"].async_unload()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """HA az entitás-/device-registry bejegyzéseket automatikusan törli a config entry
    törlésekor — de a saját Store JSON fájlunkat (.storage/timed_switch/<entry_id>/state.json)
    NEM, ez a mi felelősségünk, különben árván marad a lemezen."""
    store = storage.Store(hass, STORE_VERSION, f"{DOMAIN}/{entry.entry_id}/{STORE_KEY}.json")
    await store.async_remove()
# --------------------------------------------------------------------------------------------------
# EOF
# --------------------------------------------------------------------------------------------------
