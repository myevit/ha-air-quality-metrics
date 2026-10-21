# Air Quality Metrics for Home Assistant — DEPRECATED

> **Deprecated: `myevit/ha-air-quality-metrics`. Do not use this fork for new installs.**
> For a local Canadian PM2.5 smoke estimate, prefer Home Assistant's built-in
> [Statistics](https://www.home-assistant.io/integrations/statistics/) and
> [Template](https://www.home-assistant.io/integrations/template/) helpers with a
> built-in dashboard card. This deprecation applies to this fork, not upstream.
>
> Native rolling-window helpers do **not** guarantee exact parity with this
> integration's completed-hour calculation. Validate source units/freshness,
> continuous valid history, coverage, index/category output and missing-data
> behavior before switching consumers. A PM2.5-only local estimate is not full
> three-pollutant or official community AQHI; keep official regional AQHI separate.
>
> Existing installations may remain as a fallback until their native replacement
> has warmed up and is verified. Replace dashboard/automation consumers first,
> then retire unused integration entries and uninstall only when safe. This
> notice does not disable or uninstall anything. License, history and release
> tags remain available for reference and rollback. The inherited documentation
> below is historical reference, not a commitment to new features or a
> recommendation to install this deprecated fork.

[![GitHub Release][releases-shield]][releases]
![Project Stage][project-stage-shield]
[![License][license-shield]](LICENSE.md)

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]

[![Github Actions][github-actions-shield]][github-actions]
![Project Maintenance][maintenance-shield]
[![GitHub Activity][commits-shield]][commits]

A Home Assistant custom component that calculates precise EPA Air Quality Index
(AQI and NowCast) and Indoor Air Quality (IAQI) values from raw sensor data.

> Fork of [ex-nerd/ha-air-quality-metrics](https://github.com/ex-nerd/ha-air-quality-metrics)
> with a targeted fix for valid all-zero NowCast windows. The inherited outdoor
> calculations average recorder change samples in rolling age-based hourly buckets,
> not time-weighted, fixed completed hours; sparse change history can leave hours
> missing. This fix does not establish official EPA AQI/NowCast compliance.

## Native Canadian AQHI smoke / PM2.5

The **Outdoor — Canadian AQHI smoke / PM2.5 (local estimate)** profile implements
Canada's one-hour PM2.5 smoke component on the **1–10+** scale with Canadian
low/moderate/high/very-high categories. It uses one outdoor PM2.5 source and
time-weighted complete-hour recorder history; it does not reuse US AQI buckets.
This is a **local PM-only estimate**, not complete three-pollutant or official
community AQHI/AQHI-Plus. Existing US/indoor entries remain compatible.

See [method, primary sources, coverage policies, and native entity/card contract](docs/canadian-aqhi.md).

## Features

Local calculation of air quality metrics for either indoor or outdoor sensors,
for a variety of pollutants.

- Indoor Sensors
  - **IAQI**: ATMO produced this scale and formula as a way to produce a rating
    similar to AQI, but for indoor spaces.
    - https://atmotube.com/blog/indoor-air-quality-index-iaqi
- Outdoor Sensors
  - **EPA NowCast AQI**: This is what most people think of when they hear "AQI."
    This "real time" metric still requires valid data from 2 out of the previous
    3 hours, but will produce a reading on the AQI scale much better suited to
    people wanting to know what the air quality is like "right now," whether the
    concern is pollen, smog, or wildire smoke.
    - https://en.wikipedia.org/wiki/NowCast_(air_quality_index)
    - https://document.airnow.gov/technical-assistance-document-for-the-reporting-of-daily-air-quailty.pdf
  - **EPA AQI**: Intended as a general air quality score spread across an entire day
    (midnight to midnight), the formula used by this integration takes a more
    liberal approach and looks at 24 hour windows to produce a smoother value
    curve.
    - https://en.wikipedia.org/wiki/Air_quality_index#United_States
    - https://en.wikipedia.org/wiki/Air_quality_index#Computing_the_AQI


### Planned Future Additions

Future metrics to be implemented [RSN](https://en.wiktionary.org/wiki/real_soon_now):

- **CAQI**: This is the European equivalent to the EPA's AQI. The scale and
  formulas are different.
  - https://en.wikipedia.org/wiki/Air_quality_index#CAQI
- **Spec-compliant AQI and NowCast**: This integration uses a "rolling window"
  approach to calculating AQI and Nowcast, but the official calculations are
  meant to be once per hour for NowCast, and midnight-to-midnight for AQI. I'm
  considering adding the spec-compliant calculations for those who want them.
- **NowCast Trend**: When following the true "only once per hour" calculations,
  the EPA allows for a "trend" rating in NowCast based on more recent data that
  hasn't yet been added to the calculation:
  - https://document.airnow.gov/airnow-fire-and-smoke-map-questions-and-answers.pdf
- **RESET**: This group produces standards and programs related to indoor
  commercial space. They have published information about air quality, but I
  haven't yet had time to see if there is anything that can be added to this
  integration.
  - https://reset.build/standard/air

Room Mode:

Instead of setting up these metrics by selecting individual sensors, I like the
idea of selecting a room and having the integration auto-detect all relevant
sensors within that room.

Lovelace templates / blueprints:

I'm still trying to figure out how to add either templates or blueprints based
on the gauge card that I use in my own setup:

<img width="461" height="246" alt="nowcast_card_screenshot" src="https://github.com/user-attachments/assets/a3f0ed5b-0741-4677-a8e0-f827117b9b0d" />

For now, you can replicate it via something like this:

```yaml
type: gauge
name: "NowCast"
entity: sensor.outdoor_air_quality_nowcast_aqi
needle: true
min: 0
max: 500
segments:
  - from: 0
    color: "#00e400"
  - from: 50
    color: "#ffff00"
  - from: 100
    color: "#ff7e00"
  - from: 150
    color: "#ff0000"
  - from: 200
    color: "#8f3f97"
  - from: 300
    color: "#7e0023"
```

```yaml
type: gauge
name: "IAQI"
entity: sensor.indoor_air_quality_iaqi
needle: true
min: 0
max: 100
segments:
  - from: 0
    color: "#d32758"
  - from: 21
    color: "#ea6445"
  - from: 41
    color: "#fcb35d"
  - from: 61
    color: "#b0c160"
  - from: 81
    color: "#56ceb5"
```

## How can you help?

- **Translations**. I might use AI to help with some of the code but I don't
  trust translations to be accurate within the contexts that they need to be.
- **More Metrics**. You can see the list above for metrics that I'm already
  looking into, but please suggest any others that I haven't learned about yet.
- **Icon**. I'm not an artist. If you have a good idea for a brand logo for this
  integration, please submit a pull request. I ask only that it be drawn by you
  and not an AI.
- **Lovelace templates**. I plan to add templates/blueprints to this
  integration, but I am not a UI designer so would welcome contributions from
  anyone who has good ideas about how to render these metrics into Home
  Assistant dashboards.
- **More sensor tests**. I have some older AirGradient hardware but nothing with
  sensors for some of the more exotic gasses/particles. I'd love some feedback
  from anyone who does, or recommendations for what hardware I should get so I
  can run my own tests.
- **Device classes**. Know anyone on the Home Assistant core team who can
  provide insight about adding new device classes? It would be great to support:
  - **VOC Index** like from https://esphome.io/components/sensor/sgp4x/
  - **NOx Index** like from https://esphome.io/components/sensor/sgp4x/
  - **Formaldehyde** like from https://esphome.io/components/sensor/sfa30/
    or https://esphome.io/components/sensor/sm300d2/
  - **IAQI**: The existing AQI device class isn't entirely appropriate because AQI
    measures 0–500 with lower numbers representing clean air, whereas IAQI is
    0-100 with higher numbers representing clean air.

## Installation

### Method 1: HACS (Recommended)

1. Open **HACS** in your Home Assistant panel.
2. Click the three dots in the top-right corner and select **Custom repositories**.
3. Paste your repository URL: `https://github.com/ex-nerd/ha-air-quality-metrics`
4. Select **Integration** as the category and click **Add**.
5. Find **Air Quality** in the HACS store, click **Download**, and restart Home Assistant.

### Method 2: Manual Installation

1. Download the latest release source code.
2. Copy the contents of the `custom_components/air_quality_metrics` folder into your Home Assistant's `config/custom_components/air_quality_metrics` directory.
3. Restart Home Assistant.

## Configuration

Once installed, you can configure the integration directly through the Home Assistant user interface:

1. Navigate to **Settings** -> **Devices & Services**.
2. Click **+ Add Integration** in the bottom right corner.
3. Search for **Air Quality** and follow the on-screen configuration flow.

## Bug Reports & Feedback

If you encounter issues or have feature requests, please log them in our official [Issue Tracker](https://github.com/ex-nerd/ha-air-quality-metrics/issues).

## Code Owners

- [@ex-nerd](https://github.com/ex-nerd)

[releases]: https://github.com/ex-nerd/ha-air-quality-metrics/releases
[releases-shield]: https://img.shields.io/github/v/release/ex-nerd/ha-air-quality-metrics?include_prereleases&style=flat-square
[project-stage-shield]: https://img.shields.io/badge/fork%20stage-deprecated-orange.svg?style=flat-square
[license-shield]: https://img.shields.io/github/license/ex-nerd/ha-air-quality-metrics?style=flat-square
[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green?style=flat-square
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green?style=flat-square
[github-actions-shield]: https://img.shields.io/github/actions/workflow/status/ex-nerd/ha-air-quality-metrics/tests.yml?branch=main&style=flat-square
[github-actions]: https://github.com/ex-nerd/ha-air-quality-metrics/actions
[maintenance-shield]: https://img.shields.io/badge/fork%20status-deprecated-orange.svg?style=flat-square
[commits-shield]: https://img.shields.io/github/commit-activity/m/ex-nerd/ha-air-quality-metrics?style=flat-square
[commits]: https://github.com/ex-nerd/ha-air-quality-metrics/graphs/commit-activity
