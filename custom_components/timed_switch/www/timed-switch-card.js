const EXPECTED_SUFFIX = "_expected";

class TimedSwitchRemainingRow extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._row = document.createElement("hui-sensor-entity-row");
    this._row.setConfig({ entity: config.entity, name: config.name });
    this.replaceChildren(this._row);
    this._startTimer();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._row || !this._config) return;
    const duration = Number(hass.states[this._config.duration_entity]?.state);
    const disabled = duration === 0;
    this.toggleAttribute("disabled", disabled);
    this.setAttribute("aria-disabled", String(disabled));
    this.style.opacity = disabled ? "0.38" : "";
    this.style.filter = disabled ? "grayscale(1)" : "";
    this.style.pointerEvents = disabled ? "none" : "";
    this.style.setProperty("--state-icon-color", disabled ? "var(--disabled-text-color)" : "");
    this.style.setProperty("--primary-text-color", disabled ? "var(--disabled-text-color)" : "");
    this._render();
  }

  connectedCallback() {
    this._startTimer();
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    this._timer = undefined;
  }

  _startTimer() {
    if (!this.isConnected || this._timer) return;
    this._timer = setInterval(() => this._render(), 1000);
  }

  _countdown(state) {
    if (!state || state.state === "unknown" || state.state === "unavailable") return "--:--";
    const deadline = Date.parse(state.state);
    if (!Number.isFinite(deadline)) return "--:--";
    const remaining = Math.max(0, Math.floor((deadline - Date.now()) / 1000));
    const hours = Math.floor(remaining / 3600);
    const minutes = Math.floor((remaining % 3600) / 60);
    const seconds = remaining % 60;
    return [hours, minutes, seconds].map((value) => String(value).padStart(2, "0")).join(":");
  }

  _render() {
    if (!this._row || !this._config || !this._hass) return;
    const state = this._hass.states[this._config.entity];
    if (!state) {
      this._row.hass = this._hass;
      return;
    }
    const displayAttributes = { ...state.attributes };
    delete displayAttributes.device_class;
    const displayState = {
      ...state,
      state: this._countdown(state),
      attributes: displayAttributes,
    };
    const displayStates = Object.create(this._hass.states);
    Object.defineProperty(displayStates, this._config.entity, { value: displayState });
    const displayHass = Object.create(this._hass);
    Object.defineProperty(displayHass, "states", { value: displayStates });
    this._row.hass = displayHass;
  }
}

if (!customElements.get("timed-switch-remaining-row")) {
  customElements.define("timed-switch-remaining-row", TimedSwitchRemainingRow);
}

class TimedSwitchScheduleRow extends HTMLElement {
  setConfig(config) {
    if (!config.entity) throw new Error("Schedule row requires an entity");
    this._config = config;
    const root = this.shadowRoot || this.attachShadow({ mode: "open" });
    root.innerHTML = `
      <style>
        :host { display: block; padding: 8px 16px; }
        .label { color: var(--primary-text-color); font-size: 14px; margin-bottom: 6px; }
        .label.saving { color: var(--warning-color, #ff9800); }
        .label.saved { color: var(--success-color, #4caf50); }
        .label.error { color: var(--error-color, #db4437); }
        textarea {
          box-sizing: border-box;
          display: block;
          width: 100%;
          min-height: 76px;
          resize: vertical;
          padding: 10px 12px;
          border: 1px solid var(--outline-color, var(--divider-color));
          border-radius: var(--ha-card-border-radius, 12px);
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font: inherit;
          line-height: 1.4;
        }
        textarea:focus {
          border-color: var(--primary-color);
          outline: 1px solid var(--primary-color);
        }
        textarea:disabled { color: var(--disabled-text-color); }
      </style>
      <div class="label"></div>
    `;
    this._label = root.querySelector(".label");
    this._label.textContent = config.name;
    this._input = document.createElement("textarea");
    this._input.setAttribute("rows", "3");
    this._input.setAttribute("aria-label", config.name);
    this._input.placeholder = "One cron expression per line";
    this._input.addEventListener("change", () => this._save());
    root.appendChild(this._input);
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._input || this.shadowRoot?.activeElement === this._input) return;
    const state = hass.states[this._config.entity];
    this._input.value = state?.state === "unknown" || state?.state === "unavailable"
      ? ""
      : state?.state || "";
    this._input.disabled = !state;
  }

  async _save() {
    if (!this._hass || !this._input) return;
    clearTimeout(this._statusTimer);
    this._setStatus("saving");
    this._input.disabled = true;
    try {
      await this._hass.callService("text", "set_value", {
        entity_id: this._config.entity,
        value: this._input.value,
      }, undefined, false);
      this._setStatus("saved");
      this._statusTimer = setTimeout(() => this._setStatus(), 3000);
    } catch (error) {
      this._setStatus("error");
      this._statusTimer = setTimeout(() => this._setStatus(), 3000);
      this._showErrorDialog(this._errorMessage(error));
    } finally {
      this._input.disabled = false;
    }
  }

  _setStatus(status = "") {
    if (!this._label) return;
    this._label.classList.remove("saving", "saved", "error");
    if (status) this._label.classList.add(status);
  }

  _errorMessage(error) {
    return error?.body?.message || error?.message || "Az időzítés mentése nem sikerült.";
  }

  _showErrorDialog(message) {
    const dialog = document.createElement("ha-dialog");
    dialog.setAttribute("open", "");
    dialog.heading = "Az időzítés nem menthető";

    const content = document.createElement("div");
    content.style.whiteSpace = "pre-wrap";
    content.textContent = message;
    dialog.appendChild(content);

    const close = document.createElement("ha-button");
    close.setAttribute("slot", "primaryAction");
    close.textContent = "Bezárás";
    close.addEventListener("click", () => dialog.close());
    dialog.addEventListener("closed", () => dialog.remove());
    dialog.appendChild(close);
    document.body.appendChild(dialog);
  }
}

if (!customElements.get("timed-switch-schedule-row")) {
  customElements.define("timed-switch-schedule-row", TimedSwitchScheduleRow);
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
      onCrons: `text.${objectId}_on_crons`,
      offCrons: `text.${objectId}_off_crons`,
      status: `binary_sensor.${objectId}_status`,
      since: `sensor.${objectId}_since_last_change`,
      deviceChanged: `sensor.${objectId}_device_last_changed`,
      timedChanged: `sensor.${objectId}_timed_state_last_changed`,
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
      this._entityRow(ids.expected, "Expected state:"),
      this._entityRow(ids.device, "Device state:"),
      this._entityRow(ids.manual, "Manual Override:"),
      this._entityRow(ids.timed, "Scheduled state:"),
      { type: "section", label: "Schedule" },
      this._hass.states[ids.onCrons] ? {
        type: "custom:timed-switch-schedule-row", entity: ids.onCrons, name: "ON time(s):",
      } : undefined,
      this._hass.states[ids.offCrons] ? {
        type: "custom:timed-switch-schedule-row", entity: ids.offCrons, name: "OFF time(s):",
      } : undefined,
      { type: "section", label: "Timing" },
      this._entityRow(ids.timeout, "Manual timeout:"),
      this._entityRow(ids.interval, "Sync interval:"),
      this._remainingRow(ids.remaining, ids.timeout, "Time Until Override:"),
      this._remainingRow(ids.syncRemaining, ids.interval, "Time Until Sync:"),
      { type: "section", label: "Status" },
      this._hass.states[ids.timed] ? {
        type: "attribute", entity: ids.timed, attribute: "next_schedule",
        name: "Next schedule:", icon: "mdi:calendar-clock",
        time_format: { type: "datetime", style: "short" },
      } : undefined,
      this._entityRow(ids.deviceChanged, "Device changed:", {
        time_format: { type: "datetime", style: "short" },
      }),
      this._entityRow(ids.since, "Expected changed:", {
        time_format: { type: "datetime", style: "short" },
      }),
      this._entityRow(ids.timedChanged, "Scheduled state changed:", {
        time_format: { type: "datetime", style: "short" },
      }),
      this._entityRow(ids.status, "Status:"),
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
