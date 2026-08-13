# --------------------------------------------------------------------------------------------------
# File          : custom_components/timed_switch/const.py
#
# Állandók: domain, config kulcsok, állapot-/esemény-nevek a SPEC.md B2 szótára szerint,
# szó szerint (SPEC.md B2 / CLAUDE.md 4. pont).
# --------------------------------------------------------------------------------------------------
from __future__ import annotations

DOMAIN = "timed_switch"

PLATFORMS = ["switch", "sensor", "number", "binary_sensor"]

SUPPORTED_TARGET_DOMAINS = ["switch", "input_boolean", "light", "script", "button"]

# --- Config / options kulcsok (SPEC.md B2.4) ---------------------------------------------------
CONF_NAME = "name"
CONF_TARGET_ENTITY_ID = "target_entity_id"
CONF_ON_CRONS = "on_crons"
CONF_OFF_CRONS = "off_crons"
CONF_MANUAL_TIMEOUT = "manual_timeout"
CONF_CHECK_INTERVAL = "check_interval"
CONF_DEFAULT_STATE = "default_state"
CONF_NOTIFY_EVENTS = "notify_events"

DEFAULT_MANUAL_TIMEOUT = 600
DEFAULT_CHECK_INTERVAL = 60
DEFAULT_DEFAULT_STATE = False  # KI
DEFAULT_NOTIFY_EVENTS = False

STORE_VERSION = 1
STORE_KEY = "state"

# --- FŐ gép állapotok (SPEC.md B2.1) -----------------------------------------------------------
STATE_AUTO = "AUTO"
STATE_MANUAL = "MANUAL"

# --- ELERHETOSEGI gép állapotok (SPEC.md B2.1b) -------------------------------------------------
AVAIL_AVAILABLE = "AVAILABLE"
AVAIL_UNAVAILABLE = "UNAVAILABLE"

# --- FŐ gép események (SPEC.md B2.2) -----------------------------------------------------------
EVT_SCHEDULE_ON = "schedule_on"
EVT_SCHEDULE_OFF = "schedule_off"
EVT_MANUAL_CHANGE_ON = "manual_change_on"
EVT_MANUAL_CHANGE_OFF = "manual_change_off"
EVT_MANUAL_TIMEOUT_EXPIRED = "manual_timeout_expired"
EVT_OVERRIDE_CLEARED = "override_cleared"
EVT_OVERRIDE_SET = "override_set"
EVT_STATE_CHECK = "state_check"

# --- ELERHETOSEGI gép események (SPEC.md B2.2b) -------------------------------------------------
EVT_BECAME_UNAVAILABLE = "became_unavailable"
EVT_BECAME_AVAILABLE = "became_available"

# --- Entitás entity_id-szuffixumok (SPEC.md B2.3) -----------------------------------------------
SUFFIX_VIRTUAL = "virtual"
SUFFIX_EXPECTED = "expected"
SUFFIX_TIMED_STATE = "timed_state"
SUFFIX_IS_MANUAL_MODE = "is_manual_mode"
SUFFIX_DEVICE = "device"
SUFFIX_PROBLEM = "problem"
SUFFIX_MANUAL_REMAINING = "manual_remaining"
SUFFIX_SINCE_LAST_CHANGE = "since_last_change"
SUFFIX_DEVICE_LAST_CHANGED = "device_last_changed"
SUFFIX_MANUAL_TIMEOUT = "manual_timeout"
SUFFIX_CHECK_INTERVAL = "check_interval"

ATTR_DEVICE_AVAILABLE = "device_available"
ATTR_NEXT_SCHEDULE = "next_schedule"

SIGNAL_UPDATE = f"{DOMAIN}_update"
# --------------------------------------------------------------------------------------------------
# EOF
# --------------------------------------------------------------------------------------------------
