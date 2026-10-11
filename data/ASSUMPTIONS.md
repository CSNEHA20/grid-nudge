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
| EV Charging Sessions | Synthetic arrival, dwell, and energy distributions shaped after Caltech ACN-Data. | Parameterized log-normal dwell and energy distributions. | Charge point operator (CPO) session records. |
| Charging Station Network | Synthetic station inventory shaped after BEE Delhi charging station directory. | Plausible distribution of 3.3 kW AC, 7.4 kW AC, and 50 kW DC chargers. | Open BEE public station API feed. |
