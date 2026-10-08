# GridNudge: Master Plan (Idea → Modules → Ownership → Git → Schedule)

**Team VibeSync:** Vishal (backend / AI / AWS, ~80%) and Sneha (frontend / data / docs / video, ~20%)
**Event:** Environmental Hacks (WeMakeDevs x AWS), Oct 8 to 11, 2026 | **Track:** Waste & Energy → EV Nudges
**Deliverables:** working system deployed on AWS + 3-minute demo video (judges don't see a live demo). *Confirm the exact submission deadline and rules on the portal; the text under your team card in the screenshot was cut off.*

> Companion files (keep them in `docs/engineering/`): `01_V2_CRITIQUE.md`, `02_ANTIGRAVITY_GUIDANCE.md` (code skeletons for LinTS, Cedar, SAM, verifier), `03_DATASETS.md`. This file is the **human plan**: what we're building, who builds what, in what order, and how we use git without stepping on each other.

---

## 1. The project at a glance

### 1.1 One-liner
**GridNudge is a safety-gated, uplift-aware EV charging decision system.** Physics-based models and forecasts decide the *safest beneficial charging plan*; a causal contextual bandit decides *whether, to whom, and how* to persuade within a limited attention budget; everything is learned and audited in an EV-energy digital twin.

### 1.2 Problem
- Evening EV charging stacks on the grid's evening peak, while midday renewable energy goes under-used.
- Generic notifications cause alert fatigue and mostly reach people who would have shifted anyway.
- Naive "charge later" advice can leave someone with too little battery for tomorrow's trip. That destroys trust, so safety has to be built in, not bolted on.

### 1.3 Solution (four sentences)
1. A **digital twin** simulates EV users, batteries, trips, stations with queues, grid load, solar, tariffs and injected events.
2. **Perception** produces calibrated quantities: Journey Confidence, battery stress, station wait at arrival time, grid stress and green windows.
3. A **planner** proposes safe charging plans; a **bandit with a first-class "none" action** learns who actually changes behavior (uplift) and which framing works; a **fleet allocator** spends a limited nudge budget and staggers timing to avoid a rebound peak.
4. A **safety gate** (Cedar + code invariants) and an **LLM language layer** (Bedrock with a numeric verifier) deliver the nudge; the user's response becomes a causal reward that updates the policy.

### 1.3b The closed loop (what must run end to end)
```
Twin state → Perception → Planner (safe plans) → Bandit (uplift, none arm) → Allocator (budget, stagger)
→ Safety gate → Language → Nudge → Simulated response → Causal reward → Policy update → better decisions
```

### 1.4 The four moments judges must remember
1. **Safety veto, live:** a cost-saving nudge is blocked because tomorrow's Journey Confidence dropped below 90%; Cedar verdict and numbers shown.
2. **Learned silence:** the system stays quiet for users who would shift anyway; nudges per user stay low.
3. **Bending the curve:** inject "Heatwave" → broadcast baseline spikes, GridNudge flattens the evening peak.
4. **Calibrated confidence + Flexibility Forecast:** "Journey Confidence 94%" backed by a reliability plot, and "X MW ± Y MW shiftable (simulation)".

### 1.5 What is real vs simulated (say this plainly in the README)
- **Real:** architecture, safety logic, learning loop, AWS deployment, and public datasets used to ground the twin (charging sessions, India grid/solar, Delhi load + weather, station locations, battery cell data, tariff orders).
- **Simulated / assumed:** user response behavior (priors informed by published randomized trials from Canada/Australia, *not* Indian data), station reliability, traffic noise, feeder capacity, battery aging parameters, tariff slots unless copied from an order.

### 1.6 Scope tiers
- **CORE (must work):** twin + events; Journey Confidence with calibration; planner + safety veto; LinTS bandit with `none`, fatigue, propensity, uplift; greedy allocator; Python invariants + Cedar + fail-silent; baselines + eval harness; AWS decision path (API Gateway, Lambda, DynamoDB, S3, SQS reward loop); dashboard; README + assumptions register; video.
- **ADVANCED (only after CORE runs, in this order):** Chronos grid forecast vs seasonal-naive → station queue forecast + `relocate` plan → Bedrock rendering + verifier → Strands copilot → Flexibility Forecast → doubly-robust OPE + misspecification stress test → OR-Tools allocator → Digital Test Drive.
- **FUTURE (slide only):** deep/offline RL, causal forests, GNN, federated learning, V2G, real OCPP integration, fleet-validated battery models.
- **Not building:** LSTM/TFT training, battery XGBoost, multi-agent RL, Kinesis, always-on SageMaker endpoints, a mobile app.

---

## 2. Architecture

```
          DIGITAL TWIN (runner: local machine or small EC2/Fargate task)
  users · batteries · trips · stations+queues · grid+solar · tariffs · events
       │ every 15 simulated minutes: batch of eligible EVs + grid forecast
       ▼
 ┌──────────────────────── AWS DECISION PATH ─────────────────────────┐
 │ API Gateway ─► Lambda decide_batch                                  │
 │  1 perception   journey · battery stress · station wait · grid      │
 │  2 planner      enumerate plans → predict outcomes                  │
 │  3 SAFETY #1    invariants + Cedar → unsafe plans removed           │
 │  4 persuasion   LinTS over {none} ∪ plan×frame×timing → uplift     │
 │  5 allocator    budget (shadow price) + stagger + capacity          │
 │  6 SAFETY #2    final verify; any error ⇒ fail-silent               │
 │  7 language     templates / Bedrock + numeric verifier              │
 │  DynamoDB: UserState · ModelState · Decisions      S3: logs         │
 └──────────────┬──────────────────────────────────────────────────────┘
                ▼
     nudges → simulator applies HIDDEN behavior model → outcomes
                ▼
     POST /outcomes → SQS FIFO → Lambda reward_update (single writer)
                ▼
     causal reward → posterior update → logs → evaluation / OPE
                ▼
 Dashboard (Next.js, Amplify) ◄─ GET /metrics, /decision/{id}, bundled replay.json
```

**Design decisions that must not change:**
- **Plan → Persuade → Learn:** the planner decides *what is best and safe*; the bandit decides *whether and how to persuade*.
- **Safety acts twice** (before the bandit and on the final output). The bandit never sees an unsafe plan. **Any failure ⇒ no nudge.**
- **One contract:** every stage reads/writes the `DecisionRecord`. Backend and frontend share generated types.
- **Pure core package** (`gridnudge/`) used by both Lambda and the local runner; state behind a `StateStore` interface (`InMemoryStore` for dev/tests, `DynamoStore` on AWS). Everything is built and tested locally first.
- **Batch decisions** per interval, not one Lambda per EV. **Single-writer** model updates (reserved concurrency = 1).
- **Simulated time ≠ wall clock:** outcome events come from the twin at simulated window close, not from SQS delay timers.

---

## 3. Team structure and workload split (~80 / 20)

Hour estimates are **agent-assisted** (Antigravity writes most code; hours include prompting, reviewing, running, fixing). They are planning numbers, not promises.

### 3.1 Module ownership table

| ID | Module | Owner | Tier | Est. h | Branch prefix |
|---|---|---|---|---|---|
| M0 | Repo, contracts, CI, fixtures (unblocks Sneha) | **V** | CORE | 3.5 | `v/m0-*` |
| M1 | Data scripts + processed datasets + tariffs.yaml | **S** | CORE | 3 | `s/m1-*` |
| M2 | Digital twin + events + hidden behavior | **V** | CORE | 8 | `v/m2-*` |
| M3a | Journey Confidence + calibration | **V** | CORE | 5 | `v/m3-*` |
| M3b | Battery stress score | **V** | CORE | 2 | `v/m3-*` |
| M3c | Station wait (Erlang-C) | **V** | CORE | 2 | `v/m3-*` |
| M3d | Grid forecast (seasonal-naive core; Chronos adv) | **V** | CORE/ADV | 3 | `v/m3-*` |
| M3e | Flexibility forecast | **V** | ADV | 2 | `v/m3-*` |
| M4 | Planner | **V** | CORE | 3 | `v/m4-*` |
| M5 | Safety: invariants + Cedar + fail-silent | **V** | CORE | 4 | `v/m5-*` |
| M6 | Persuasion: LinTS, fatigue, uplift, propensity | **V** | CORE | 6 | `v/m6-*` |
| M7 | Allocator (greedy; OR-Tools adv) | **V** | CORE | 3 | `v/m7-*` |
| M8a | Message templates (per frame, EN + one Indian language) | **S** | CORE | 1 | `s/m8-*` |
| M8b | Bedrock rendering + numeric verifier | **V** | ADV | 3 | `v/m8-*` |
| M8c | Strands operator copilot | **V** | ADV | 2 | `v/m8-*` |
| M9 | Pipeline orchestration + StateStore | **V** | CORE | 4 | `v/m9-*` |
| M10 | AWS infra (SAM) + Lambda handlers + deploy | **V** | CORE | 8 | `v/m10-*` |
| M11 | Evaluation harness, baselines, CRN, plots, stress tests | **V** | CORE/ADV | 7 + 4 | `v/m11-*` |
| M12 | Dashboard (Next.js): live, decision card, evaluation | **S** | CORE | 8 | `s/m12-*` |
| M12b | Dashboard extras: flexibility page, copilot drawer | **S** | ADV | 3 | `s/m12-*` |
| M13 | README, assumptions register, demo script, video | **S** | CORE | 3 | `s/m13-*` |
| M14 | Digital Test Drive: engine (V) + form UI (S) | V/S | ADV | 3 / 2 | `v/m14-*`, `s/m14-*` |

**Totals:** Vishal ≈ 56 h CORE + 19 h ADV. Sneha ≈ 15 h CORE + 5 h ADV. **Overall ≈ 79 / 21.**

### 3.2 Honest capacity warning
Vishal's CORE load (~56 h) in about 3.5 days is only realistic with heavy agent parallelism (run independent modules in parallel agents) and strict priority order. If you're behind at any checkpoint, use the **kill rules** in §9. Do not start ADVANCED items until the local closed loop runs.

### 3.3 How Sneha helps Vishal without touching his code (non-code support tasks)
- Run `python -m eval.run ...` and collect plots/CSVs into a shared folder (read-only use of Vishal's code).
- Proofread dashboard text, chart labels and README claims against `results/summary.csv`.
- Test the deployed API with the Postman/curl collection Vishal provides; file issues with request/response attached.
- Keep `docs/BUILD_LOG.md` readable (summarize what Vishal logged), draft the video script.

### 3.4 What Sneha must never do
- Edit files in Vishal's paths (§6.1), even to "quickly fix" something. Open an issue instead (request protocol in §6.7).
- Change `contracts/` without a `contract/*` PR approved by both.

---

## 4. Module-by-module implementation guide

Format: **Goal → Interface → Steps → Key details → Acceptance → Tests → Depends on.**
Long code skeletons (LinTS, Cedar policy, SAM template, verifier) live in `02_ANTIGRAVITY_GUIDANCE.md`; copy from there.

---

### M0: Repo, contracts, CI, fixtures (Vishal, ~3.5 h) **Sneha's unblocker, do this first**
**Goal:** repo scaffold + the one data contract + sample data so Sneha can build the dashboard immediately.
**Steps:**
1. Create the repo layout (§5), `pyproject.toml`, pytest/ruff config, `.gitignore`, `CODEOWNERS`, `scripts/check_ownership.py`, `.githooks/pre-push`, GitHub Action (§6).
2. Implement `gridnudge/contracts.py` (`DecisionRecord` and sub-models; see guidance §6.1).
3. Export `contracts/decision_record.schema.json`; generate TypeScript types to `contracts/ts/decision-record.d.ts`.
4. Write `eval/make_fixtures.py` that produces **hand-authored but schema-valid** fixtures in `fixtures/`: `decisions.sample.json` (include **one veto case**, **one silence case**, **one normal nudge**), `metrics.timeline.json` (two load curves: baseline vs GridNudge, with a heatwave peak), `evaluation.summary.json` (baselines table with CI), `calibration.json`, `flexibility.json`.
5. Tag `contracts-v1.0` and announce the freeze.
**Acceptance:** `pytest` passes; schema + TS types exist; fixtures validate against the schema; Sneha can `git pull dev` and start.
**Rule:** after `contracts-v1.0`, any change goes through a `contract/*` PR (§6.5).

---

### M1: Data scripts and processed datasets (Sneha, ~3 h)
**Goal:** reproducible download/prep of real datasets, with fallbacks, into agreed schemas.
**Interface (files Vishal's twin reads from `data/processed/`):**
| File | Columns |
|---|---|
| `grid_series.parquet` | `ts` (hourly), `demand_norm`, `solar_norm`, `wind_norm` (each normalized 0..1 or to peak) |
| `weather_delhi.parquet` | `ts`, `temp_c`, `shortwave_radiation` |
| `sessions_profile.parquet` | `arrival_hour`, `dwell_hours`, `kwh` (+ optional `user_id`) |
| `stations_delhi.parquet` | `station_id`, `lat`, `lon`, `charger_type`, `kw`, `connectors` |
| `config/tariffs.yaml` | three ToU slots: solar-hour low, evening peak, night; Rs/kWh; cite source order |
**Steps:** (1) Open-Meteo API for Delhi weather; (2) Grid-India hourly series (Mendeley) and Delhi load (IEEE DataPort) → normalize; (3) ACN-Data via `acnportal` (needs a free token) or the Harvard Dataverse CSV → session distributions; (4) Ministry of Power station list (Dataful) filtered to Delhi; (5) a tariff order (state regulator) → `tariffs.yaml`; (6) `data/scripts/validate.py` checks schemas.
**Fallback (important):** each script has `--synthetic` that writes plausible data and appends a line to `data/ASSUMPTIONS.md`. **Hard time cap: 3 hours.** Don't let data hunting eat the build.
**Also:** maintain `data/raw/SOURCES.md` (URL, access date, license, citation). Never commit raw datasets.
**Acceptance:** `python data/scripts/validate.py` passes; every file loads in pandas; SOURCES.md complete.
**Depends on:** M0 (schema table). **Used by:** M2, M3.

---

### M2: Digital twin (Vishal, ~8 h)
**Goal:** a fast, reproducible EV-energy world that is also the safe test bed.
**Interface:**
```python
class World:
    def __init__(self, seed: int, n_users: int = 2000, step_minutes: int = 15, config: dict = ...): ...
    def candidates(self) -> list[dict]          # eligible EVs now (plugged, not capped, not held out)
    def grid_state(self) -> dict                # feeder load, capacity, stress, solar share, tariff slot
    def apply_decisions(self, decisions: list)  # nudges delivered → hidden behavior decides adoption
    def step(self) -> dict                      # advance one interval → telemetry
    def pop_outcomes(self) -> list[dict]        # outcomes whose window just closed
    def inject(self, event: dict) -> None       # heatwave | solar_drop | station_outage | tariff_change
```
**Steps:** (1) vectorized user generation (archetype mix, battery kWh, efficiency, home charger kW, trip schedule from session distributions); (2) default charging engine (plug-in → max power to target SOC) so the evening peak appears; (3) grid: `feeder_load = base_load(t) + ev_load(t)`, `stress = load/capacity`, solar share curve, ToU tariff; (4) stations with connectors, queues, outages; (5) event injector; (6) **hidden behavior model** (`twin/behavior_hidden.py`, never imported by the learner; formulas in guidance §8, parameters in `config/behavior_assumed.yaml`, all flagged ASSUMED); (7) outcome windows → `{adopted, kwh_shifted, savings_inr, battery_stress_delta, opted_out, realized_value}`; (8) **common random numbers**: per-user, per-step streams from `(seed, user_id, step)`.
**Key details:**
- Spontaneous shifting: users shift without a nudge with probability `sigmoid(base_shift_logit[arch])`. So `none` has nonzero baseline value and uplift is a real difference.
- The twin knows **true uplift**; the eval harness uses it as an oracle.
- True trip energy includes noise the Journey model does not know exactly (so calibration is a real test, in simulation).
- Priors: cost framing high effect, green framing near-zero (informed by a published randomized trial; assumed, not Indian evidence); no carryover after incentives stop.
**Acceptance:** 2,000 EVs × 7 days under ~60 s on a laptop; visible evening peak; identical results for the same seed; events change the curves visibly.
**Tests:** reproducibility; event effects; conservation (energy delivered ≤ capacity × time); no negative SOC.
**Depends on:** M0, M1 (with synthetic fallback so it's never blocked).

---

### M3: Perception engines (Vishal)

**M3a Journey Confidence (~5 h):**
- **Energy model:** `Wh/km = base × traffic_factor × driver_factor + HVAC_kW × 1000 / avg_speed`; `HVAC_kW` grows with distance of temperature from a comfort range (capped). Constants ASSUMED; optionally sanity-check against the Vehicle Energy Dataset.
- **Uncertainty:** Monte Carlo (300 to 500 draws) over traffic, temperature error, driver factor → arrival SOC quantiles `q10/q50/q90` and `p_arrive_above_reserve` (reserve default 10% SOC).
- **Calibration:** simulate a few thousand held-out trips with the twin's *true* energy; fit isotonic regression (or Platt) from predicted `p_arrive` to observed frequency; also compute split-conformal interval widths. Persist calibrators.
- **Safety link:** `journey_conf_lb` is computed for the plan's resulting SOC at departure (delaying charging lowers SOC at an early departure).
- **Acceptance:** reliability diagram where "90%" is right ~90% of the time on held-out simulated trips; interval coverage reported; function returns in milliseconds for 500 EVs.
- **Tests:** monotonicity (more SOC → higher confidence), hot-day energy > mild-day energy, calibration error under threshold.

**M3b Battery stress (~2 h):** `stress_score` (0..1, relative) from hours at high SOC, C-rate above threshold, temperature above threshold, depth of discharge. ADVANCED: semi-empirical aging (calendar + cycle) with Monte Carlo parameter ranges → `soh_delta_range_pct` between plans. **Report relative plan differences only, never absolute lifespan.**

**M3c Station wait (~2 h):** Erlang-C mean wait using the forecast arrival rate at the user's ETA and the planned load (so nudges that move arrivals change predicted queues). Skeleton in guidance §9.3. Reliability = assumed outage probability (label it).

**M3d Grid forecast (~3 h):** CORE uses seasonal-naive quantiles. ADVANCED: **Chronos-2** zero-shot probabilistic forecast, benchmarked against seasonal-naive on held-out windows (keep Chronos only if it wins). Outputs: stress quantiles, Grid Stress Windows, Green Charging Windows. Verify the Chronos API against the current model card first.

**M3e Flexibility forecast (~2 h, ADV):** per plugged EV, `shiftable_kwh = min(e_default_in_peak_window, p_max × hours_available_outside_window_before_deadline)`; fleet flexibility `= Σ shiftable_i × P(adopt | nudge, x_i)`; Monte Carlo over adoption draws → `MW ± MW`, labeled "Simulation".

**Depends on:** M2 (telemetry/state), M1 (for realistic distributions).

---

### M4: Planner (Vishal, ~3 h)
**Goal:** for each candidate EV, enumerate candidate charging plans and predict their outcomes.
**Plans:** `default`, `delay` (to green/off-peak window before the deadline), `relocate` (best predicted station; ADV), `slow_charge`, `top_up_now` (protective).
**Outcomes per plan:** `cost_inr`, `journey_conf_lb`, `grid_value`, `battery_stress_delta`, `wait_min`, `creates_new_peak` (bool).
**Key details:** `grid_value` rises with forecast stress where energy is *removed from peak* and with renewable share where it is *added*. The planner is deterministic given perception outputs.
**Acceptance:** returns ≥ 2 plans for typical EVs; `top_up_now` appears when journey confidence is at risk; outcomes are monotone in obvious ways (later start ⇒ lower journey confidence for early departures).
**Depends on:** M3.

---

### M5: Safety (Vishal, ~4 h)
**Goal:** a hard gate the bandit cannot trade away, plus fail-silent behavior.
**Two layers:**
1. **Python invariants** (`safety/invariants.py`): `journey_conf_lb ≥ 0.90`, `arrival_soc_q10 ≥ reserve`, plan power ≤ vehicle limit, no new peak above feeder capacity in the slot. Each returns a human-readable veto reason (shown on the decision card).
2. **Cedar** (`safety/cedar_policies/*.cedar`): quiet hours, max nudges/day (3), opt-out, vehicle supports requested speed, journey check as integer basis points (`journeyConfLbBps >= 9000`). Policy text and call shape in guidance §9.5. Verify the Python binding (`cedarpy`) or use Amazon Verified Permissions.
3. **Fail-silent wrapper:** exceptions, timeouts or Cedar `ERROR` → `fail_silent=True`, frame `none`, error logged.
**Runs twice:** before the bandit (removes unsafe plans) and after allocation (final verify).
**Acceptance:** a property test shows no unsafe plan is ever chosen; forced exceptions yield no message; every veto has a readable reason.
**Depends on:** M3, M4.

---

### M6: Persuasion engine (Vishal, ~6 h) **the core intelligence**
**Goal:** uplift-aware contextual bandit with a first-class `none` action, fatigue awareness, and logged propensities.
**Action set:** `none` ∪ {safe plan × frame ∈ {cost, green, battery, convenience, reassurance} × timing ∈ {at_plug_in, plus_30m, pre_peak}}.
**Features:** `[1, onehot(frame incl. none), onehot(timing), onehot(plan), x ⊗ onehot(frame)]` with ~12 context features (SOC, hours to departure, hour sin/cos, grid stress, savings, delay hours, journey confidence, fatigue, nudges today, archetype posterior, recent-ignore rate). ~80 to 90 dims.
**Algorithm:** Linear Thompson Sampling (skeleton in guidance §9.6) with discounting for non-stationarity. Per user per interval: draw `m` theta samples → score all actions → select by Thompson; **propensity** = selection frequency mixed with ε-exploration (5 to 10%, includes `none`); **uplift** = paired difference `score(a) − score(none)` (report mean and p10). **Global holdout** of ~5% of users never nudged.
**Reward** (same metric for `none` and nudges so uplift is meaningful): `r = w_g·grid_value·kwh_shifted + w_u·savings_inr − w_b·battery_stress_delta − w_w·extra_wait − w_f·fatigue_cost − w_o·opted_out`. Tune weights once, then freeze before the final benchmark.
**Fatigue + archetype posterior:** decayed nudge counter, ignore rate, repeated-frame flag; a per-user archetype posterior updated by Bayes rule using the *learner's own* likelihood (never the hidden one).
**Acceptance:** on a toy problem with known uplift, regret decreases and `none` is chosen when uplift ≤ 0; in the twin, learned policy beats the non-personalized bandit on uplift per nudge; nudges/user stays below the cap.
**Tests:** toy-bandit regret; propensities sum to 1; uplift sign; discounting works after a mid-run behavior shift.
**Depends on:** M2 (reward source), M4, M5.

---

### M7: Fleet allocator (Vishal, ~3 h; OR-Tools adv)
**Goal:** spend a limited attention budget where it produces the most useful change, without creating a new peak.
**Greedy algorithm:** candidates = eligible EVs with a non-`none` best action; rank by `uplift (p10 or mean) × grid_value`; select subject to attention budget (≈ 5 to 10% of plugged-in EVs per interval; the marginal value of the last pick is the displayed shadow price), per-user daily cap, and feeder/station capacity per slot; **anti-herding:** stagger start slots across 15-minute offsets.
**ADVANCED:** solve the same selection with OR-Tools (assignment/CP-SAT) and report the greedy-vs-optimal gap.
**Acceptance:** respects budget, caps, capacity; fleet load after allocation never exceeds capacity in any slot (when feasible); slots are staggered.
**Depends on:** M6, M3.

---

### M8: Language layer
- **M8a Templates (Sneha, ~1 h):** `gridnudge/language/templates.py`, one short template per frame (cost, green, battery, convenience, reassurance), English plus one Indian language, with named placeholders only (`{saving_inr}`, `{start_time}`, `{window}`). No claims beyond what the placeholders carry. This is the permanent fallback.
- **M8b Bedrock + verifier (Vishal, ~3 h, ADV):** Bedrock `converse` call that paraphrases verified facts; **numeric verifier** rejects any number not present in the facts and any forbidden phrase (guarantee, "will last", "100%"), falling back to the template. Cache by `(plan, frame, tone, lang, bucketed numbers)`.
- **M8c Strands copilot (Vishal, ~2 h, ADV):** tools `get_decision`, `explain_veto`, `compare_policies`, `inject_scenario` (output validated against the event schema). Answers cite decision IDs.
**Acceptance:** verifier unit tests (accepts template facts, rejects invented numbers); every shown message has `source` = llm/template and `verified=true`.

---

### M9: Pipeline and StateStore (Vishal, ~4 h)
**Goal:** `decide_batch(request) → list[DecisionRecord]` orchestrating M3 to M8 with fail-silent wrapping, over a swappable `StateStore`.
**Interface:**
```python
class StateStore(Protocol):
    def get_users(self, ids: list[str]) -> dict[str, dict]: ...
    def put_users(self, users: dict[str, dict]) -> None: ...
    def get_model(self, model_id: str) -> dict: ...
    def put_model(self, model_id: str, model: dict, expected_version: int) -> None: ...
    def put_decisions(self, records: list[dict]) -> None: ...
    def get_decision(self, decision_id: str) -> dict | None: ...
```
`InMemoryStore` (dev/tests) and `DynamoStore` (AWS). Every record carries `run_id`, `fail_silent`, `error`.
**Acceptance:** the **local closed loop works**: twin → decide → nudges → outcomes → reward update → improved policy, using `InMemoryStore`, with B4 beating B1 on peak reduction and nudges per user.
**Depends on:** M2 to M8.

---

### M10: AWS infrastructure and handlers (Vishal, ~8 h)
**Goal:** the decision path runs on AWS and the runner talks to it.
**Resources (SAM, skeleton in guidance §11):** HTTP API; Lambdas `decide`, `outcomes`, `reward_update` (SQS-triggered, **reserved concurrency = 1**), `metrics`, `decision_get`, `explain`; DynamoDB `UserState`, `ModelState`, `Decisions` (on-demand); S3 log bucket; SQS FIFO reward queue; CloudWatch custom metrics via structured logs; Amplify for the dashboard.
**Steps:** (1) handlers as thin wrappers around `gridnudge.pipeline` with `DynamoStore`; (2) package numpy/pydantic via layer or container (decide path stays numpy-only); (3) runner client posting batches to `/decide` and outcomes to `/outcomes`; (4) least-privilege IAM; (5) AWS Budgets alert **before** deploying; (6) `curl`/Postman collection for Sneha's API testing.
**Rules:** no always-on resources; use a named AWS profile; never commit credentials; agents must ask before `sam deploy`.
**Acceptance:** the runner completes a run against AWS; the `Decisions` table fills; model updates persist across Lambda invocations; `/metrics` returns the timeline the dashboard needs.
**Fallback (kill rule):** if SQS/reward-update fights back, process rewards synchronously inside `/outcomes` and say so truthfully.
**Depends on:** M9.

---

### M11: Evaluation harness (Vishal, ~7 h core + ~4 h advanced) **this is your proof**
**Policies (same fleet, same seeds, same events):** B0 no nudges; B1 broadcast cost nudge at peak; B2 rule-based; B3 non-personalized bandit; B4 GridNudge.
**Common random numbers** across all policies. **≥ 5 to 10 seeds**, report mean ± CI.
**Metrics:** peak load reduction % (18:00 to 22:00), kWh shifted, nudges per user per day, opt-out rate, uplift per nudge (oracle + estimator), **stranded trips attributable to nudges = 0**, veto count, regret vs oracle, uplift-estimation error (Qini/AUUC), calibration (reliability + coverage), mean ₹ saved per participating user.
**Advanced:** misspecification test (learn under behavior A, evaluate under perturbed B); non-stationarity test (mid-run tariff change); sensitivity sweep; doubly-robust OPE; real-data check against the openICPSR randomized-trial replication data.
**CLI:** `python -m eval.run --seeds 10 --users 2000 --days 7 --scenario heatwave --policies B0 B1 B2 B3 B4` → `results/summary.csv`, `results/timeline.json`, `results/plots/*.png`.
**Also:** `eval/make_replay.py` converts a run into `dashboard/public/replay/timeline.json`... **Vishal writes it to `results/replay/`; Sneha copies it into the dashboard** (keeps ownership clean, see §6).
**Acceptance:** B4 beats B1/B2/B3 on the headline metrics across seeds with CIs; safety metric is zero; plots exist and match `summary.csv`.
**Depends on:** M9.

---

### M12: Dashboard (Sneha, ~8 h core + ~3 h advanced)
**Stack:** Next.js (App Router), TypeScript, Tailwind CSS, Recharts. Types come from `contracts/ts/decision-record.d.ts` (read-only for Sneha).
**Data modes:** `USE_FIXTURES=1` reads `fixtures/*.json` through Next.js route handlers; later `NEXT_PUBLIC_API_BASE` points to the deployed API; **replay mode** reads a bundled `public/replay/timeline.json` (default for the public URL and for recording the video).
**Design:** dark theme, high contrast, one accent per concept (grid = amber, GridNudge = green, baseline = red/grey, safety = blue). **Every chart is labeled "Simulation".** Big numbers, minimal text.
**Pages (priority order):**
1. **`/live` (hero):** fleet load chart with baseline vs GridNudge lines, shaded peak window, grid stress strip; **Event Injector** buttons (Heatwave, Solar drop, Station outage, Tariff change; in fixture/replay mode they switch pre-recorded scenarios); counters for nudges per user, attention budget used (with shadow price), vetoes, peak reduction %.
2. **`/decision/[id]`:** stepper: Perception (three confidence rings) → Plans table → **Safety (veto reasons highlighted, Cedar ALLOW/DENY)** → Persuasion (frame, uplift mean/p10, propensity) → Allocation (slot) → Message (source llm/template, verified ✓). "Explain" button (ADV).
3. **`/evaluation`:** baselines table with CI whiskers, regret curve, calibration reliability diagram, uplift-estimation error, stress-test result.
4. **`/flexibility` (ADV):** forecast band for the next peak ("X MW ± Y MW, simulation").
5. **Copilot drawer, `/testdrive` form (ADV).**
**Acceptance:** all pages render from fixtures with zero backend; veto case is visually striking; switching to the real API requires only an env var change; no number appears that isn't from a fixture/run file.
**Depends on:** M0 fixtures (day one), later M10 API and M11 replay.

---

### M13: README, assumptions, demo script, video (Sneha, ~3 h; Vishal supplies numbers)
- **README:** problem → solution (one diagram) → real vs simulated table → architecture + AWS map → results table from `results/summary.csv` (CIs) → safety and calibration evidence → assumptions register link → honest limitations → how to run → future work.
- **`data/ASSUMPTIONS.md`:** every assumed parameter, its source or "assumed", and how to replace it with real data.
- **Demo script (3 min):** 0:00–0:20 problem; 0:20–0:45 "Plan → Persuade → Learn", ML decides / LLM phrases; 0:45–1:25 twin + Heatwave, baseline spikes; 1:25–2:00 GridNudge flattens peak, silence for low-uplift users; 2:00–2:25 **safety veto moment**; 2:25–2:45 confidence rings, calibration plot, flexibility forecast (labeled simulation); 2:45–3:00 AWS map, CI results, honest limits, future work.
- **Allowed phrases:** "in simulation", "under our assumptions", "calibrated on held-out simulated trips", "relative difference between plans". **Forbidden:** "guaranteed", "your battery will last…", "saves X% in the real world", "proven on real users".
**Rule:** README numbers are copied from run outputs only.

---

### M14: Digital Test Drive (ADVANCED, last; Vishal engine ~3 h, Sneha UI ~2 h)
Inputs: commute km, weekend trips, home-charging access, climate, tariff. Engine: run the twin for a simulated year with Monte Carlo over traffic/temperature/behavior → **Ownership Confidence** (share of simulated weeks with no range-risk event and manageable cost), public-charging dependency, expected cost, battery-stress profile. **Must include an honest "not suitable" path** (e.g. no home charging + long commute + poor station reliability). First thing to cut if time slips.

---

## 5. Repository layout (with owners)

```
gridnudge/
├─ AGENTS.md                         [V]  concise agent rules (see separate file)
├─ README.md                         [S]
├─ CODEOWNERS (or .github/CODEOWNERS)[V]
├─ .githooks/pre-push                [V]
├─ .github/workflows/ci.yml          [V]
├─ scripts/check_ownership.py        [V]
├─ contracts/                        [SHARED, contract/* PRs only]
│  ├─ decision_record.schema.json
│  └─ ts/decision-record.d.ts
├─ fixtures/                         [V writes, S reads]
├─ config/
│  ├─ sim.yaml safety.yaml behavior_assumed.yaml     [V]
│  └─ tariffs.yaml                                   [S]
├─ data/
│  ├─ scripts/                       [S]
│  ├─ raw/  (gitignored) + SOURCES.md                [S]
│  ├─ processed/ (gitignored or small samples)       [S]
│  └─ ASSUMPTIONS.md                                 [S]
├─ gridnudge/                        [V]  (except language/templates.py [S])
├─ twin/                             [V]
├─ eval/                             [V]
├─ services/                         [V]
├─ agent/                            [V]
├─ infra/                            [V]
├─ tests/                            [V]
├─ results/                          [V]  (gitignored except summary + replay)
├─ dashboard/                        [S]
└─ docs/
   ├─ engineering/                   [V]  01_V2_CRITIQUE.md 02_ANTIGRAVITY_GUIDANCE.md 03_DATASETS.md 04_MASTER_PLAN.md BUILD_LOG.md
   └─ (everything else)              [S]  DEMO_SCRIPT.md, submission text, screenshots
```

---

## 6. Git workflow and branching rules (no interference)

### 6.1 Ownership by path (single source of truth)
| Path | Owner |
|---|---|
| `dashboard/**`, `data/scripts/**`, `data/raw/SOURCES.md`, `data/ASSUMPTIONS.md`, `config/tariffs.yaml`, `gridnudge/language/templates.py`, `README.md`, `docs/**` **except** `docs/engineering/**` | **Sneha (`s/`)** |
| Everything else: `gridnudge/**` (except templates.py), `twin/**`, `eval/**`, `services/**`, `agent/**`, `infra/**`, `tests/**`, `config/**` (except tariffs.yaml), `fixtures/**`, `results/**`, `scripts/**`, `.github/**`, `.githooks/**`, `AGENTS.md`, `CODEOWNERS`, `pyproject.toml`, `docs/engineering/**` | **Vishal (`v/`)** |
| `contracts/**` | **Shared**, only via `contract/*` branches, approved by both |

**Rule:** you only commit to files you own. If you need a change in the other person's area, use the request protocol (§6.7).

### 6.2 Branches
| Branch | Purpose | Who can push |
|---|---|---|
| `main` | demo-ready only; tagged at milestones | nobody directly; PR from `dev` with the *other person's* approval |
| `dev` | integration branch | nobody directly; via PRs from feature branches |
| `v/<module>-<desc>` | Vishal's feature branches, e.g. `v/m2-twin`, `v/m6-lints` | Vishal only |
| `s/<module>-<desc>` | Sneha's feature branches, e.g. `s/m12-live-page`, `s/m1-data` | Sneha only |
| `contract/<desc>` | changes to `contracts/**` | either; needs both approvals |
| `hotfix/<desc>` | urgent fix to `main` before submission | either; needs the other's approval |

Branch from `dev`, keep branches short-lived (**merge at least once a day**), and delete after merge.

### 6.3 Pull requests and merging
- **Into `dev`:** PR from your feature branch. If the **ownership check passes** (you only touched your own paths) and CI is green, you may **self-merge** (squash). This keeps the 80/20 workflow fast.
- **Needs the other person's approval:** any PR touching `contracts/**`; any PR into `main`; any PR where the ownership check flags shared files.
- **Merge strategy:** squash into `dev`; `dev → main` with a merge commit; tag milestones (`m1-local-loop`, `m2-aws-live`, `m3-freeze`, `submission`).
- **Never force-push** `main` or `dev`. Force-push is allowed only on your own feature branch.
- **Rebase daily:** `git fetch origin && git rebase origin/dev` on your feature branch before opening the PR.
- **Commit messages:** `type(scope): summary`, e.g. `feat(twin): add heatwave event`, `fix(safety): veto when q10 below reserve`, `docs(readme): add results table`. Commit small, push at least hourly.

### 6.4 What never goes into git
Secrets (`.env`, AWS keys), raw datasets, large model files, `node_modules`, `.venv`, `results/plots` bulk output. Commit only `results/summary.csv` and the small replay JSON.

### 6.5 Contract changes
`contracts/**` is frozen at tag `contracts-v1.0` (end of M0). To change it: open a `contract/<desc>` branch, update the schema **and** regenerated TS types **and** fixtures, bump the version tag (`contracts-v1.1`), get both approvals, merge to `dev`, and message the other person. Prefer **additive** changes (new optional fields) so neither side breaks.

### 6.6 Sync points (so integration is never a surprise)
Three short syncs per day (about 5 minutes each, chat is fine): **midday, evening, night**. Each person posts: what merged into `dev`, what's next, and any blocker/request. After each sync both do `git pull --rebase origin dev`.

### 6.7 Request protocol (instead of touching each other's files)
1. Open an issue/message titled `REQUEST(from→to): <what you need>`, with the exact file/field/format.
2. The owner responds with an ETA or a decision. For data shapes, update fixtures (Vishal) so Sneha is unblocked immediately.
3. Never "just fix it yourself" in the other person's path, even if it's a one-line change.

### 6.8 Enforcement (don't rely on discipline alone)
Rules in AGENTS.md guide the AI agent but do not enforce anything. Enforce with a hook and CI:

**`scripts/check_ownership.py`** (Vishal owns; first match wins):
```python
#!/usr/bin/env python3
"""Fail if the current branch touches files owned by the other person."""
import argparse, fnmatch, subprocess, sys

# Ordered rules: first match wins. owner: "s", "v", or "shared"
RULES = [
    ("contracts/*", "shared"),
    ("docs/engineering/*", "v"),
    ("docs/*", "s"),
    ("dashboard/*", "s"),
    ("data/scripts/*", "s"),
    ("data/raw/SOURCES.md", "s"),
    ("data/ASSUMPTIONS.md", "s"),
    ("config/tariffs.yaml", "s"),
    ("gridnudge/language/templates.py", "s"),
    ("README.md", "s"),
    ("*", "v"),
]
PREFIX_OWNER = {"v/": "v", "s/": "s", "contract/": "shared"}

def owner_of(path: str) -> str:
    for pattern, owner in RULES:
        if fnmatch.fnmatch(path, pattern):
            return owner
    return "v"

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default=None)
    ap.add_argument("--base", default="origin/dev")
    a = ap.parse_args()
    branch = a.branch or subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    who = next((o for p, o in PREFIX_OWNER.items() if branch.startswith(p)), None)
    if who is None:
        return 0  # main, dev, hotfix: not checked here
    files = subprocess.check_output(
        ["git", "diff", "--name-only", f"{a.base}...HEAD"], text=True).split()
    bad = []
    for f in files:
        o = owner_of(f)
        if o == "shared" and who != "shared":
            bad.append((f, "shared (use a contract/* branch)"))
        elif o != "shared" and who != "shared" and o != who:
            bad.append((f, f"owned by {o}"))
    if bad:
        print("OWNERSHIP VIOLATION on branch", branch)
        for f, why in bad:
            print(f"  {f}  -> {why}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

**`.githooks/pre-push`:**
```bash
#!/usr/bin/env bash
python3 scripts/check_ownership.py || { echo "Push blocked: ownership check failed"; exit 1; }
```
Enable once per clone: `git config core.hooksPath .githooks && chmod +x .githooks/pre-push`.

**`.github/workflows/ci.yml`** (runs on PRs):
```yaml
name: ci
on: [pull_request]
jobs:
  checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - name: Ownership check
        run: python scripts/check_ownership.py --branch "${{ github.head_ref }}" --base "origin/${{ github.base_ref }}"
      - name: Tests
        run: |
          pip install -e .[dev]
          pytest -q
```
**`CODEOWNERS`** (replace handles): `* @vishal-handle`, `/dashboard/ @sneha-handle`, `/docs/ @sneha-handle`, `/docs/engineering/ @vishal-handle`, `/data/scripts/ @sneha-handle`, `/config/tariffs.yaml @sneha-handle`, `/contracts/ @vishal-handle @sneha-handle`.
**GitHub settings:** protect `main` (require PR + approval) and `dev` (require PR + CI). *Branch protection on private repos may require a paid plan; if unavailable, rely on the hook, CI and the rules above.*

### 6.9 Agent hygiene (Antigravity)
Each person works in their **own clone** and starts agent sessions only on their own branch. Tell the agent who you are and that it may edit only your paths; the committed `AGENTS.md` and each person's local, gitignored `GEMINI.md` carry this (see the separate AGENTS.md file). Review every agent diff before committing. The pre-push hook is the backstop if an agent wanders.

---

## 7. Interfaces between the two tracks

| Interface | Producer | Consumer | Format / location |
|---|---|---|---|
| Data contract | V | S | `contracts/decision_record.schema.json` + `contracts/ts/*.d.ts` (frozen at `contracts-v1.0`) |
| Sample data | V | S | `fixtures/*.json` (regenerated by `python -m eval.make_fixtures`) |
| Processed datasets | S | V | `data/processed/*.parquet` (schemas in M1) |
| Tariffs | S | V | `config/tariffs.yaml` |
| Message templates | S | V | `gridnudge/language/templates.py` (named placeholders; function `render_template(frame, lang, facts)`) |
| API | V | S | `NEXT_PUBLIC_API_BASE`, endpoints in guidance §6.2, plus a Postman/curl collection |
| Replay run | V | S | `results/replay/timeline.json` → Sneha copies into `dashboard/public/replay/` |
| Final numbers | V | S | `results/summary.csv` (README tables copy from it) |

---

## 8. Schedule with parallel tracks and checkpoints

Assume the build starts the evening of **Thu Oct 8**. Times are targets; **confirm the submission deadline** and adjust.

| Checkpoint | Target | Vishal | Sneha | Done when |
|---|---|---|---|---|
| **C1: Unblock** | Thu night | M0: repo, contracts, fixtures, CODEOWNERS, hook, CI; start M2 | M1 data scripts start; clone repo, enable hook, scaffold Next.js | `contracts-v1.0` tagged; fixtures in `dev`; Sneha rendering fixture data |
| **C2: Twin + baselines** | Fri midday | M2 twin + events; B0/B1/B2 curves | M12 `/live` page on fixtures; M8a templates; finish M1 | first baseline-vs-baseline chart; `/live` shows curves |
| **C3: Local closed loop** | Fri night | M3a/b/c, M4, M5 (invariants), M6, M7, M9; B3/B4 | M12 `/decision/[id]` and `/evaluation` on fixtures | **B4 beats B1 locally**; decision card shows veto |
| **C4: AWS live** | Sat midday | M10 deploy; runner → AWS; Cedar in path | API testing with Postman; dashboard env switch to real API (test) | Decisions table filling; model updates persist |
| **C5: Proof** | Sat evening | M11 multi-seed runs, calibration plot, ADV items in order (Chronos → station → Bedrock → …) | Integrate replay; polish; README skeleton; assumptions register | `results/summary.csv`, plots, replay in dashboard |
| **C6: FREEZE** | Sat night | no new features; bug fixes only; final benchmark on untouched seeds | flexibility page if numbers exist; record video draft | tag `m3-freeze` |
| **C7: Submit** | Sun morning | final `results/`, verify deploy, answer Q&A prep | final video, README with exact numbers, submission form | `submission` tag; everything on the portal |

---

## 9. Kill rules, risks and definition of done

**Kill rules**
- **End of Fri night (C3):** if the local closed loop isn't running, drop **all** ADVANCED items.
- **Mid Sat (C4):** if AWS isn't responding, deploy only `decide` + DynamoDB + S3 and process rewards synchronously; describe SQS truthfully as the intended scale path.
- **Bedrock blocked/slow:** templates only; say so.
- **Cedar packaging pain:** use Amazon Verified Permissions or keep policies in the repo with a Python evaluator test; state exactly what runs where.
- **Data blocked:** use `--synthetic` fallbacks and document them. Never wait on a download.
- **Never cut:** baselines, safety veto, calibration plot, replay mode.

**Risks**
| Risk | Mitigation |
|---|---|
| "You trained on your own simulator" | hidden behavior model, misspecification test, oracle comparison, real-data grounding, honest framing |
| Vishal overloaded | strict priority order, parallel agents, kill rules, Sneha support tasks (§3.3) |
| Integration surprises | frozen contract, fixtures first, three syncs/day |
| AWS cost surprise | Budgets alert day one, serverless only, delete unused stacks |
| LLM invents claims | verifier + template fallback |
| Merge conflicts | disjoint ownership + hook + CI |

**Definition of done (submission)**
- [ ] Closed loop runs end to end; B4 beats baselines with CIs over ≥ 5 seeds; stranded trips attributable to nudges = 0
- [ ] Deployed on AWS (decide path), public dashboard URL works (replay mode at minimum)
- [ ] Safety veto visible on a decision card; calibration plot present
- [ ] README with real-vs-simulated table, assumptions register, honest limitations, all numbers from `summary.csv`
- [ ] 3-minute video recorded and uploaded; submission form complete before the deadline
- [ ] No secrets in git; `main` tagged `submission`

---

## 10. Setup commands (each person, once)

```bash
git clone <repo> && cd gridnudge
git config core.hooksPath .githooks && chmod +x .githooks/pre-push
git checkout dev && git pull
# Vishal
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .[dev]
pytest -q
# Sneha
cd dashboard && npm install && USE_FIXTURES=1 npm run dev
# Daily
git fetch origin && git rebase origin/dev
git checkout -b v/m2-twin      # or s/m12-live-page
```
