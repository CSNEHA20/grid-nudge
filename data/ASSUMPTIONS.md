# Assumptions Register

In accordance with AGENTS.md Rule 1.1 and Rule 8, every assumed or synthetic parameter is documented below.

| Parameter Category | Assumed Value / Model | Rationale & Context | How to Ground with Real Data |
|---|---|---|---|
| User Nudge Response | Logit model with archetype sensitivities: Cost (high), Green (near-zero), Battery (moderate). | Indian EV consumer nudge trial data is not publicly available. Informed by published EV behavioral experiments (e.g., Canadian and Australian trials). | Run randomized A/B trial with local utility or fleet operator. |
| Spontaneous Shifting Probability | 5%–15% baseline shift probability without any intervention. | Users occasionally shift charging due to existing routine or ToU awareness without receiving a nudge. | Empirical pre-intervention baseline observations. |
| Driver Fatigue Decay | Half-life of 3 days for alert fatigue; maximum 3 nudges per day cap. | Human factors literature on notification habituation and alert burnout. | Telematics / app open rate telemetry. |
| Station Reliability & Outages | Mean time between failures: 7 days; repair duration: 4 hours; MTBF simulated per connector. | Indian public charging station downtime is simulated based on field reports. | Real-time OCPP status heartbeat feeds. |
| Reserve State-of-Charge (SOC) | Minimum target arrival SOC reserve = 10% (0.10). | Buffer required to prevent stranding risk. | Driver customizable preference setting. |
| Journey Energy Model | Nominal 150 Wh/km base consumption with ambient temperature HVAC penalty and traffic scale factors. | Physics-inspired model based on standard compact EV sedans/SUVs. | Vehicle telematics (CAN bus / OBD-II) real-world log. |
| Feeder Capacity | Nominal feeder threshold: 12 MW per substation zone with 2,000 EVs. | Distribution grid feeder sizing for suburban Delhi feeder. | SCADA telemetry from DISCOM (e.g., BRPL / BYPL). |
| Grid Base Demand Series | Synthetic 15-min series shaped after POSOCO national load profiles and diurnal patterns. | Scaled to 12 MW feeder context with daytime and evening peaks. | DISCOM distribution feeder SCADA feeds. |
| EV Charging Sessions | Synthetic arrival, dwell, and energy distributions shaped after Caltech ACN-Data. | Parameterized log-normal dwell and energy distributions. | Charge point operator (CPO) session records (`data/processed/sessions_profile.parquet`). |
| Charging Station Network | Synthetic station inventory shaped after BEE Delhi charging station directory. | Plausible distribution of 3.3 kW AC, 7.4 kW AC, and 50 kW DC chargers. | Open BEE public station API feed (`data/processed/stations_delhi.parquet`). |
| Behavioral Uplift Priors | Bailey et al. (openICPSR 202941) Canadian RCT: Cost frame (-49% peak), Green frame (flat). | Real RCT replication dataset used for contextual bandit offline pretraining. | Causal A/B field experiment records (`data/processed/rct_nudge_response.parquet`). |
| Battery Aging Reference | Severson et al. (Nature Energy 2019) & CALCE cell cycle aging vs C-rate & DoD. | Physics-inspired relative stress scoring validated on 124 experimental LFP/graphite cells. | Real pack battery laboratory cycling logs (`data/processed/battery_aging_reference.parquet`). |
| Journey Energy Model Grounding | Vehicle Energy Dataset (VED) speed, HVAC load, and road grade curves. | Real telematics speed-energy relationships used to calibrate physics range prediction. | Real-world EV CAN-bus trip datasets (`data/processed/ved_trip_energy.parquet`). |

