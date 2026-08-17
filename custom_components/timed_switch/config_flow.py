# --------------------------------------------------------------------------------------------------
# File          : custom_components/timed_switch/config_flow.py
#
# Beállítás + Opciók flow. SPEC.md B2.4: on_crons/off_crons/manual_timeout/check_interval
# élőben (reload nélkül) érvényesül — ezt az __init__.py update_listenere végzi a Controlleren.
# --------------------------------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import Any, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant import data_entry_flow
from homeassistant.core import callback
from homeassistant.helpers.selector import selector
from homeassistant.loader import IntegrationNotFound, async_get_integration
from homeassistant.util import slugify

from .const import (
    CONF_CHECK_INTERVAL,
    CONF_DEFAULT_STATE,
    CONF_MANUAL_TIMEOUT,
    CONF_NAME,
    CONF_NOTIFY_EVENTS,
    CONF_OFF_CRONS,
    CONF_ON_CRONS,
    CONF_TARGET_ENTITY_ID,
    DEFAULT_CHECK_INTERVAL,
    DEFAULT_DEFAULT_STATE,
    DEFAULT_MANUAL_TIMEOUT,
    DEFAULT_NOTIFY_EVENTS,
    DOMAIN,
    SUPPORTED_TARGET_DOMAINS,
)

_LOGGER = logging.getLogger(__name__)


def _schema(defaults: dict[str, Any], include_name: bool, include_target: bool = True) -> vol.Schema:
    base: dict[Any, Any] = {}
    if include_name:
        base[vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, ""))] = str
    if include_target:
        base[vol.Optional(CONF_TARGET_ENTITY_ID, default=defaults.get(CONF_TARGET_ENTITY_ID, ""))] = selector(
            {"entity": {"domain": SUPPORTED_TARGET_DOMAINS, "multiple": False}}
        )
    base[vol.Optional(CONF_ON_CRONS, default=defaults.get(CONF_ON_CRONS, ""))] = str
    base[vol.Optional(CONF_OFF_CRONS, default=defaults.get(CONF_OFF_CRONS, ""))] = str
    base[vol.Optional(CONF_MANUAL_TIMEOUT, default=defaults.get(CONF_MANUAL_TIMEOUT, DEFAULT_MANUAL_TIMEOUT))] = int
    base[vol.Optional(CONF_CHECK_INTERVAL, default=defaults.get(CONF_CHECK_INTERVAL, DEFAULT_CHECK_INTERVAL))] = int
    base[vol.Optional(CONF_DEFAULT_STATE, default=defaults.get(CONF_DEFAULT_STATE, DEFAULT_DEFAULT_STATE))] = bool
    base[vol.Optional(CONF_NOTIFY_EVENTS, default=defaults.get(CONF_NOTIFY_EVENTS, DEFAULT_NOTIFY_EVENTS))] = bool
    return vol.Schema(base)


class TimedSwitchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._entry_data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return TimedSwitchOptionsFlow(config_entry)

    async def async_step_user(self, user_input: Optional[dict[str, Any]] = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if not name:
                errors["base"] = "name_required"
            else:
                self._entry_data = dict(user_input)
                return await self.async_step_target()
        return self.async_show_form(
            step_id="user",
            data_schema=_schema({}, include_name=True, include_target=False),
            errors=errors,
        )

    async def async_step_target(self, user_input: Optional[dict[str, Any]] = None):
        menu_options = ["built_in_virtual", "existing_entity"]
        try:
            await async_get_integration(self.hass, "virtual_switch")
        except IntegrationNotFound:
            pass
        else:
            menu_options.append("new_virtual_switch")
        return self.async_show_menu(step_id="target", menu_options=menu_options)

    async def async_step_built_in_virtual(self, user_input: Optional[dict[str, Any]] = None):
        self._entry_data[CONF_TARGET_ENTITY_ID] = ""
        return self.async_create_entry(title=self._entry_data[CONF_NAME], data=self._entry_data)

    async def async_step_existing_entity(self, user_input: Optional[dict[str, Any]] = None):
        if user_input is not None:
            self._entry_data[CONF_TARGET_ENTITY_ID] = user_input[CONF_TARGET_ENTITY_ID]
            return self.async_create_entry(title=self._entry_data[CONF_NAME], data=self._entry_data)
        return self.async_show_form(
            step_id="existing_entity",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TARGET_ENTITY_ID): selector(
                        {"entity": {"domain": SUPPORTED_TARGET_DOMAINS, "multiple": False}}
                    )
                }
            ),
        )

    async def async_step_new_virtual_switch(self, user_input: Optional[dict[str, Any]] = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            virtual_name = str(user_input.get(CONF_NAME, "")).strip()
            if not virtual_name:
                errors["base"] = "name_required"
            else:
                result = await self.hass.config_entries.flow.async_init(
                    "virtual_switch",
                    context={"source": config_entries.SOURCE_IMPORT},
                    data={CONF_NAME: virtual_name},
                )
                if result["type"] == data_entry_flow.FlowResultType.ABORT:
                    errors["base"] = (
                        "virtual_switch_already_exists"
                        if result.get("reason") == "already_configured"
                        else "virtual_switch_create_failed"
                    )
                else:
                    self._entry_data[CONF_TARGET_ENTITY_ID] = f"switch.{slugify(virtual_name)}_main"
                    return self.async_create_entry(title=self._entry_data[CONF_NAME], data=self._entry_data)
        return self.async_show_form(
            step_id="new_virtual_switch",
            data_schema=vol.Schema(
                {vol.Required(CONF_NAME, default=f"{self._entry_data.get(CONF_NAME, '')} Virtual"): str}
            ),
            errors=errors,
        )


class TimedSwitchOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: Optional[dict[str, Any]] = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {**self.entry.data, **(self.entry.options or {})}
        return self.async_show_form(step_id="init", data_schema=_schema(defaults, include_name=False))
# --------------------------------------------------------------------------------------------------
# EOF
# --------------------------------------------------------------------------------------------------
