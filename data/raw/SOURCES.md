# Data Sources Register

This document records all external data sources referenced or planned for calibration and simulation grounding, per AGENTS.md Rule 1.1 and Rule 8.

| ID | Dataset / Source | URL / Access Method | License | Purpose in GridNudge | Status |
|---|---|---|---|---|---|
| S1 | Open-Meteo Historical Weather (Delhi) | https://open-meteo.com/en/docs/historical-weather-api | Open Access (CC-BY 4.0) | Ambient temperature and solar irradiation for HVAC load model and solar generation profiles | Live fetched Open-Meteo API dataset (`data/processed/weather_delhi.parquet`) |
| S2 | Grid-India / POSOCO Hourly Series | https://posoco.in / Mendeley Data | Research / Open Data | Feeder base demand curves and national solar/wind profiles | Synthetic, shaped after POSOCO hourly load curves (`data/processed/grid_series.parquet`) |
| S3 | Delhi Load Profile (IEEE DataPort) | https://ieee-dataport.org | IEEE Academic / Open | Delhi distribution peak load shaping | Assumed / normalized profiles |
| S4 | ACN-Data EV Charging Sessions | https://ev.caltech.edu/dataset | CC BY 4.0 | EV arrival times, dwell durations, and requested energy distributions | Synthetic, shaped after Caltech ACN-Data session distributions (`data/processed/sessions_profile.parquet`) |
| S5 | Delhi EV Charging Station Registry | Ministry of Power / BEE / Dataful | Public Domain (Government of India) | Station locations, connector types, and charger power capacities | Synthetic, shaped after Delhi BEE charging station registry (`data/processed/stations_delhi.parquet`) |
| S6 | DERC (Delhi Electricity Regulatory Commission) Tariff Order | https://www.derc.gov.in | Public Order | Time-of-Day (ToD/ToU) tariff rates and peak surcharge hours | Configured in `config/tariffs.yaml` |
| S7 | Battery Aging Dataset (NASA / Oxford Battery Data) | NASA Prognostics Center of Excellence | Public Domain | Empirical cell degradation parameters for relative stress scoring | Synthetic relative battery stress formulation |
| S8 | openICPSR EV Randomized Field Trial (Bailey et al.) | https://www.openicpsr.org/openicpsr/project/202941 (DOI: 10.3886/E202941V1) | Open Access | Causal nudge response priors (financial incentive -49% peak vs moral suasion flat) for LinTS bandit pretraining | Synthetic, shaped after openICPSR 202941 RCT distributions (`data/processed/rct_nudge_response.parquet`) |
| S9 | Battery Aging & Fast Charging Benchmark (Severson et al. / CALCE) | Nature Energy 4, 383-391 (2019) / CALCE | Academic Open Data | Empirical battery degradation vs C-rate, temperature, and DoD | Synthetic, shaped after Severson/CALCE cell aging protocols (`data/processed/battery_aging_reference.parquet`) |
| S10 | Vehicle Energy Dataset (VED / eVED) | https://github.com/gsoh/VED (Oh et al. 2020) | Creative Commons / Academic | Real trip speed, ambient temperature, HVAC load, and energy consumption (Wh/km) | Synthetic, shaped after VED telematics distributions (`data/processed/ved_trip_energy.parquet`) |

