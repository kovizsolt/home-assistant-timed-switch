const EXPECTED_SUFFIX = "_expected";

class TimedSwitchRemainingRow extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._row = document.createElement("hui-sensor-entity-row");
    this._row.setConfig({ entity: config.entity, name: config.name });
    this.replaceChildren(this._row);
  }

  set hass(hass) {
    if (!this._row || !this._config) return;
    this._row.hass = hass;
    const duration = Number(hass.states[this._config.duration_entity]?.state);
    const disabled = duration === 0;
    this.toggleAttribute("disabled", disabled);
    this.setAttribute("aria-disabled", String(disabled));
    this.style.opacity = disabled ? "0.38" : "";
    this.style.filter = disabled ? "grayscale(1)" : "";
    this.style.pointerEvents = disabled ? "none" : "";
    this.style.setProperty("--state-icon-color", disabled ? "var(--disabled-text-color)" : "");
    this.style.setProperty("--primary-text-color", disabled ? "var(--disabled-text-color)" : "");
  }
}

if (!customElements.get("timed-switch-remaining-row")) {
  customElements.define("timed-switch-remaining-row", TimedSwitchRemainingRow);
}

class TimedSwitchCard extends HTMLElement {
  static getStubConfig(hass, entities = [], entitiesFill = []) {
    const suggested = [...entities, ...entitiesFill]
      .find((entityId) => TimedSwitchCard._isExpectedEntity(hass, entityId));
    const firstAvailable = Object.keys(hass?.states || {})
      .find((entityId) => TimedSwitchCard._isExpectedEntity(hass, entityId));
    return { entity: suggested || firstAvailable || "" };
  }

  static getConfigForm() {
    return {
      schema: [{
        name: "entity",
        required: true,
        selector: {
          entity: {
            filter: { domain: "switch", integration: "timed_switch" },
          },
        },
      }],
      computeLabel: (schema) => schema.name === "entity" ? "Timed Switch instance (Expected)" : undefined,
      computeHelper: (schema) => schema.name === "entity"
        ? "Select the Expected switch of the Timed Switch device."
        : undefined,
      assertConfig: (config) => {
        if (!config.entity?.startsWith("switch.") || !config.entity.endsWith(EXPECTED_SUFFIX)) {
          throw new Error("Select the Expected switch of a Timed Switch device");
        }
      },
    };
  }

  static _isExpectedEntity(hass, entityId) {
    const state = hass?.states?.[entityId];
    return entityId?.startsWith("switch.")
      && entityId.endsWith(EXPECTED_SUFFIX)
      && state?.attributes?.device_available !== undefined;
  }

  setConfig(config) {
    if (!config.entity || !config.entity.startsWith("switch.") || !config.entity.endsWith(EXPECTED_SUFFIX)) {
      throw new Error("Select the Expected switch of a Timed Switch device");
    }
    this._config = { ...config };
    this._nativeCard = undefined;
    this._buildPromise = undefined;
    this.replaceChildren();
    this._ensureNativeCard();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._nativeCard) this._nativeCard.hass = hass;
    else this._ensureNativeCard();
  }

  getCardSize() { return 10; }

  getGridOptions() {
    return { columns: 12, min_columns: 8 };
  }

  _ids() {
    const expected = this._config.entity;
    const objectId = expected.slice("switch.".length, -EXPECTED_SUFFIX.length);
    return {
      expected,
      timed: `switch.${objectId}_timed_state`,
      manual: `switch.${objectId}_is_manual_mode`,
      device: `switch.${objectId}_device`,
      remaining: `sensor.${objectId}_manual_remaining`,
      syncRemaining: `sensor.${objectId}_sync_remaining`,
      timeout: `number.${objectId}_manual_timeout`,
      interval: `number.${objectId}_sync_interval`,
      problem: `binary_sensor.${objectId}_problem`,
      since: `sensor.${objectId}_since_last_change`,
      deviceChanged: `sensor.${objectId}_device_last_changed`,
    };
  }

  _entityRow(entity, name, extra = {}) {
    return this._hass?.states?.[entity] ? { entity, name, ...extra } : undefined;
  }

  _remainingRow(entity, durationEntity, name) {
    return this._hass?.states?.[entity] ? {
      type: "custom:timed-switch-remaining-row",
      entity,
      duration_entity: durationEntity,
      name,
    } : undefined;
  }

  _nativeConfig() {
    const ids = this._ids();
    const expected = this._hass.states[ids.expected];
    const title = this._config.name
      || expected?.attributes?.friendly_name?.replace(/ Expected$/, "")
      || "Timed Switch";
    const rows = [
      this._entityRow(ids.expected, "Target state"),
      this._entityRow(ids.device, "Device state"),
      this._entityRow(ids.manual, "Manual override"),
      this._entityRow(ids.timed, "Scheduled state"),
      { type: "section", label: "Timing" },
      this._entityRow(ids.timeout, "Manual timeout"),
      this._entityRow(ids.interval, "Sync interval"),
      this._remainingRow(ids.remaining, ids.timeout, "Manual remaining"),
      this._remainingRow(ids.syncRemaining, ids.interval, "Sync remaining"),
      { type: "section", label: "Status" },
      this._hass.states[ids.timed] ? {
        type: "attribute", entity: ids.timed, attribute: "next_schedule",
        name: "Next schedule", icon: "mdi:calendar-clock",
        time_format: { type: "datetime", style: "short" },
      } : undefined,
      this._entityRow(ids.since, "Target changed", {
        time_format: { type: "datetime", style: "short" },
      }),
      this._entityRow(ids.deviceChanged, "Device changed", {
        time_format: { type: "datetime", style: "short" },
      }),
      this._entityRow(ids.problem, "Status"),
    ].filter(Boolean);
    return {
      type: "entities", title, icon: "mdi:calendar-clock",
      show_header_toggle: false, state_color: true, entities: rows,
    };
  }

  _ensureNativeCard() {
    if (!this._config || !this._hass || this._nativeCard || this._buildPromise) return;
    this._buildPromise = window.loadCardHelpers()
      .then((helpers) => {
        const card = helpers.createCardElement(this._nativeConfig());
        card.hass = this._hass;
        this._nativeCard = card;
        this.replaceChildren(card);
      })
      .catch((error) => {
        const message = document.createElement("ha-alert");
        message.setAttribute("alert-type", "error");
        message.textContent = `Timed Switch card: ${error.message}`;
        this.replaceChildren(message);
      })
      .finally(() => { this._buildPromise = undefined; });
  }
}

if (!customElements.get("timed-switch-card")) customElements.define("timed-switch-card", TimedSwitchCard);

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "timed-switch-card")) {
  window.customCards.push({
    type: "timed-switch-card",
    name: "Timed Switch Card",
    description: "Native Home Assistant controls for one Timed Switch device",
    preview: true,
    getEntitySuggestion: (hass, entityId) => {
      if (!TimedSwitchCard._isExpectedEntity(hass, entityId)) return null;
      return { config: { type: "custom:timed-switch-card", entity: entityId } };
    },
  });
}
