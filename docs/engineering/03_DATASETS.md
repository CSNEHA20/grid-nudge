# GridNudge: Dataset Master List (every feature covered, nothing dropped)

**Team:** VibeSync | **Compiled:** Oct 8, 2026 | **Purpose:** start building today without waiting on data

---

## 0. Read this first (honest framing)

**What I verified:** I searched for each dataset and confirmed from its listing/paper/page that it exists and what it contains. **What I did NOT do:** download any file or check row counts, formats, or current license terms. Some may need a free login (IEEE DataPort, Mendeley, ICPSR) or an API token. Budget 15 minutes per source to confirm access.

**The promise I can make, and the one I can't:**
- ✅ **Every feature has a data path**, because each one has a 3-level fallback: **Real data → Real proxy → Calibrated synthetic (documented)**. No feature needs to be dropped for lack of data.
- ❌ **Not every feature has real *Indian* data.** There is no public dataset of Indian EV user charging sessions, station queue times, or nudge responses. For those, you ground the twin with real data from elsewhere and label it as such. That is normal in simulation research and judges respect it when it's stated plainly.

### The most important finding in this whole search

There **is** real randomized-trial data on EV charging nudges, and it changes how you should set your simulator's behavior priors:

- A Canadian field experiment (Bailey, Brown, Shaffer, Wolak) found that **financial incentives strongly shifted charging, while a pro-social "moral suasion" nudge had no statistically detectable effect.** Incentive recipients raised their off-peak share of kWh from 59% to 77%, and peak-hour charging fell by about 49%. When incentives were removed, behavior reverted, so there was no habit formation. The replication data is on openICPSR (217 vehicles).
- An Australian randomized trial (390 EVs) found price incentives cut peak-period charging by roughly 27% for non-solar owners and 17% for solar owners, and midday charging gains came mostly from commuters and out-of-home charging.

**What this means for GridNudge:**
1. Set the simulator's priors so **cost framing has high uplift and green/"social good" framing has low or near-zero uplift.** Then the bandit *discovering* that is a credibility win, not a flaw.
2. Model **no carryover** (effect disappears when the incentive stops). It justifies keeping the bandit non-stationary/discounted.
3. These studies are Canada and Australia. Say so. Indian price sensitivity is reportedly high (per an Ember analysis), which supports a strong cost-frame prior, but that is not Indian experimental evidence.

---

## 1. Feature → dataset coverage matrix

| GridNudge feature | Level 1: real data | Level 2: real proxy | Level 3: calibrated synthetic |
|---|---|---|---|
| **EV user charging behavior** (arrival, duration, kWh) | ACN-Data; Harvard workplace set; Korean 72k-session set | IEEE India workplace set (synthetic but India-flavored, includes 2-wheelers) | Fit distributions from ACN/Korea, scale to India vehicle mix |
| **User archetypes / repeat behavior** | Harvard set (85 repeat users); Korean set (2,337 users) | ACN-Data user IDs | Mixture model with documented parameters |
| **Nudge response / uplift priors** | **Bailey et al. RCT replication data (openICPSR)**; published effect sizes (Canada, Australia, Konstanz RCT) | None for India | Behavior model whose parameters are set from RCT effect sizes, then stress-tested |
| **Journey / range prediction** | Vehicle Energy Dataset (VED) and eVED (real trips, includes PHEV/EV subset) | Physics model parameters from published EV specs | Physics energy model + Monte Carlo noise |
| **Battery degradation / SoH** | NASA PCoE, CALCE, MIT-Stanford-Toyota (Severson), Oxford, Sandia (batteryarchive.org), HUST, RWTH | BatteryML (packages several of these) | Semi-empirical calendar + cycle aging with literature parameters |
| **Battery stress features** (C-rate, DoD, temp, SOC dwell) | Same cell datasets above (they log these) | Wenzhou e-bus randomized usage data (pointer from a 2025 paper) | Derived from twin telemetry |
| **Station occupancy / queue** | Korean set (2,119 chargers, sessions with timestamps → occupancy); ACN session overlap | Harvard set (105 stations) | M/M/c queue calibrated from session arrival/duration |
| **Station locations / types / power ratings (India)** | Ministry of Power station list via Dataful (state, district, lat/long, charger type, rating); PIB and data.gov.in state totals | Bengaluru station set (IEEE DataPort) | Place synthetic stations by city weights |
| **Station reliability** | None found | None | Assumed outage rates, labeled |
| **Grid demand (India)** | Grid-India 1-hour demand/solar/wind (Mendeley); Delhi hourly load + weather 2018 to Mar 2025 (IEEE DataPort) | Indian peak-demand time series (IEEE DataPort) | Duck-curve shaped synthetic series |
| **Solar / renewable generation** | Grid-India hourly solar and wind; India hourly solar/wind capacity factors 1979 to 2022 (Zenodo); 72 kWp Karnataka plant hourly (IEEE DataPort) | Open-Meteo solar radiation → simple PV model | Synthetic solar curve |
| **Carbon intensity** | CEA CO2 Baseline Database (annual grid emission factors) | Grid-India hourly generation mix × fuel factors (approximation) | Fixed factor with evening-coal bump, labeled assumption |
| **Weather / temperature (range, HVAC, battery)** | Open-Meteo Historical API (hourly, ERA5-based); NASA POWER | Delhi dataset's weather columns | Seasonal sinusoid + heatwave events |
| **Tariffs / ToU** | State regulator orders (TNERC, MERC, APERC, Kerala SERC); CEEW tariff explainer; Ember analysis | News summaries of revisions | Assumed 3-slot ToU, parameterized |
| **Heatwave / demand spike events** | Delhi load + weather (real heat-load relationship) | Open-Meteo historical heatwave days | Multiplier on baseline load |
| **Fleet flexibility envelope** | Derived from session data (energy needed, plug-in duration, max power) | n/a | Derived from twin |
| **Ownership suitability ("Test Drive")** | VED trips (daily driving patterns), station lists (public charging access), tariffs | VAHAN / EV spec sources (from memory, verify) | Synthetic commute profiles |
| **Grid forecasting (Chronos vs baseline)** | Grid-India hourly series; Delhi series | Synthetic series | n/a (forecast on any series) |

---

## 2. Dataset catalog (with where to get them)

### 2.1 EV charging sessions (behavior, flexibility, occupancy)

| Dataset | What it is | Notes |
|---|---|---|
| **ACN-Data (Caltech/JPL)** | Real workplace charging sessions; papers cite 30k to 80k+ depending on date. Python client `acnportal` pulls data from a public API. Portal: ev.caltech.edu (dataset page at ev.caltech.edu/dataset). | Best overall source for arrival/duration/energy distributions. US workplace charging, so say so. Likely needs a free API token; confirm. ACN-Sim (open-source simulator) is also available and uses this data, useful as a reference design. |
| **Harvard Dataverse workplace charging** | 3,395 sessions, 85 repeat drivers, 105 stations, 25 sites, Nov 2014 to Oct 2015. `doi:10.7910/DVN/NFPQLW`. Mirrored on Kaggle. Columns include user, station, kWh, dollars, start/end. | Small but has user IDs and cost, good for archetypes and per-user repeat behavior. |
| **Korean charging transactions (Scientific Data, 2024)** | 72,856 sessions, 2,337 users, 2,119 chargers from a commercial operator. DOI `10.1038/s41597-024-02942-9`. | Best for station occupancy and queue calibration. |
| **IEEE DataPort: synthetic workplace EV sessions (India)** | 30 days, about 900 sessions/day, 90 AC and 10 DC chargers, includes electric two-wheelers and two car generations. | **Explicitly synthetic.** Useful only for India vehicle-type mix and charger types. Label it. |
| **Kaggle "Electric Vehicle Charging Dataset" (~1,320 sessions)** | Listed as sourced from Kaggle. | **Check whether it is synthetic before relying on it.** Many Kaggle EV sets are generated. |
| **Telangana EV station electricity consumption** | Monthly aggregate consumption per area, open government license. | Aggregate only. Not session-level. Low value. |

### 2.2 Nudge / incentive response (the behavior priors)

| Source | What you get | Use |
|---|---|---|
| **openICPSR: "Data and Code for: Show Me the Money!"** (project 202941, DOI `10.3886/E202941V1`) | Replication data and code from a randomized field experiment (control / nudge / financial reward), 217 vehicles, 2022. | **Only real nudge-vs-control EV dataset I found.** Use it to fit response curves and to validate your uplift estimator on real randomized data. Biggest credibility upgrade available. |
| **NBER Working Paper w31630 / AEJ: Economic Policy (2025), DOI `10.1257/pol.20230653`** | The paper and effect sizes. | Citable priors. |
| **Australian midday-charging RCT (390 EVs)** | Effect sizes in abstract (Berkeley Energy Institute POWER conference listing). | Priors for solar-aligned charging. Check whether data is public. |
| **Konstanz RCT on "green"/free charging via email notifications** | Randomized trial on notification-driven charging. | Direct evidence on notification effects. Check data availability. |

### 2.3 Battery aging / SoH / stress

| Dataset | Notes |
|---|---|
| **NASA PCoE Li-ion battery aging** (also random-usage and HIRF sets) | 18650 cells run to end of life; classic benchmark. Capacity regeneration spikes. |
| **CALCE (Univ. of Maryland)** | CS2/CX2 cells; cycling, storage, dynamic driving profiles. |
| **MIT-Stanford-Toyota (Severson et al.)** | 124 LFP/graphite cells under many fast-charging protocols. Best match for "fast charging effect on aging." |
| **Oxford Battery Degradation Dataset 1** | LCO pouch cells, drive-cycle style. |
| **Sandia (Preger et al.)** | NCA, NMC, LFP across temperatures/rates; hosted via batteryarchive.org. |
| **HUST** | 77 LFP cells. |
| **RWTH** | 48 cells. |
| **Wenzhou randomized battery usage** | Reported as data from 60 electric buses (mileage, cycles, ambient temperature). Check access. |
| **BatteryML (open-source platform)** | Already packages CALCE, MATR, HUST, SNL, RWTH in a common format. **Fastest route to usable data.** |
| **Directories** | GitHub "open-source-battery-data" list; BatteryBits spreadsheet; the "Lithium-ion battery data and where to find it" review (30+ datasets). |

**Honesty note:** these are *cell-level lab* datasets, not pack-level data from Indian EVs. Use them to validate that your semi-empirical aging structure behaves sensibly (shape, rate dependence), not to claim real pack lifetimes.

### 2.4 Journey energy / driving

| Dataset | Notes |
|---|---|
| **Vehicle Energy Dataset (VED)**, github.com/gsoh/VED | 383 cars in Ann Arbor, Nov 2017 to Nov 2018, about 374,000 miles; GPS trajectories, speed, energy, auxiliary power. Includes a small EV/PHEV subset (static data notes only a few pure EVs). Good for energy-vs-speed/temperature/HVAC relationships, not for EV-only claims. |
| **eVED (extended)** | Adds calibrated GPS traces and map attributes (speed limits, intersections) from OpenStreetMap-based sources. |

### 2.5 India grid, renewables, carbon

| Dataset | Notes |
|---|---|
| **Grid-India hourly demand, solar, wind (Mendeley Data, DOI `10.17632/y58jknpgs8`)** | Hourly, all five regional grids combined, Sept 2021 to June 2025 (version 2). Primary grid series. |
| **Delhi hourly load + weather, 2018 to 25 Mar 2025 (IEEE DataPort)** | 60,593 hourly rows, built for probabilistic forecasting. Ideal for the Delhi build day and heatwave modeling. May need free login. |
| **Hourly solar/wind capacity factors for India, 1979 to 2022 (Zenodo record 7824872)** | Plus reported daily POSOCO wind/solar/hydro 2012 to 2023. |
| **Karnataka 72 kWp solar plant, hourly, May 2021 to Sep 2024 (IEEE DataPort)** | Real plant output shape. |
| **Indian evening peak demand time series, 2014 to 2021 (IEEE DataPort)** | Regional peak MW. |
| **CEA CO2 Baseline Database for the Indian Power Sector** | Official grid emission factors; versions seen through v17 (FY 2020-21). Check the CEA site for a newer version. Annual averages, **not hourly marginal intensity**, so state that. |

### 2.6 Stations (India)

| Dataset | Notes |
|---|---|
| **Ministry of Power station list (via Dataful, dataset 23369)** | State, district, city, location name, lat/long, charger type, charger rating, connectors, with operator. Snapshot dated Oct 2025 in the listing. Great for realistic station placement and charger mix. |
| **PIB annexure and data.gov.in tables** | State-wise public station counts (one annexure totals 29,277). Counts differ by source and date, so cite the date. data.gov.in needs login. |
| **Bengaluru EV station dataset (IEEE DataPort)** | OpenChargeMap/PlugShare-derived, geocoded for Bengaluru. |

### 2.7 Tariffs

State regulators publish current orders; news pieces summarize revisions. Use primary orders for numbers and **read the current version before quoting any rate**, since several states revised in 2025.

- **Tamil Nadu (TNERC):** retains a time-of-day model for EV charging.
- **Maharashtra (MERC):** Tata Power MYT order (Jan 2025) includes EV single-part tariff and ToD rebates/charges.
- **Andhra Pradesh (APERC):** EV tariff order 2025-26.
- **Kerala:** revised ToD for EV charging stations (applies to stations, not home chargers).
- **Overviews:** CEEW "cost of charging electric vehicles" (state ranges and fixed charges); Ember on ToD and green tariffs.
- Delhi had only announced plans for EV ToD in older coverage, so check its current status.

### 2.8 Weather (free APIs)

- **Open-Meteo Historical API** (`archive-api.open-meteo.com/v1/archive`): 80+ years hourly, about 10 km, includes solar radiation. Free for non-commercial use, no key, CC BY 4.0 attribution. Fine for a hackathon; mind the terms if you commercialize later.
- **NASA POWER:** hourly/daily solar and meteorology, free.

```bash
# Delhi hourly temperature + solar radiation, example
curl "https://archive-api.open-meteo.com/v1/archive?latitude=28.61&longitude=77.21&start_date=2024-04-01&end_date=2024-06-30&hourly=temperature_2m,shortwave_radiation&timezone=Asia%2FKolkata"
```

### 2.9 Not re-verified (from memory, check before relying)

OpenStreetMap + Overpass (road/POI data); Open-Elevation or SRTM (elevation); US NHTS (travel survey, for trip-length distributions); VAHAN dashboard (EV registrations by state); manufacturer/ARAI EV spec sheets and EV Database sites (battery kWh, efficiency); UK Low Carbon London, ElaadNL (Netherlands), Dundee and Boulder charging datasets; Pecan Street (typically licensed).

---

## 3. True gaps and how to handle each (so no feature is dropped)

| Gap | Why it's a gap | What to do |
|---|---|---|
| **Indian EV user session data** | Nothing public found. | Fit from ACN/Korea/Harvard; apply India vehicle mix from the IEEE synthetic set; state "US/Korea-derived distributions." |
| **Indian nudge-response data** | Doesn't exist publicly. | Use the RCT effect sizes as priors, sweep parameters in a sensitivity analysis, and run the misspecification stress test. |
| **Station queue/wait times and reliability** | No open real telemetry. | Derive occupancy from Korean sessions; calibrate M/M/c; assume outage rates and label them. |
| **Pack-level battery aging in Indian conditions** | Public data is cell-level lab data. | Physics-inspired model validated on cell data; report relative plan differences, never lifespan. |
| **Hourly marginal carbon intensity for India** | Only annual emission factors found. | Use CEA annual factor with a clearly labeled evening adjustment, or report kWh shifted without CO₂ claims. |
| **Real feeder-level grid stress** | Not public. | Use national/Delhi hourly demand; define a synthetic feeder with capacity. |
| **Real traffic for journey uncertainty** | Not verified. | Model traffic as a speed multiplier with variance; calibrate speed-energy relation on VED. |

---

## 4. Build order: what to download and do today (about 3 hours, hard cap)

1. **Open-Meteo + Grid-India + Delhi load** (easiest, all hourly time series). Output: `grid_series.parquet`, `weather_delhi.parquet`. Run the Chronos vs seasonal-naive comparison on these.
2. **ACN-Data via `acnportal`** (or Harvard Dataverse CSV if the API token slows you). Output: session distributions → user archetypes → flexibility envelopes.
3. **Dataful station list** → `stations_india.parquet` (filter Delhi/Chennai).
4. **openICPSR RCT replication files** → fit response curves; set simulator priors; later validate your uplift estimator on it.
5. **BatteryML or NASA/CALCE** → sanity-check the aging model shape. Do this *after* the core loop runs.
6. **Tariff orders** for one or two states → ToU table in config.

**Folder layout:**
```
data/
├─ raw/            # untouched downloads + SOURCES.md (URL, date, license, citation)
├─ processed/      # parquet outputs
└─ ASSUMPTIONS.md  # every synthetic/assumed parameter, its source, and how to replace it
```

---

## 5. Licensing and citation checklist

- Record URL, access date, license and citation for **every** dataset in `SOURCES.md`.
- **Open-Meteo:** attribute ("Weather data by Open-Meteo.com", CC BY 4.0); free tier is for non-commercial use.
- **IEEE DataPort / Mendeley / ICPSR:** may require free accounts; cite DOIs.
- **ACN-Data:** cite the ACN-Data paper if you use it.
- **Government data:** check the specific license (Telangana's is Open Government License, India).
- Don't redistribute raw datasets in your repo; link to them and ship only processed samples where licensing allows.

---

## 6. One-paragraph "data story" for your submission

> *"GridNudge's digital twin is grounded in real public data wherever it exists: real charging-session distributions (ACN-Data, Korean operator data), real Indian grid demand and solar series (Grid-India, Delhi load and weather), real Indian station locations (Ministry of Power), and effect sizes from published randomized trials of EV charging incentives. Where no public data exists (Indian user response, station reliability), we use documented, parameterized assumptions and stress-test the policy against misspecified behavior. Every assumption is listed in our assumptions register."*
