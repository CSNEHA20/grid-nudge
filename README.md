# GridNudge

> **A Safety-Gated, Uplift-Aware EV Charging Decision System**  
> **Track:** Waste & Energy → EV Nudges | **Hackathon:** Environmental Hacks — WeMakeDevs × AWS  
> **Team VibeSync:** Vishal ([@Vishallakshmikanthan](https://github.com/Vishallakshmikanthan)) & Sneha ([@CSNEHA20](https://github.com/CSNEHA20))

---

## 1. Executive Summary & Core Thesis

Urban electric vehicle adoption in mega-cities like Delhi presents a critical infrastructure challenge: unmanaged, concurrent residential and commercial charging during the evening peak window (18:00–22:00) threatens distribution feeder transformer overloads.

Conventional demand-side management relies on broadcast notifications, inducing driver alert fatigue, high opt-out rates, and unintended secondary rebound peaks.

**GridNudge** solves this through a principled separation of concerns:
> **Physics, forecasts, and hard constraints decide WHAT charging plan is safe and beneficial.**  
> **A contextual bandit with a first-class `none` action decides WHETHER and HOW to persuade.**  
> **The LLM never decides; it only phrases approved factual tokens into natural language.**

```
+---------------------------------------------------------------------------------+
|                               DIGITAL TWIN                                      |
|            (2,000 EVs, 15-min Timesteps, Seeded NumPy CRN, Delhi Feeder)        |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
|                                 PERCEPTION                                      |
|      * Calibrated Journey Confidence (P(arrival SOC >= 10% reserve))             |
|      * Relative Battery Stress & SoH Range                                      |
|      * Public Station Queue Wait (Erlang-C) & Grid Feeder Stress               |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
|                                  PLANNER                                        |
|     Enumerates candidate plans: default, delay, slow_charge, relocate           |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
|                          SAFETY FILTER #1 (Python + Cedar)                      |
|      VETOES any plan where journey confidence lower bound < 90% (0.90)          |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
|                         PERSUASION (Linear Thompson Sampling)                   |
|     Selects arm: {none} OR {plan x frame x timing}; learns silence on routine   |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
|                              FLEET ALLOCATOR                                    |
|     Enforces 8% attention budget, daily caps, and anti-herding time staggering  |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
|                     SAFETY FILTER #2 & NUMERIC LANGUAGE VERIFIER                |
|     Validates Cedar policy; verifies numbers against approved facts payload     |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
|                      CAUSAL REWARD LOOP & POSTERIOR UPDATE                      |
|     Updates LinTS bandit posterior via single-writer Lambda & DynamoDB          |
+---------------------------------------------------------------------------------+
```

---

## 2. Multi-Seed Benchmark Evaluation (5 Seeds, 2,000 EVs)

All metrics below originate from multi-seed runs evaluated under Common Random Numbers (CRN) recorded in `results/summary.csv`:

| Policy ID | Policy Description | Evening Peak Load (MW) | Peak Reduction (%) | Energy Shifted (kWh) | Nudges / User / Day | Opt-Out Rate (%) | Attributable Stranded Trips | Regret vs Oracle |
|---|---|---|---|---|---|---|---|---|
| **B0** | Uncontrolled Default | 21.68 ± 0.28 | 0.00% | 0.0 | 0.00 | 0.00% | 0 | 486.2 |
| **B1** | Broadcast Delay Nudges | 20.38 ± 0.19 | 6.02 ± 0.88% | 2,816 ± 180 | 0.99 ± 0.02 | 0.72% | 0 | 294.1 |
| **B2** | Safe Rule-Based (1/day cap) | 20.38 ± 0.19 | 6.02 ± 0.88% | 2,816 ± 180 | 0.99 ± 0.02 | 0.72% | 0 | 294.1 |
| **B3** | Plain Bandit (No Allocator) | 21.39 ± 0.18 | 1.32 ± 0.42% | 668 ± 94 | 0.54 ± 0.01 | 0.38% | 0 | 382.4 |
| **B4** | **GridNudge Full Pipeline** | **20.47 ± 0.14** | **5.61 ± 0.66%** | **3,131 ± 142** | **0.53 ± 0.01** | **0.35%** | **0** | **163.6** |

### Benchmark Takeaways:
1. **Attention Efficiency:** GridNudge achieves comparable evening peak reduction (5.61% vs 6.02%) while **cutting driver notification volume in half** (0.53 vs 0.99 nudges/user/day).
2. **Lowest Driver Fatigue:** Lowest opt-out rate across all policies (0.35% vs 0.72% in broadcast).
3. **Lowest Oracle Regret:** LinTS causal bandit achieves the lowest regret (163.6), learning when drivers shift spontaneously without needing attention spent.
4. **Zero Attributable Stranded Trips:** 100% adherence to the journey reserve safety invariant ($P(\text{SOC}_{\text{arrival}} \ge 10\%) \ge 90\%$).

---

## 3. Data Grounding & Provenance Honesty

Per AGENTS.md Rule 1.1 and Rule 8, we state data sources and modeling boundaries with complete transparency:

| Dataset / Dimension | Source & Method | Status in GridNudge |
|---|---|---|
| **Delhi Weather & Temperatures** | Open-Meteo Historical Archive (Delhi summer 45°C heatwaves) | Grounded processed series (`weather_delhi.parquet`) |
| **Grid Feeder Load & Solar Profile** | Grid-India / POSOCO hourly demand series | Grounded normalized profiles (`grid_series.parquet`) |
| **EV Session Dwell & Energy** | ACN-Data / Caltech EV Charging Dataset & Harvard Dataverse | Calibrated proxy distributions (`sessions_profile.parquet`) |
| **Delhi Charging Plazas** | Bureau of Energy Efficiency (BEE) / Ministry of Power | Delhi public fast charger registry (`stations_delhi.parquet`) |
| **Electricity Tariffs** | Delhi Electricity Regulatory Commission (DERC) ToU Order | Grounded configuration (`config/tariffs.yaml`) |
| **Driver Nudge Response Priors** | Literature-informed discrete choice model (A/B EV trial data) | Calibrated synthetic with hidden misspecification testing |
| **Battery Aging** | Semi-empirical Arrhenius + C-rate model (NASA/Oxford battery data) | Relative stress scoring (not absolute lifespan claims) |

---

## 4. AWS Serverless Architecture

GridNudge is architected with a local-first Python decision engine wrapped by a thin serverless AWS Lambda and API Gateway deployment (`infra/template.yaml`):

```
                        +----------------------+
                        |  Amazon API Gateway  |
                        +----------------------+
                                   |
         +-------------------------+-------------------------+
         |                         |                         |
         v                         v                         v
   POST /decide             POST /outcomes             GET /metrics
   (Lambda decide)         (Lambda outcomes)         (Lambda metrics)
         |                         |                         |
         v                         v                         v
+------------------+      +------------------+      +------------------+
| DynamoDB         |      | SQS FIFO Queue   |      | S3 Log Bucket    |
| - UserState      |      | (single-writer)  |      | (audit trail)    |
| - ModelState     |      +------------------+      +------------------+
| - Decisions      |               |
+------------------+               v
                         +-------------------+
                         | Lambda            |
                         | RewardUpdateFn    |
                         | (ReservedConcurr=1|
                         +-------------------+
```

---

## 5. Quickstart & Verification (3 Commands)

### 1. Install & Run Tests
```bash
python -m pip install -e .[dev]
python -m pytest -q
```

### 2. Validate Datasets & Schemas
```bash
python data/scripts/validate.py
```

### 3. Launch High-Fidelity Next.js Dashboard
```bash
cd dashboard
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to inspect `/live`, `/decisions`, `/evaluation`, `/twin`, and `/testdrive`.

---

## 6. Repository Structure

```
gridnudge/
├── contracts/             # Authoritative DecisionRecord schema & TS types
├── config/                # Sim, safety, tariffs, and behavioral configurations
├── data/
│   ├── processed/         # Grounded parquet series (weather, grid, sessions, stations)
│   └── scripts/           # Standalone reproducible fetchers & validators
├── gridnudge/
│   ├── contracts.py       # Pydantic v2 domain schemas
│   ├── pipeline.py        # 6-stage decision orchestrator with fail-silent wrapper
│   ├── planner.py         # Feasible charging plan generator
│   ├── allocator.py       # Attention budget & anti-herding slot allocator
│   ├── perception/        # Journey confidence, battery stress, grid & station intelligence
│   ├── persuasion/        # Linear Thompson Sampling contextual bandit & causal reward
│   ├── safety/            # Python invariants & AWS Cedar authorization policies
│   ├── language/          # Numeric verifier & multilingual templates (en/hi/ta)
│   └── testdrive.py       # Digital Test Drive 52-week ownership simulator
├── twin/                  # Vectorized digital twin (2,000 EVs, CRN streams, events)
├── eval/                  # CRN baselines (B0-B4), OPE (IPS/DR), metrics, calibration
├── services/              # Thin AWS Lambda service adapters & GridNudgeClient
├── infra/                 # AWS SAM serverless infrastructure template
└── dashboard/             # High-fidelity Next.js App Router dashboard
```

---

## 7. License & Compliance

Built for the **Environmental Hacks Hackathon (WeMakeDevs × AWS)**.  
Licensed under the Apache License 2.0.
