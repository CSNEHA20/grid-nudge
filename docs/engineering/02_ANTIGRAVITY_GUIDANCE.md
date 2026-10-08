# GridNudge: Locked Build Guidance for Antigravity

> **How to use this file**
> 1. Copy it to the **repo root as `AGENTS.md`** (Antigravity reads `AGENTS.md`, and `GEMINI.md` if you want Antigravity-only overrides; workspace rules can also live in `.agents/rules/`). Keep the name `GRIDNUDGE_ANTIGRAVITY_GUIDANCE.md` too if you want a human copy.
> 2. Give agents **one phase at a time** using the prompts in §14. Don't ask for "the whole project" in one go.
> 3. In Antigravity's autonomy settings, prefer **review-before-run for terminal commands that touch AWS** (`sam deploy`, `aws ...`, anything with `delete`). Let agents run local tests freely.
> 4. Items marked **[VERIFY]** are library/API details I could not confirm. Have the agent check the current docs before coding against them.

**Team:** VibeSync (Vishal, Sneha) | **Event:** Environmental Hacks (WeMakeDevs x AWS), Oct 8 to 11, 2026 | **Track:** Waste & Energy → EV Nudges
**Deliverables:** working system, deployed on AWS, 3-minute demo video (judges do not see a live demo). *Confirm the exact submission deadline on the portal.*

---

## 1. Rules for every agent (non-negotiable)

1. **Never invent numbers.** Any figure shown in UI, README, or video must come from a logged run. Everything produced by the twin is labeled **"Simulation"**.
2. **Never present battery or range predictions as guarantees.** Use ranges and confidence. Never say "your battery will last N years."
3. **Safety beats reward.** A plan that fails a safety invariant is removed *before* the bandit sees it. Safety is a constraint, never a reward term.
4. **Fail silent.** If any perception model, Cedar call, forecaster or verifier errors or times out → **send no nudge** and log it.
5. **The LLM never decides.** ML/optimization decides *what*; the LLM only phrases *how*, using verified facts, with a numeric verifier (§9.4).
6. **One contract:** the `DecisionRecord` (§6.1) is the single data structure passed between all stages and logged. Don't invent side channels.
7. **No new scope.** Build only what is in §2 "Locked scope". Anything else goes in `docs/FUTURE.md`.
8. **Test what you build.** Each module ships with pytest tests (§12). Don't claim "done" until tests pass and you've run the module end to end.
9. **Reproducibility:** all randomness flows from a seeded `numpy.random.Generator`. Baselines and GridNudge use **common random numbers** (same seed streams).
10. **Secrets:** never hardcode AWS keys. Use a named AWS profile / environment variables. Never commit `.env`.
11. **Cost safety:** don't create always-on resources (SageMaker real-time endpoints, NAT gateways, provisioned capacity). Prefer on-demand/serverless.
12. **Keep a running log** in `docs/BUILD_LOG.md`: what was built, what is stubbed, known issues.
13. **When blocked >15 minutes, stop and use the documented fallback** (§13 kill rules), don't thrash.

---

## 2. The locked project

### 2.1 One-liner
**GridNudge is a safety-gated, uplift-aware EV charging decision system.** Physics-based models and forecasts decide the *safest beneficial charging plan*; a causal contextual bandit decides *whether, to whom, and how* to persuade within a limited attention budget; everything is learned and audited inside an EV-energy digital twin.

### 2.2 The problem (Waste & Energy → EV Nudges)
- Evening EV charging stacks on top of the grid's evening peak, and renewable midday energy is under-used.
- Generic notifications cause alert fatigue and mostly nudge people who would have shifted anyway.
- Naive "charge later" advice can strand users with low battery before a trip, which destroys trust.

### 2.3 The solution in four sentences
1. A **digital twin** simulates EV users, batteries, trips, stations with queues, grid load, solar, tariffs and injected events.
2. **Perception** produces calibrated quantities: Journey Confidence, battery stress, station wait at arrival time, grid stress and green windows.
3. A **planner** proposes safe charging plans (delay, relocate, slow charge, top-up); a **bandit with a first-class "none" action** learns who actually changes behavior (uplift) and which framing works; a **fleet allocator** spends a limited nudge budget while staggering timing to avoid a rebound peak.
4. A **safety gate** (Cedar + code invariants) and an **LLM language layer** (Bedrock, with a numeric verifier) deliver the nudge; the response becomes a causal reward that updates the policy.

### 2.4 What judges must remember (the four moments)
1. **Safety veto, shown live:** a cost-saving nudge is blocked because the user's next-morning journey confidence fell below threshold. Cedar verdict and numbers visible.
2. **Learned silence:** the system stays quiet for users who would shift anyway; nudges per user stay low.
3. **Bending the curve:** inject "Heatwave" → broadcast baseline spikes, GridNudge flattens the evening peak.
4. **Calibrated confidence + Flexibility Forecast:** "Journey Confidence 94%" backed by a calibration plot, and "X MW ± Y MW shiftable (simulation)".

### 2.5 Locked scope

**CORE (must work):**
- Digital twin (vectorized, ~2,000 EVs), event injector (heatwave, solar drop, station outage, tariff change)
- Journey Confidence (physics model + Monte Carlo + calibration)
- Planner with safety veto; battery stress score (simple semi-empirical)
- LinTS contextual bandit with "none" arm, fatigue state, propensity logging, uplift
- Greedy allocator with budget + staggering + capacity limit
- Safety: Python invariants + Cedar policies + fail-silent
- Baselines on common random numbers + evaluation harness + charts
- AWS decision path: API Gateway + Lambda + DynamoDB + S3 + SQS (reward loop)
- Dashboard (Next.js) with event button, curves, decision card, metrics
- README, assumptions register, 3-minute video

**ADVANCED (in this order, only after CORE works):**
1. Chronos grid forecasting vs seasonal-naive
2. Station queue forecast + `relocate` plan
3. Bedrock message rendering + numeric verifier
4. Strands operator copilot (2 to 3 tools)
5. Flexibility Forecast widget
6. Doubly-robust off-policy evaluation panel + misspecification stress test
7. OR-Tools allocator vs greedy gap
8. Digital Test Drive (ownership confidence, includes honest "not suitable" path)

**FUTURE (slide only):** deep/offline RL, causal forests, GNN over feeder topology, federated learning, V2G, real OCPP integration, fleet-validated battery models.

**Explicitly not building:** LSTM/TFT training, battery XGBoost, multi-agent RL, Kinesis, SageMaker training pipelines, always-on endpoints, a mobile app, real payments.

---

## 3. System architecture

```
                DIGITAL TWIN (runner: local or small EC2/Fargate task)
   users · batteries · trips · stations+queues · grid+solar · tariffs · events
        │  per 15-min interval: batch of eligible EVs + grid forecast
        ▼
 ┌───────────────────────── AWS DECISION PATH ──────────────────────────┐
 │ API Gateway ─► Lambda: decide_batch                                    │
 │   1 perception   journey · battery stress · station wait · grid stress │
 │   2 planner      enumerate plans → predict outcomes                    │
 │   3 SAFETY #1    invariants + Cedar → drop unsafe plans                │
 │   4 persuasion   LinTS(none ∪ plan×frame×timing) → uplift + propensity │
 │   5 allocator    budget (shadow price) + stagger + capacity            │
 │   6 SAFETY #2    final verify; any error ⇒ fail-silent                 │
 │   7 language     Bedrock paraphrase + numeric verifier (or template)   │
 │   DynamoDB: UserState · ModelState · Decisions      S3: decision logs  │
 └───────────────┬───────────────────────────────────────────────────────┘
                 ▼
        nudges delivered to simulator ─► simulator applies hidden behavior model
                 ▼
        POST /outcomes ─► SQS FIFO ─► Lambda: reward_update (single writer)
                 ▼
        causal reward → posterior update → logs (S3) → OPE / evaluation
                 ▼
 Dashboard (Next.js on Amplify) ◄─ GET /metrics, /decision/{id}, replay.json
 Operator copilot (Strands + Bedrock) ◄─ reads Decisions table
```

**Design decisions to preserve:**
- **Batch decisions per interval** (hundreds of eligible EVs per request), not one Lambda per EV.
- **Core logic is a pure Python package (`gridnudge/`)** used by Lambda handlers *and* the local runner. State is behind a `StateStore` interface with `InMemoryStore` (dev/tests) and `DynamoStore` (AWS). This lets agents build and test everything locally before touching AWS.
- **Simulator time ≠ wall-clock.** The twin emits outcome events when the *simulated* outcome window closes. Do not use SQS delay timers for reward timing.
- **Single-writer model updates:** the bandit's parameters are updated by one Lambda with reserved concurrency = 1 (batched from SQS) to avoid race conditions.

---

## 4. Tech stack (locked)

| Area | Choice | Notes |
|---|---|---|
| Language (backend/ML) | **Python 3.11** | |
| Numerics | **numpy**, **pandas**, **scipy** (offline only), **scikit-learn**, **lightgbm** (quantile regression for journey, optional) | Keep the Lambda decision path **numpy-only** to avoid heavy packaging |
| Contracts | **pydantic v2** | Export JSON Schema → generate TS types for the frontend |
| Optimization | Greedy + Lagrangian (core); **OR-Tools** (advanced, offline/container) | |
| Forecasting | **Chronos-2** via `chronos-forecasting` (zero-shot, quantiles, covariates; CPU ok) vs seasonal-naive baseline | Runs in the runner for CORE; Lambda container only if time permits. **[VERIFY]** API (`Chronos2Pipeline`, `predict_df`) against the current model card |
| Bandit | **Linear Thompson Sampling** (own implementation, ~60 lines) | |
| Policy | **AWS Cedar** via `cedarpy` **[VERIFY]**, or Amazon Verified Permissions as the managed alternative | Numeric checks computed in code, passed to Cedar as integer/boolean attributes |
| LLM | **Amazon Bedrock** via `boto3` `bedrock-runtime` `converse` API | Model ID from env var `BEDROCK_MODEL_ID`; enable model access in your region first **[VERIFY]** |
| Agent | **Strands Agents SDK** (`strands-agents`) **[VERIFY]** | Operator copilot, advanced |
| AWS infra | **SAM** (`template.yaml`): API Gateway HTTP API, Lambda, DynamoDB, S3, SQS FIFO, (EventBridge optional), CloudWatch | |
| Hosting | **Amplify Hosting** (Next.js) | Fallback: static export to S3 + CloudFront |
| Frontend | **Next.js (App Router) + TypeScript + Tailwind CSS + Recharts** | ECharts only if a chart needs it |
| Testing | **pytest**, **hypothesis** (property tests for safety), **vitest** or none for UI | |
| Dev tooling | `uv` or `venv`, `ruff`, `black`, `pre-commit` (optional) | |

**Region:** pick the region where your chosen Bedrock model is enabled and keep everything else there. Mumbai (`ap-south-1`) is closest for India but check model availability first. **[VERIFY]**

**Budget:** set an AWS Budgets alert (e.g. $20 and $50) on day one. Use the free tier and the credits from the hackathon page.

---

## 5. Repository layout

```
gridnudge/
├─ AGENTS.md                      # this file
├─ README.md                      # architecture, results, honest limits, how to run
├─ contracts/                     # decision_record.schema.json, api.openapi.yaml
├─ config/
│  ├─ sim.yaml                    # fleet size, intervals, stations, feeder capacity
│  ├─ behavior_assumed.yaml       # hidden user-response parameters (ALL flagged ASSUMED)
│  ├─ tariffs.yaml                # ToU slots (cite tariff order source)
│  └─ safety.yaml                 # thresholds
├─ data/
│  ├─ raw/  (+ SOURCES.md)        # untouched downloads
│  ├─ processed/                  # parquet
│  └─ ASSUMPTIONS.md              # every assumed/synthetic parameter + how to replace it
├─ gridnudge/                     # core Python package (pure, importable by Lambda + runner)
│  ├─ contracts.py                # pydantic models (DecisionRecord etc.)
│  ├─ state.py                    # StateStore, InMemoryStore, DynamoStore
│  ├─ perception/ journey.py battery.py station.py grid.py flexibility.py
│  ├─ planner.py
│  ├─ persuasion/ features.py lints.py fatigue.py uplift.py
│  ├─ allocator.py
│  ├─ safety/ invariants.py cedar_policies/*.cedar cedar_check.py failsilent.py
│  ├─ language/ templates.py render.py verify.py
│  └─ pipeline.py                 # decide_batch(): orchestrates stages → DecisionRecords
├─ twin/                          # simulator (NOT imported by Lambda)
│  ├─ world.py users.py battery_truth.py stations.py grid.py events.py behavior_hidden.py runner.py
├─ eval/                          # baselines, CRN, metrics, plots, stress tests, calibration
├─ services/                      # Lambda handlers: decide.py outcomes.py reward_update.py explain.py metrics.py
├─ agent/                         # Strands copilot (advanced)
├─ infra/template.yaml            # SAM
├─ dashboard/                     # Next.js app
├─ tests/
└─ docs/ BUILD_LOG.md FUTURE.md DEMO_SCRIPT.md
```

---

## 6. Contracts

### 6.1 DecisionRecord (pydantic skeleton)

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

PlanType = Literal["default", "delay", "relocate", "slow_charge", "top_up_now"]
Frame    = Literal["none", "cost", "green", "battery", "convenience", "reassurance"]
Timing   = Literal["at_plug_in", "plus_30m", "pre_peak"]

class Journey(BaseModel):
    p_arrive_above_reserve: float          # calibrated
    arrival_soc_q10: float
    arrival_soc_q50: float
    arrival_soc_q90: float
    reserve_soc: float = 0.10

class BatteryView(BaseModel):
    stress_score: float                    # 0..1, relative
    soh_delta_range_pct: tuple[float, float]  # simulated, plan vs default, assumption-driven

class StationView(BaseModel):
    eta_wait_min_q50: float
    eta_wait_min_q90: float
    reliability: float                     # ASSUMED in simulation

class GridView(BaseModel):
    stress_q50: float
    stress_q90: float
    green_window_start: Optional[str] = None
    green_window_end: Optional[str] = None

class Plan(BaseModel):
    plan_id: str
    type: PlanType
    start: str                             # ISO time
    kw: float
    where: str                             # "home" | station id
    outcomes: dict                         # cost_inr, journey_conf_lb, grid_value, battery_stress_delta, wait_min

class Safety(BaseModel):
    invariants_ok: bool
    cedar: Literal["ALLOW", "DENY", "ERROR"]
    vetoed: list[str] = []                 # human-readable reasons, e.g. "p3: journey_conf_lb 0.82 < 0.90"

class Persuasion(BaseModel):
    chosen_plan: Optional[str]
    frame: Frame
    timing: Optional[Timing]
    uplift_mean: float
    uplift_p10: float
    propensity: float                      # P(this action | context), logged for OPE
    explored: bool

class Allocation(BaseModel):
    selected: bool
    shadow_price: float
    slot: Optional[str] = None

class Language(BaseModel):
    message: Optional[str] = None
    facts_used: dict = {}
    verified: bool = False
    source: Literal["llm", "template", "none"] = "none"

class Outcome(BaseModel):
    adopted: Optional[bool] = None
    kwh_shifted: Optional[float] = None
    opted_out: Optional[bool] = None
    reward: Optional[float] = None

class DecisionRecord(BaseModel):
    decision_id: str
    run_id: str
    sim_time: str
    user_id: str
    ev: dict
    journey: Optional[Journey] = None
    battery: Optional[BatteryView] = None
    station: Optional[StationView] = None
    grid: Optional[GridView] = None
    plans: list[Plan] = []
    safety: Safety
    persuasion: Persuasion
    allocation: Allocation
    language: Language = Language()
    outcome: Outcome = Outcome()
    fail_silent: bool = False
    error: Optional[str] = None
```

Export JSON Schema (`DecisionRecord.model_json_schema()`) to `contracts/` and generate TypeScript types for the dashboard so frontend and backend never drift.

### 6.2 HTTP API (API Gateway HTTP API)

| Method / path | Purpose |
|---|---|
| `POST /decide` | Body: `{run_id, sim_time, grid_forecast, stations, candidates:[{user_id, ev, trip, context}]}` → returns `DecisionRecord[]` (only selected ones have a message) |
| `POST /outcomes` | Body: `{decision_id, adopted, kwh_shifted, opted_out, realized_value}` → enqueues to SQS FIFO (`MessageGroupId = run_id`) |
| `POST /events` | Inject scenario (`heatwave`, `solar_drop`, `station_outage`, `tariff_change`) or publish forecasts; stored for the runner/dashboard |
| `GET /metrics?run_id=` | Aggregated time series for the dashboard |
| `GET /decision/{id}` | One DecisionRecord |
| `POST /explain` | Narration of a DecisionRecord (LLM, verified) |

### 6.3 DynamoDB tables (on-demand billing)

| Table | Key | Contents |
|---|---|---|
| `UserState` | PK `user_id` | archetype posterior (K floats), fatigue score, per-frame habituation, nudges today, opt-out flag, last nudge time |
| `ModelState` | PK `model_id` | LinTS `A` matrix and `b` vector (serialized float arrays), version, update count |
| `Decisions` | PK `decision_id`, GSI `run_id` + `sim_time` | DecisionRecord JSON (TTL optional) |

S3 layout: `runs/{run_id}/decisions/part-*.jsonl`, `runs/{run_id}/timeline.json` (aggregates for replay), `runs/{run_id}/summary.json`.

---

## 7. Data and configuration

Use the real datasets listed in `GridNudge_Dataset_Master_List.md`. Keep `data/raw/SOURCES.md` (URL, date, license) and `data/ASSUMPTIONS.md` (every assumed number).

**Minimum data tasks:**
1. `grid_series.parquet`: Grid-India hourly demand/solar (normalize to a feeder shape) + Delhi hourly load/weather.
2. `sessions_profile.parquet`: arrival-hour, dwell, kWh distributions from ACN-Data (or the Harvard set if the API is slow).
3. `stations_delhi.parquet`: Ministry of Power station list filtered to Delhi (charger types and kW).
4. `tariffs.yaml`: a 3-slot ToU table (solar-hour low, evening peak high, night mid). Cite the state order you based it on; mark values ASSUMED if not copied from an order.
5. `behavior_assumed.yaml` (below).

**Behavior priors (ASSUMED, informed by a published randomized trial):** financial/cost framing has high uplift; green/"social good" framing has near-zero uplift (a Canadian trial found no detectable effect of a pro-social nudge); effect does **not persist** after the incentive stops. These are Canada/Australia findings, not Indian evidence. State this in the README.

```yaml
# config/behavior_assumed.yaml  (ALL values ASSUMED, sweep them in sensitivity runs)
archetypes:            # mix
  price_sensitive: 0.30
  eco_motivated: 0.15
  convenience: 0.20
  routine_locked: 0.25
  fatigue_prone: 0.10
base_shift_logit:      # P(shift without nudge)
  price_sensitive: -1.2
  eco_motivated: -1.0
  convenience: -1.5
  routine_locked: -3.0
  fatigue_prone: -1.5
frame_effect_logit:    # added when nudged with this frame (cost per Rs 100 saved handled separately)
  price_sensitive: {cost: 1.6, green: 0.05, battery: 0.2, convenience: 0.2, reassurance: 0.1}
  eco_motivated:   {cost: 0.5, green: 0.30, battery: 0.3, convenience: 0.1, reassurance: 0.1}
  convenience:     {cost: 0.4, green: 0.0,  battery: 0.1, convenience: 1.0, reassurance: 0.2}
  routine_locked:  {cost: 0.1, green: 0.0,  battery: 0.0, convenience: 0.1, reassurance: 0.0}
  fatigue_prone:   {cost: 0.8, green: 0.0,  battery: 0.1, convenience: 0.3, reassurance: 0.1}
money_coef_per_100inr: 0.8
delay_penalty_per_hour: {price_sensitive: 0.3, eco_motivated: 0.4, convenience: 0.9, routine_locked: 1.8, fatigue_prone: 0.5}
fatigue_penalty: {price_sensitive: 0.4, eco_motivated: 0.4, convenience: 0.5, routine_locked: 0.6, fatigue_prone: 1.2}
fatigue_decay_per_day: 0.7
repeat_frame_penalty: 0.3
optout_logit: {intercept: -5.0, per_fatigue: 0.9, per_repeat_frame: 0.4}
```

---

## 8. Digital twin spec (`twin/`)

**World:** `World(seed, n_users=2000, step_minutes=15, days=N)`; vectorized over users with numpy arrays.

**User attributes:** archetype, battery_kwh (e.g. 30 to 60 for cars; optionally include 2-wheeler class later), efficiency base Wh/km, home charger kW (3.3/7.4/11), has_home_charging, commute km, depart/arrive time distributions (from session data), weekend trip probability, current SOC, plugged flag, departure deadline, target SOC.

**Default charging behavior:** plug in at arrival, charge at max power until target SOC (this creates the evening peak).

**Stations:** 8 to 12 with `c` connectors and kW; queue dynamics via simple arrival/service simulation; outages from event injector.

**Grid:** `feeder_load(t) = base_load(t) + ev_load(t)`; `base_load` scaled from the Grid-India/Delhi shape; `feeder_capacity` fixed; `stress = feeder_load / capacity`. Solar share curve from Grid-India/Open-Meteo radiation. ToU tariff per slot.

**Events (`events.py`):**
| Event | Effect |
|---|---|
| `heatwave` | base load ×1.18 for 16:00 to 22:00, temperature +4 °C (raises HVAC energy and battery stress) |
| `solar_drop` | solar share ×0.6 for 11:00 to 15:00 |
| `station_outage` | selected stations capacity → 0 for a window |
| `tariff_change` | shift ToU slot boundaries or multiply peak price |

**Hidden behavior model (`behavior_hidden.py`)**, never imported by the learner:
```
logit_shift = base_shift_logit[arch]
            + 1{nudged} * ( frame_effect_logit[arch][frame]
                            + money_coef_per_100inr * savings_inr/100
                            - delay_penalty_per_hour[arch] * delay_hours
                            - fatigue_penalty[arch] * fatigue
                            - repeat_frame_penalty * 1{same frame as last} )
P(adopt) = sigmoid(logit_shift)
P(opt_out) = sigmoid(optout_intercept + per_fatigue*fatigue + per_repeat*repeat) * 1{nudged}
fatigue_{t+1} = decay * fatigue_t + 1{nudged}
```
Without a nudge, users shift spontaneously with `sigmoid(base_shift_logit)`. The simulator **knows the true uplift** `P(adopt|nudge) − P(adopt|none)`, which the evaluation harness uses as an oracle.

**Outcome:** when a plan is adopted, the twin recomputes that user's charging timeline, then at the end of the outcome window emits `{adopted, kwh_shifted_to_green_or_offpeak, savings_inr, battery_stress_delta, opted_out, realized_value}`.

**Truth vs model separation:** the twin's "true" trip energy uses noise the Journey model does not see exactly (traffic and driver factors), so calibration is a real test (in simulation).

**Acceptance:** 2,000 EVs × 7 days runs in under ~60 s on a laptop; evening peak visible in fleet load; reproducible given seed.

---

## 9. Intelligence modules

### 9.1 Journey Confidence (`perception/journey.py`) [CORE]
- Energy per km = `base_wh_km × traffic_factor × driver_factor` + `HVAC_kW × 1000 / avg_speed`, where `HVAC_kW` rises with distance of temperature from comfort range (cap it). **All constants ASSUMED**; calibrate shape on the Vehicle Energy Dataset if time allows.
- Monte Carlo (N ≈ 300 to 500 draws) over traffic, temperature error and driver factor → arrival SOC samples → quantiles `q10/q50/q90` and `p_arrive_above_reserve = mean(arrival_soc ≥ reserve)`.
- **Calibration:** generate a few thousand held-out simulated trips with the twin's *true* energy; fit isotonic regression (or Platt) from predicted `p_arrive` → observed frequency; also compute split-conformal interval widths for arrival SOC. Persist calibrators to `models/`.
- **Output used by safety:** `journey_conf_lb` = calibrated probability for the *plan's resulting SOC trajectory at departure* (e.g. delaying charging lowers SOC at an early departure).
- **Deliverable chart:** reliability diagram ("when we say 90%, how often is it true?") + interval coverage. Required for the demo.

### 9.2 Battery stress (`perception/battery.py`) [CORE: simple; ADVANCED: SoH ranges]
- `stress_score` (0..1, relative) from: hours at high SOC, C-rate above a threshold, temperature above a threshold, depth of discharge.
- ADVANCED: semi-empirical aging: `loss = calendar(T, SOC_avg, t) + cycle(throughput, C-rate, DoD, T)`; sample parameters from literature-style ranges (Monte Carlo) → `soh_delta_range_pct` for plan vs default. Report **relative differences between plans**, never absolute lifespan. Validate shape against NASA/CALCE/Severson data (advanced).

### 9.3 Station and grid intelligence
- **Station wait at ETA** (`perception/station.py`): Erlang-C queue using forecast arrival rate and service rate.
```python
import math
def erlang_c_wq(lam_per_min: float, mu_per_min: float, c: int) -> float:
    a = lam_per_min / mu_per_min
    rho = a / c
    if rho >= 1:
        return float("inf")
    s = sum(a**k / math.factorial(k) for k in range(c))
    top = a**c / math.factorial(c) / (1 - rho)
    p_wait = top / (s + top)
    return p_wait / (c * mu_per_min - lam_per_min)   # mean wait, minutes
```
Feed it *planned* load so nudges that move arrivals change predicted queues.
- **Grid stress / green windows** (`perception/grid.py`): `stress = feeder_load/capacity`; forecast quantiles via **Chronos-2** (ADVANCED) or seasonal-naive (CORE). Green window = hours where forecast renewable share is high and stress is low. **Prove Chronos beats seasonal-naive** on held-out windows (MASE or pinball loss); otherwise keep the baseline.
- **Flexibility envelope** (`perception/flexibility.py`): per plugged EV, `shiftable_kwh = min(e_default_in_peak_window, p_max × hours_available_outside_window_before_deadline)`. Fleet flexibility = `Σ shiftable_i × P(adopt | nudge, x_i)`, with Monte Carlo over adoption draws → `MW ± MW` (**label "Simulation"**).

### 9.4 Planner (`planner.py`) [CORE]
Enumerate plans per EV: `default`, `delay` (to green/off-peak window within the deadline), `relocate` (to the station with lowest predicted wait + cost, ADVANCED), `slow_charge` (battery- and grid-friendly), `top_up_now` (protective, used when journey confidence is at risk). For each, predict outcomes: `cost_inr`, `journey_conf_lb`, `grid_value` (stress-weighted reduction of peak-window draw), `battery_stress_delta`, `wait_min`.
`grid_value(t)` is increasing in forecast grid stress at the time energy is *removed from peak* and in renewable share where it is *added*.

### 9.5 Safety (`safety/`) [CORE]
**Invariants (Python, unit-tested):**
```python
def plan_is_safe(plan, journey, battery, limits) -> tuple[bool, str]:
    if plan.outcomes["journey_conf_lb"] < limits.min_journey_conf:         # default 0.90
        return False, f"{plan.plan_id}: journey_conf_lb {plan.outcomes['journey_conf_lb']:.2f} < {limits.min_journey_conf:.2f}"
    if plan.kw > limits.max_kw_for_vehicle:
        return False, f"{plan.plan_id}: power exceeds vehicle limit"
    if plan.outcomes.get("creates_new_peak", False):
        return False, f"{plan.plan_id}: would exceed feeder capacity in its slot"
    return True, ""
```
**Cedar policy** (integers and booleans only; pass fractional values as basis points):
```cedar
// permit only when every condition holds
permit (
  principal,
  action == Action::"SendNudge",
  resource
) when {
  context.optedOut == false &&
  context.quietHours == false &&
  context.nudgesToday < 3 &&
  context.journeyConfLbBps >= 9000 &&
  context.invariantsOk == true &&
  context.vehicleSupportsPlan == true
};

// belt and braces: hard deny on unsafe journey regardless of other permits
forbid (
  principal,
  action == Action::"SendNudge",
  resource
) when { context.journeyConfLbBps < 9000 };
```
Call shape (verify against the library you choose): request with principal `User::"<id>"`, action `Action::"SendNudge"`, resource `Nudge::"<decision_id>"`, and the context above.
**Fail-silent wrapper:** wrap each stage; on exception, timeout or Cedar `ERROR`, return a record with `fail_silent=True`, `persuasion.frame="none"`, and log the error.

### 9.6 Persuasion: uplift-aware contextual bandit (`persuasion/`) [CORE]
**Action:** `none` ∪ { (plan ∈ safe plans) × (frame ∈ cost/green/battery/convenience/reassurance) × (timing ∈ at_plug_in/plus_30m/pre_peak) }. The plan comes from the planner; only safe plans exist.

**Features φ(x,a):** `[1, onehot(frame incl. none), onehot(timing), onehot(plan), x ⊗ onehot(frame)]` where `x` ≈ 12 context features: SOC, hours to departure, hour-of-day (sin/cos), grid stress, savings_inr (scaled), delay_hours, journey_conf, fatigue, nudges_today, archetype posterior (K=5 probabilities, 4 free), recent-ignore rate. About 80 to 90 dimensions.

**LinTS:**
```python
import numpy as np

class LinTS:
    def __init__(self, d, lam=1.0, v=0.5, gamma=0.999, seed=0):
        self.d, self.lam, self.v, self.gamma = d, lam, v, gamma
        self.A = lam * np.eye(d)
        self.b = np.zeros(d)
        self.rng = np.random.default_rng(seed)

    def sample_theta(self, m=64):
        Ainv = np.linalg.inv(self.A)
        mu = Ainv @ self.b
        L = np.linalg.cholesky(self.v**2 * Ainv + 1e-9 * np.eye(self.d))
        return mu + (L @ self.rng.standard_normal((self.d, m))).T      # (m, d)

    def update(self, Phi, r):                  # Phi: (n, d), r: (n,)
        I = np.eye(self.d)
        self.A = self.gamma * (self.A - self.lam * I) + self.lam * I + Phi.T @ Phi
        self.b = self.gamma * self.b + Phi.T @ r
```
**Decision per user:** draw `m` theta samples; `scores = thetas @ Phi_actions.T` (shape `m × n_actions`).
- **Choice:** the action with the highest score under one sampled theta (Thompson). Estimate `propensity` as the selection frequency across the `m` samples, then mix with exploration: `π = (1-ε)·π_TS + ε/|A|` with ε ≈ 0.05 to 0.10 (includes `none`).
- **Uplift:** `u_m = scores[m, a] − scores[m, none]` (paired draws) → report mean and p10.
- **Global holdout:** ~5% of users never receive nudges (for clean uplift and honest evaluation).
- **Log** `(context features, action, propensity, reward)` for every decision.

**Reward (computed from the twin's outcome, same metric for `none` and nudges):**
```
r = w_g * grid_value * kwh_shifted
  + w_u * savings_inr
  + w_b * (−battery_stress_delta)
  − w_w * extra_wait_min
  − w_f * fatigue_cost
  − w_o * opted_out
```
Reward is the *realized value* of the user's behavior, so `none` can be nonzero (spontaneous shifting). Uplift = difference. Start weights: `w_g=1.0, w_u=0.02/INR, w_b=0.5, w_w=0.02/min, w_f=0.3, w_o=5.0` (tune once, then freeze before final benchmark).

**Archetype posterior:** per user, a K-vector updated by Bayes rule from observed responses using the *learner's own* (not the hidden) likelihood model, e.g. per-archetype adoption probability tables learned from data (start from a mild prior).

**Fatigue state:** exponentially decayed nudge counter, ignore rate, last-frame repeat flag. It is both a context feature and a reward penalty.

### 9.7 Fleet allocator (`allocator.py`) [CORE greedy; ADVANCED OR-Tools]
Each interval:
1. Candidates = eligible EVs with a non-`none` best action.
2. Rank by `uplift_p10_or_mean × grid_value`.
3. Select greedily subject to: **attention budget** (≈ 5 to 10% of plugged-in EVs per interval; treat the marginal value of the last selected candidate as the shadow price shown in the UI), per-user daily cap, **feeder/station capacity per slot** (if the chosen slot would exceed capacity, push to the next slot or skip).
4. **Anti-herding:** distribute selected users' `timing`/start slots across 15-minute offsets (round-robin or randomized within the allowed window) so the shifted load does not land in one interval.
ADVANCED: solve the same problem with OR-Tools (assignment/CP-SAT) and report the greedy-vs-optimal gap.

### 9.8 Language layer (`language/`) [CORE: templates; ADVANCED: Bedrock]
- **Templates first** (`templates.py`): one short template per frame, filled with verified numbers. This is the permanent fallback.
- **Bedrock rendering:** input is only the `facts` dict (plan, frame, numbers, times); output is one or two short sentences in a requested language/tone.
```python
import boto3, os, json
brt = boto3.client("bedrock-runtime")
def render(facts: dict, tone: str, lang: str) -> str:
    prompt = (f"Write one friendly sentence in {lang}, tone: {tone}. "
              f"Use ONLY these facts, do not add numbers or claims: {json.dumps(facts)}")
    r = brt.converse(modelId=os.environ["BEDROCK_MODEL_ID"],
                     messages=[{"role": "user", "content": [{"text": prompt}]}],
                     inferenceConfig={"maxTokens": 120, "temperature": 0.2})
    return r["output"]["message"]["content"][0]["text"].strip()
```
- **Numeric verifier (mandatory with any LLM output):**
```python
import re
NUM = re.compile(r"\d+(?:\.\d+)?")
FORBIDDEN = re.compile(r"guarantee|will last|safe for sure|100%|risk[- ]free", re.I)

def verify(text: str, facts: dict) -> bool:
    allowed = {n for v in facts.values() for n in NUM.findall(str(v))}
    found = set(NUM.findall(text.replace(",", "")))
    return found <= allowed and not FORBIDDEN.search(text)
```
If `verify` fails → use the template and set `language.source="template"`. Cache by `(plan, frame, tone, lang, bucketed numbers)`. Express times as numbers present in `facts` (e.g. `"hour": "22", "minute": "30"`).
- **Explanation** (`/explain`): the same pipeline narrates a DecisionRecord ("why this decision / why blocked"). Never add facts not in the record.

### 9.9 Operator copilot (Strands) [ADVANCED]
```python
from strands import Agent, tool   # [VERIFY] package and API

@tool
def get_decision(decision_id: str) -> dict: ...
@tool
def explain_veto(decision_id: str) -> str: ...
@tool
def compare_policies(policy_a: str, policy_b: str) -> dict: ...   # reads precomputed OPE/benchmark results
@tool
def inject_scenario(text: str) -> dict: ...                       # NL → structured event (validated against a schema)

agent = Agent(tools=[get_decision, explain_veto, compare_policies, inject_scenario],
              system_prompt="Answer only from tool outputs. Cite decision_ids. Never invent numbers.")
```
`inject_scenario` must validate the model's output against the event schema before the twin sees it.

---

## 10. Evaluation harness (`eval/`) [CORE, this is your proof]

**Policies (same fleet, same seeds, same events):**
- **B0** no nudges
- **B1** broadcast: everyone eligible gets a cost nudge at peak start
- **B2** rule-based: SOC < threshold and peak approaching → cost nudge
- **B3** non-personalized bandit (context-free)
- **B4** GridNudge (full)

**Common random numbers:** derive per-user, per-step random streams from `(seed, user_id, step)` so every policy sees identical randomness.

**Metrics (mean ± CI over ≥ 5 to 10 seeds):**
| Metric | Definition |
|---|---|
| Peak load reduction % | `(peak_B0_or_B1 − peak_B4)/peak_ref` over 18:00 to 22:00 |
| kWh shifted | energy moved out of the peak window |
| Nudges per user per day | |
| Opt-out rate | |
| Uplift per nudge | kWh caused per nudge (oracle from twin, plus estimator) |
| Safety | **stranded trips attributable to nudges = 0**; count of vetoes |
| Regret | vs oracle policy (twin knows true uplift) |
| Uplift estimation error | estimated vs true uplift; Qini/AUUC |
| Calibration | reliability diagram, interval coverage |
| Cost saved | mean INR per participating user |

**Stress tests (ADVANCED but high value):**
1. **Misspecification:** learner trained under behavior config A, evaluated under perturbed config B (archetype mix, fatigue decay, price sensitivity). Report degradation honestly.
2. **Non-stationarity:** mid-run tariff change or new archetype; show the discounted posterior recovers.
3. **Sensitivity sweep** over key assumed parameters.
4. **Real-data check (ADVANCED):** fit response curves on the openICPSR randomized-trial replication data and compare to your assumed priors.

**CLI:**
```
python -m eval.run --seeds 10 --users 2000 --days 7 --scenario heatwave --policies B0 B1 B2 B3 B4
# → results/summary.csv, results/timeline.json (for replay), results/plots/*.png
```

---

## 11. AWS infrastructure (`infra/template.yaml`, SAM skeleton)

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Globals:
  Function:
    Runtime: python3.11
    Timeout: 30
    MemorySize: 1024
    Environment:
      Variables:
        USER_TABLE: !Ref UserState
        MODEL_TABLE: !Ref ModelState
        DECISION_TABLE: !Ref Decisions
        LOG_BUCKET: !Ref LogBucket
        REWARD_QUEUE_URL: !Ref RewardQueue
        BEDROCK_MODEL_ID: ""          # set after enabling model access
Resources:
  UserState:
    Type: AWS::DynamoDB::Table
    Properties:
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions: [{AttributeName: user_id, AttributeType: S}]
      KeySchema: [{AttributeName: user_id, KeyType: HASH}]
  ModelState:
    Type: AWS::DynamoDB::Table
    Properties:
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions: [{AttributeName: model_id, AttributeType: S}]
      KeySchema: [{AttributeName: model_id, KeyType: HASH}]
  Decisions:
    Type: AWS::DynamoDB::Table
    Properties:
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - {AttributeName: decision_id, AttributeType: S}
        - {AttributeName: run_id, AttributeType: S}
        - {AttributeName: sim_time, AttributeType: S}
      KeySchema: [{AttributeName: decision_id, KeyType: HASH}]
      GlobalSecondaryIndexes:
        - IndexName: by_run
          KeySchema: [{AttributeName: run_id, KeyType: HASH}, {AttributeName: sim_time, KeyType: RANGE}]
          Projection: {ProjectionType: ALL}
  LogBucket:
    Type: AWS::S3::Bucket
  RewardQueue:
    Type: AWS::SQS::Queue
    Properties:
      FifoQueue: true
      ContentBasedDeduplication: true
  Api:
    Type: AWS::Serverless::HttpApi
  DecideFn:
    Type: AWS::Serverless::Function
    Properties:
      Handler: services.decide.handler
      CodeUri: .
      Events:
        Decide: {Type: HttpApi, Properties: {ApiId: !Ref Api, Path: /decide, Method: post}}
      Policies:
        - DynamoDBCrudPolicy: {TableName: !Ref UserState}
        - DynamoDBReadPolicy: {TableName: !Ref ModelState}
        - DynamoDBCrudPolicy: {TableName: !Ref Decisions}
        - S3WritePolicy: {BucketName: !Ref LogBucket}
        - Statement: [{Effect: Allow, Action: [bedrock:InvokeModel, bedrock:Converse], Resource: '*'}]
  OutcomesFn:
    Type: AWS::Serverless::Function
    Properties:
      Handler: services.outcomes.handler
      CodeUri: .
      Events:
        Outcomes: {Type: HttpApi, Properties: {ApiId: !Ref Api, Path: /outcomes, Method: post}}
      Policies: [SQSSendMessagePolicy: {QueueName: !GetAtt RewardQueue.QueueName}]
  RewardUpdateFn:
    Type: AWS::Serverless::Function
    Properties:
      Handler: services.reward_update.handler
      CodeUri: .
      ReservedConcurrentExecutions: 1          # single writer for model updates
      Events:
        Q: {Type: SQS, Properties: {Queue: !GetAtt RewardQueue.Arn, BatchSize: 10}}
      Policies:
        - DynamoDBCrudPolicy: {TableName: !Ref ModelState}
        - DynamoDBCrudPolicy: {TableName: !Ref UserState}
        - DynamoDBCrudPolicy: {TableName: !Ref Decisions}
        - S3WritePolicy: {BucketName: !Ref LogBucket}
  # Add: MetricsFn (GET /metrics), ExplainFn (POST /explain), DecisionGetFn (GET /decision/{id})
Outputs:
  ApiUrl: {Value: !Sub 'https://${Api}.execute-api.${AWS::Region}.amazonaws.com'}
```
Notes: this is a **skeleton**; adapt policies to least privilege and fix names as you go. `numpy` and `pydantic` must be packaged (use a Lambda layer or container image). Keep the decide path numpy-only. Send to FIFO with `MessageGroupId=run_id`. CloudWatch: emit custom metrics (`veto_count`, `fail_silent_count`, `nudges_sent`) via structured logs.

**Local-first rule:** every Lambda handler is a thin wrapper around `gridnudge.pipeline` with the store injected, so the same code runs against `InMemoryStore` in tests and `DynamoStore` in AWS.

---

## 12. Tests (must exist)

| Test | Asserts |
|---|---|
| `test_safety_veto` (hypothesis) | no plan with `journey_conf_lb < 0.90` is ever returned as chosen |
| `test_failsilent` | forcing exceptions in perception/Cedar/verifier yields `fail_silent=True`, no message |
| `test_verifier` | text with a number not in `facts` or a forbidden phrase is rejected |
| `test_crn` | same seed → identical baseline trajectories across policies |
| `test_bandit_toy` | on a synthetic known-uplift problem, regret decreases and `none` is chosen when uplift ≤ 0 |
| `test_allocator` | respects budget, per-user cap, capacity, and staggers slots |
| `test_no_new_peak` | fleet load after allocation does not exceed capacity in any slot (when feasible) |
| `test_calibration` | reliability error below a set threshold on held-out simulated trips |
| `test_contracts` | DecisionRecord round-trips through JSON; schema matches TS types |

---

## 13. Build plan with kill rules

Assume today is **Thu Oct 8** and the event runs through **Sun Oct 11** (build day at DTU on Oct 10 is optional). Time-box ruthlessly.

| Phase | Goal | Done when |
|---|---|---|
| **P0 (1 h)** Setup | repo, venv, SAM CLI, AWS profile + budget alert, contracts, `AGENTS.md` in place | `pytest` runs; `DecisionRecord` schema exported |
| **P1 (Day 1)** Twin + baselines | twin runs, B0/B1/B2 produce fleet curves, evening peak visible | first comparison chart (B0 vs B1) |
| **P2 (Day 1)** Brain, local | journey+calibration, planner, safety, LinTS, greedy allocator, B3/B4, `InMemoryStore` | **local closed loop works**: decide → outcome → update → better decisions; B4 beats B1 on peak and nudges/user |
| **P3 (Day 2 AM)** AWS path | SAM deploy: `/decide`, `/outcomes`, SQS→reward_update, DynamoDB, S3 logs | runner talks to AWS; Decisions table fills; model updates persist |
| **P4 (Day 2, parallel)** Dashboard | live curves, event button, decision card, metrics, replay mode | works against mock API first, then real |
| **P5 (Day 2 PM)** Cedar + eval | Cedar in the path, eval harness with 5+ seeds, calibration plot | `results/summary.csv` + plots |
| **P6 (Day 3)** Advanced, in order | Chronos → station/relocate → Bedrock+verifier → Strands → flexibility → OPE/stress tests → (OR-Tools, Test Drive) | each item gated by "does CORE still run?" |
| **FREEZE (Oct 10 night)** | no new features | |
| **P7 (Oct 11 AM)** | final multi-seed run, README, assumptions register, video, submission | submitted before the deadline |

**Kill rules:**
- End of Day 1: if the local closed loop isn't running, drop **all** Advanced items.
- Mid Day 2: if the AWS path isn't responding, deploy only `decide` + DynamoDB + S3 and process rewards **synchronously** (drop SQS/EventBridge); mention SQS in the architecture as the scale path only if truthful.
- If Bedrock access/latency blocks you: template-only language layer, and say so.
- If Cedar library packaging fights you: evaluate policies via Amazon Verified Permissions, or keep Cedar policies in the repo with a Python evaluator test, and say exactly what runs where.
- **Never cut:** baselines, the safety veto, the calibration plot, the replay mode.

**Suggested split:** Vishal: twin core, journey/calibration, bandit/uplift, allocator, AWS path, Cedar, eval. Sneha: dashboard, decision-card UX, event injection UX, Bedrock/Strands layer, README, video. **Agree the DecisionRecord schema in P0**, then both build in parallel (frontend against a mock API). In Antigravity, run parallel agents on independent modules (e.g. twin / dashboard / infra), and review each agent's plan before it runs.

---

## 14. Prompts to paste into Antigravity (one per phase)

**P0:** "Read AGENTS.md fully. Create the repo layout in §5, `pyproject.toml`, pytest config, and `gridnudge/contracts.py` implementing §6.1. Export JSON Schema to `contracts/` and generate TypeScript types into `dashboard/src/types`. Add `docs/BUILD_LOG.md`. Don't touch AWS yet."

**P1:** "Implement `twin/` per §8 with a seeded `numpy` Generator and common-random-number streams. Load processed data if present, otherwise use documented synthetic fallbacks. Implement baselines B0, B1, B2 in `eval/` and a script that plots fleet load for each under a `heatwave` event. Add tests for reproducibility. Report the peak load numbers you observed."

**P2:** "Implement `perception/journey.py` (§9.1) with Monte Carlo and isotonic calibration trained on twin-simulated trips; `planner.py` (§9.4); `safety/invariants.py` and `failsilent.py` (§9.5); `persuasion/` with LinTS (§9.6) incl. propensity, uplift, holdout; `allocator.py` greedy (§9.7); and `pipeline.decide_batch` using `InMemoryStore`. Wire B3 and B4 into `eval/`. Add the tests in §12. Show that regret decreases and that `none` is chosen for low-uplift users."

**P3:** "Create `infra/template.yaml` from §11, `services/*.py` handlers as thin wrappers over `gridnudge.pipeline` with a `DynamoStore`, and a runner client that posts batches to `/decide` and outcomes to `/outcomes`. Use a named AWS profile. **Do not run `sam deploy` or any AWS command without asking me first.**"

**P4:** "Build `dashboard/` (Next.js App Router, TypeScript, Tailwind, Recharts) per §15 against a mock API serving fixtures from `results/timeline.json`. Components: FleetLoadChart, EventInjector, NudgeBudgetGauge, DecisionCard with safety-veto highlight, ConfidenceRings, CalibrationPlot, MetricsTable with CI. Add replay mode that reads a bundled `replay.json`."

**P5:** "Integrate Cedar for the policies in §9.5 (verify the Python library or use Verified Permissions), add the policy tests, and run `python -m eval.run --seeds 5` producing `results/summary.csv` and plots. Do not tune on the final seeds."

**P6 (per item):** "Implement ADVANCED item <N> from §2.5 only. Keep CORE tests green. If it cannot be done within 90 minutes, stop and document the blocker in BUILD_LOG.md."

**P7:** "Generate README per §16 using only numbers from `results/summary.csv`. List every assumption in `data/ASSUMPTIONS.md`. Do not add any claim not backed by a logged run."

---

## 15. Dashboard spec (`dashboard/`)

**Design:** dark theme, high-contrast, one accent per concept (grid = amber, GridNudge = green, baseline = red/grey, safety = blue). Every chart is labeled **"Simulation"**. Minimal text, big numbers.

**Pages / panels:**
1. **`/live` (hero):** fleet load chart with two lines (broadcast baseline vs GridNudge), shaded peak window, grid stress strip, solar curve; **Event Injector** buttons (Heatwave, Solar drop, Station outage, Tariff change); counters: nudges per user, attention budget used (with shadow price), vetoes so far, peak reduction %.
2. **`/decision/[id]`:** stepper card: Perception (confidence rings) → Plans (table with outcomes) → **Safety (veto reasons highlighted, Cedar ALLOW/DENY)** → Persuasion (frame, uplift mean/p10, propensity) → Allocation (slot) → Message (source: llm/template, verified ✓). "Explain" button calls `/explain`.
3. **`/evaluation`:** baselines table with CI whiskers, regret curve, uplift-estimation error / Qini, calibration reliability diagram, misspecification result.
4. **`/flexibility`:** forecast band for next peak ("X MW ± Y MW, simulation"), physical envelope vs adoption-weighted.
5. **`/testdrive` (optional):** commute/charging-access form → Ownership Confidence with reasons, including an honest "not suitable" case.
6. **Copilot drawer (optional):** chat with the Strands agent, answers cite decision IDs.

**Data:** poll `GET /metrics` every 1 to 2 s in live mode; **replay mode** loads a bundled `public/replay/timeline.json` (default for the public URL and for recording the video; judges only see the video). Types generated from the JSON Schema.

---

## 16. README, submission and video

**README structure:** problem → solution (one diagram) → what's real vs simulated (table) → architecture + AWS map → results table (from `summary.csv`, with CIs) → safety and calibration evidence → assumptions register link → honest limitations → how to run → future work.

**Real vs simulated table (be explicit):** *Real:* architecture, safety logic, learning loop, AWS deployment, public datasets used for grounding (list them). *Simulated/assumed:* user response behavior, station reliability, traffic noise, feeder capacity, battery aging parameters, tariff slots unless copied from an order.

**3-minute video** (see `docs/DEMO_SCRIPT.md`):
| Time | Beat |
|---|---|
| 0:00 to 0:20 | Problem: evening peak, notification spam, risk of stranding users |
| 0:20 to 0:45 | Idea: "Plan → Persuade → Learn", ML decides, LLM only phrases |
| 0:45 to 1:25 | Twin running; click **Heatwave**; baseline spikes |
| 1:25 to 2:00 | GridNudge flattens the peak; few staggered nudges; silence for low-uplift users |
| 2:00 to 2:25 | **Safety veto moment** on the decision card (Cedar DENY with numbers) |
| 2:25 to 2:45 | Confidence rings + calibration plot + Flexibility Forecast (labeled simulation) |
| 2:45 to 3:00 | AWS map, results with CIs, honest limits, future work |

**Allowed phrases:** "in simulation", "under our assumptions", "calibrated on held-out simulated trips", "relative difference between plans".
**Forbidden phrases:** "guaranteed", "your battery will last", "saves X% in the real world", "proven on real users".

---

## 17. Verify-before-use checklist (agents should confirm these first)

- [ ] `chronos-forecasting` API (`Chronos2Pipeline`, `predict_df`) and CPU runtime on your machine
- [ ] `cedarpy` (or Verified Permissions) request/response shape; Cedar policy syntax
- [ ] `strands-agents` package name and `@tool` / `Agent` usage
- [ ] Bedrock model access enabled in your region; `converse` works; `BEDROCK_MODEL_ID` set
- [ ] ACN-Data API token; Dataverse/Mendeley/IEEE DataPort access and licenses
- [ ] Lambda packaging approach for numpy (layer vs container)
- [ ] Amplify build for Next.js (fallback: static export to S3 + CloudFront)
- [ ] Hackathon submission deadline and required fields on the portal (the registration page text under your team card was cut off in the screenshot; read it, it may be a team-lock rule)
