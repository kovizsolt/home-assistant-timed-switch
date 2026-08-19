# Timed Switch

[Magyar dokumentáció](README.hu.md) · [Changelog](CHANGELOG.md)

Timed Switch is a Home Assistant custom integration for reliable, scheduled control
of switchable devices. It can turn a physical smart switch, relay, or light on and
off at predefined times. Each integration instance controls exactly one target entity.

Key features:

- flexible cron-based ON/OFF schedules;
- manual control with a timed override mode;
- configurable continuous verification of the physical switch state, with automatic
  correction when it differs from the expected state;
- persisted operating state for resilient recovery after Home Assistant restarts,
  outages, and temporary network failures;
- separate diagnostics for target availability.

Supported target domains: `switch`, `input_boolean`, `light`, `script`, and `button`.

## Requirements

- Home Assistant 2025.9.4 or newer;
- access to the Home Assistant `config` directory;
- permission to restart Home Assistant;
- the `frontend` and `lovelace` integrations for the custom dashboard card.

Home Assistant automatically installs the Python dependency (`croniter`) declared in
`manifest.json`.

## Installation

### HACS (recommended)

1. Open HACS and select **Custom repositories** from the top-right menu.
2. Add `https://github.com/kovizsolt/home-assistant-timed-switch` as an
   **Integration** repository.
3. Find **Timed Switch** in HACS and download it.
4. Restart Home Assistant.
5. Open **Settings → Devices & services → Add integration**.
6. Search for **Timed Switch** and add it.

### Manual installation

1. Copy `custom_components/timed_switch` into the Home Assistant configuration
   directory so that the resulting path is:

   ```text
   <config>/custom_components/timed_switch/
   ```

2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration**.
4. Search for **Timed Switch** and add it.

To update, replace the complete `timed_switch` directory and restart Home Assistant.
Configuration and runtime state are retained in Home Assistant storage.

### Local validation

Before publishing, run every local check from the repository root:

```bash
./scripts/validate.sh all
```

Individual modes are `static`, `tests`, and `hassfest`. Add `--no-pull` to the
Hassfest or `all` mode to use the locally cached Docker image.

## Configuration

The integration is configured entirely through the Home Assistant UI. No
`configuration.yaml` entry is required.

When creating an instance, configure:

- **Name:** base name for the device and its entities;
- **ON cron list:** scheduled activation times;
- **OFF cron list:** scheduled deactivation times;
- **Manual timeout:** duration of a manual override in seconds (default: 600); `0`
  keeps the override active until the next scheduled change;
- **Sync interval:** target-state verification period in seconds (default: 60); `0`
  disables verification;
- **Default state:** initial state when no saved or evaluable schedule exists;
- **Send notifications:** creates a persistent Home Assistant notification for
  scheduled target changes and corrective actions.

Then select the controlled device:

- **Built-in virtual switch:** creates the integration's own target switch;
- **Existing entity:** controls an existing entity in one of the supported domains;
- **New Virtual Switch:** creates and targets a new `virtual_switch` instance; this
  option is available only when the Virtual Switch integration is installed.

Settings can later be changed under **Settings → Devices & services → Timed Switch →
Configure**. Changing the target requires a full integration reload. Schedule and
timing changes are applied live.

### Cron format

The ON and OFF fields accept multiple five-field `croniter` expressions, separated
by commas or new lines. Text after `#` is treated as a comment. Expressions use the
local time zone configured in Home Assistant and have one-minute precision.
Short expressions are completed on the right with `*` fields. Fields after the fifth
are discarded only when they are all `*`; any other extra field is reported as an error.

```text
# At 07:30 every weekday
30 7 * * 1-5

# At 22:00 every day
0 22 * * *
```

For an alternating cycle of 10 minutes ON and 10 minutes OFF, use this **ON cron
list**:

```text
0,20,40 * * * *
```

And this **OFF cron list**:

```text
10,30,50 * * * *
```

This turns the device on at minute `00`, `20`, and `40`, and off at minute `10`,
`30`, and `50` of every hour. The cycle continues across hour boundaries.

The same schedule can be written in the shorter step syntax. The **ON cron list**:

```text
*/20 * * * *
```

The **OFF cron list**:

```text
10-59/20 * * * *
```

`*/20` means every twentieth minute starting at minute 0. `10-59/20` means every
twentieth minute starting at minute 10. Together they produce the 10-minute ON,
10-minute OFF cycle. The `*/10` and `5-59/10` pattern follows the same principle,
but changes state every five minutes.

When both lists are empty, no scheduled transition occurs and the scheduled state
remains at its default value.

For additional help creating and checking cron expressions, see
[crontab.guru](https://crontab.guru/).

## Dashboard display

The integration includes a custom **Timed Switch Card**. In Lovelace storage mode,
the JavaScript resource is registered automatically. While editing a dashboard,
select **Add card → Timed Switch Card**, then select the instance's
`switch.<name>_expected` entity.

In YAML dashboard or YAML resource mode, add the resource manually:

```yaml
lovelace:
  resources:
    - url: /timed_switch/timed-switch-card.js
      type: module
```

Card configuration in YAML:

```yaml
type: custom:timed-switch-card
entity: switch.garden_lights_expected
```

The card shows the expected, physical, and scheduled states, manual mode, ON/OFF
schedules, timing controls, next scheduled change, and diagnostics. If a secondary
entity is disabled, the remaining controls continue to work.

## Usage

In normal **AUTO** mode, the `Expected` switch follows the scheduled state and the
integration applies it to the target. Manually changing the target, `Expected`, or
`Device` switch enters **MANUAL** mode. When the timeout expires, the instance returns
to AUTO mode and applies the current scheduled state.

Main entities (`<name>` is the slug generated from the instance name):

| Entity | Purpose |
|---|---|
| `switch.<name>_expected` | Desired target state; can also be controlled manually |
| `switch.<name>_device` | Two-way mirror of the physical target entity |
| `switch.<name>_timed_state` | Raw schedule output; manual changes simulate schedule events |
| `switch.<name>_is_manual_mode` | Enables or clears manual override mode |
| `number.<name>_manual_timeout` | Timeout used for subsequent manual overrides |
| `number.<name>_sync_interval` | Physical-state verification interval |
| `text.<name>_on_crons`, `text.<name>_off_crons` | Live schedule editing |
| `binary_sensor.<name>_problem` | Target availability problem indicator |

Additional sensors show the manual and synchronization countdowns and the times of
the most recent target and physical-device state changes. Home Assistant may hide
some configuration and diagnostic entities from the normal device view by default;
they can be enabled from the device's entity list.

### Important behavior

- In MANUAL mode, the schedule continues to update in the background but does not
  overwrite the device until the timeout expires.
- With `manual_timeout: 0`, the next ON or OFF schedule event ends manual mode.
- In AUTO mode, state verification corrects mismatches between the desired and
  physical states. It does not intervene in MANUAL mode.
- When the target is `unknown` or `unavailable`, the control logic continues to run
  and the `Problem` binary sensor reports the fault.
- Runtime state is restored after a restart. A manual timeout that expired during
  downtime is taken into account during startup.

## Removal

Remove every instance under **Settings → Devices & services → Timed Switch**, restart
Home Assistant, and then remove `<config>/custom_components/timed_switch`. Removing an
integration entry also removes its stored runtime state.
