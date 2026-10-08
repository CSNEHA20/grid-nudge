# Data Sources Register

This document records all external data sources referenced or planned for calibration and simulation grounding, per AGENTS.md Rule 1.1 and Rule 8.

| ID | Dataset / Source | URL / Access Method | License | Purpose in GridNudge | Status |
|---|---|---|---|---|---|
| S1 | Open-Meteo Historical Weather (Delhi) | https://open-meteo.com/en/docs/historical-weather-api | Open Access (CC-BY 4.0) | Ambient temperature and solar irradiation for HVAC load model and solar generation profiles | Synthetic fallback ready / planned download |
| S2 | Grid-India / POSOCO Hourly Series | https://posoco.in / Mendeley Data | Research / Open Data | Feeder base demand curves and national solar/wind profiles | Synthetic profile calibrated to typical Delhi load curve |
| S3 | Delhi Load Profile (IEEE DataPort) | https://ieee-dataport.org | IEEE Academic / Open | Delhi distribution peak load shaping | Assumed / normalized profiles |
| S4 | ACN-Data EV Charging Sessions | https://ev.caltech.edu/dataset | CC BY 4.0 | EV arrival times, dwell durations, and requested energy distributions | Proxy dataset for EV charging session statistics |
| S5 | Delhi EV Charging Station Registry | Ministry of Power / BEE / Dataful | Public Domain (Government of India) | Station locations, connector types, and charger power capacities | Modeled Delhi public charger network |
| S6 | DERC (Delhi Electricity Regulatory Commission) Tariff Order | https://www.derc.gov.in | Public Order | Time-of-Day (ToD/ToU) tariff rates and peak surcharge hours | Configured in `config/tariffs.yaml` |
| S7 | Battery Aging Dataset (NASA / Oxford Battery Data) | NASA Prognostics Center of Excellence | Public Domain | Empirical cell degradation parameters for relative stress scoring | Relative battery stress model |
