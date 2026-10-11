# GridNudge: Repo Analysis and Module-Wise Completion Plan

**Repo analysed:** `gridnudge-dev.zip` (244 files, ~10.8k lines of Python excluding the dashboard; Next.js dashboard with 10 routes)
**Team:** VibeSync (Vishal ≈ 80% hard engineering, Sneha ≈ 20% light tasks)
**Scope of this plan:** every module from the master plan (M0 to M14), including everything that was already planned. Nothing is dropped; items are **ordered**, so stopping at any stage still leaves something truthful and shippable.

---

## 0. What I verified and what I did not

**Verified by running or reading:**
- Unzipped and read the code, configs, build log, agent rules, fixtures and results.
- Installed the package and ran `pytest`: **117 passed** in about 17 s.
- Read `results/summary.csv` (the real benchmark output) and compared it with what the dashboard displays.
- Ran diagnostic simulations (400 users, 2 days) to see what the GridNudge policy (B4) actually does.
- Grepped for dataset loaders, Cedar engine use, Chronos, OR-Tools, Strands, Bedrock, AWS resources.

**Not verified:**
- `npm run build` for the dashboard (the build log claims it passes).
- Anything on AWS (nothing is deployed; I didn't touch AWS).
- Git history and branches (the zip has no `.git`).
- The hackathon submission deadline (check the portal; today is Oct 11).

---

## 1. Findings (read this before anything else)

### 1.1 What is genuinely good
- Clean architecture that matches the plan: contracts, twin, perception, planner, two-stage safety, LinTS bandit with a `none` arm, allocator, language verifier, pipeline, services, eval harness.
- **117 tests pass**, common random numbers exist, fail-silent wrapper exists, a numeric verifier exists, SAM template validates (per the log), ownership enforcement (hook + CI) exists.
- All dashboard routes exist (`/live`, `/decisions`, `/decision/[id]`, `/evaluation`, `/twin`, `/flexibility`, `/testdrive`, `/about`) plus copilot drawer, alerts, event injector, time scrubber.

### 1.2 Critical problems (must fix; ordered by severity)

| # | Severity | Finding | Evidence |
|---|---|---|---|
| **C1** | **Blocker** | **The real benchmark shows GridNudge (B4) does NOT beat the baselines.** Evening peak reduction vs B0: **B1 6.02%**, B2 6.02%, B3 1.32%, **B4 0.46%**. B4 shifts far less energy (668 kWh vs 2,816 for B1) with similar nudge counts. | `results/summary.csv` (5 seeds) |
| **C2** | **Blocker (honesty)** | **The dashboard shows hand-authored numbers, not run results.** Values like 118%, 96%, −14.2%, 0.8 vs 4.0, 62% are hard-coded in components (`ConcentricGauge.tsx`, `PeakReductionCircle.tsx`, `AlertsPopover.tsx`, `EventInjector.tsx`) or come from `make_fixtures.py`. The Copilot drawer even states "All values verified from current simulation run: Peak reduction 14.2%". The real replay shows **~0.2%** reduction (124.1% vs 123.9% of capacity). This violates your own rule 1.1 ("never invent numbers") and would be indefensible in Q&A. | `OperatorCopilotDrawer.tsx:82`, `ConcentricGauge.tsx:13`, `results/replay/timeline.json` vs `dashboard/public/fixtures/metrics.timeline.json` (131.7% → 97.5%) |
| **C3** | High | **Root cause of C1 (diagnosed):** B4 applies `slow_charge` for **~78%** of nudges (648 of 851 in my run; only 182 `delay`). In the twin, an adopted `slow_charge` is counted as adoption and earns a battery-stress bonus (−0.05) but shifts **zero kWh** (kWh shifted is only counted for `delay`). So the bandit learns "slow_charge is rewarding" because the reward's battery term (`w_b = 0.5`) is easy to earn, while peak shaving is not rewarded. Frames are also near-uniform across all five (the bandit hasn't learned that cost framing is strongest). | `/tmp/diag2.py` output; `twin/world.py` lines ~183 to 191, 352 to 356; `persuasion/uplift.py` weights |
| **C4** | High | **Twin bug:** adopting `slow_charge` does `user.charger_kw = max(2.0, user.charger_kw * 0.5)`, which **permanently halves** that user's charger power, so repeated adoption keeps shrinking it and extends charging into the evening. | `twin/world.py:190` |
| **C5** | High | **Policy wrapper hard-codes values:** `delay_hrs = 3.5` for every chosen plan, `capacity_mw = 12.0`, `commute_km = 30`, savings fallback 65. Plan-specific delay and savings from the planner are ignored. | `gridnudge/pipeline.py` (`create_pipeline_policy`) |
| **C6** | High | **Baselines are not distinct:** B1 and B2 have identical results (the SOC ≥ 0.25 rule never binds). So the scoreboard effectively has 4 policies. | `results/summary.csv`, `eval/baselines.py` |
| **C7** | High | **Metric bugs:** `mean_uplift_per_nudge` prints **0.00 for every policy**, yet the outcomes carry `true_uplift` around 0.7 (the summary is not reading it correctly). **`stranded_trips` is not a real measurement:** it counts "adopted and initial SOC < 0.15", with a comment saying safety gates "guarantee" zero. That is an assumption, not a test. | `eval/metrics.py` lines ~88 to 106 |
| **C8** | Medium | **No real datasets are used anywhere.** There are no loaders (`read_parquet`/`read_csv` appear nowhere in `twin/`, `gridnudge/`, `eval/`, `services/`). The twin is fully synthetic. `data/scripts/` contains only `validate.py` (no fetchers). | grep results |
| **C9** | Medium | **Cedar is a Python re-implementation**, not the Cedar engine (`cedarpy`/Verified Permissions not used). Fine as a fallback, but it must be described honestly. | `safety/cedar_check.py`; build log |
| **C10** | Medium | **AWS path never run:** `sam validate` only; no deployment; `DynamoStore` never exercised against real DynamoDB; no live adapter in the dashboard (it reads files via `fs`). | build log; `dashboard/src/lib/data.ts` |
| **C11** | Medium | **Advanced engines absent:** no Chronos, no OR-Tools, no doubly-robust off-policy evaluation, Strands not used (the copilot is plain functions), no Test Drive engine (fixtures only), station forecast and flexibility use fixtures/simple models in the UI. | greps |
| **C12** | Medium | **Missing deliverables:** no root `README.md` (`pyproject.toml` references one), no `templates.py` (M8a; only English defaults inside `render.py`), no demo script, no dashboard CI job. Ownership rules were edited so one person could build the dashboard; `CODEOWNERS` uses placeholder handles. | file listing |

### 1.3 Why this changes the plan
Your plan's headline claim ("GridNudge flattens the peak, with a calibrated safety story") is currently **not supported by your own benchmark**, and the dashboard presents numbers that don't come from it. Everything below is ordered so that **truth and a working learning loop come first**, then data, then AWS, then the advanced engines, then polish.

---

## 2. Gap matrix: every planned module vs the repo

| ID | Module | Status | Evidence / gap |
|---|---|---|---|
| M0 | Repo, contracts, CI, fixtures | **Done** (with caveats) | Contracts, schema, TS types, hook, CI exist. Placeholder `CODEOWNERS` handles; no dashboard CI; fixtures are hand-authored (C2). |
| M1 | Data scripts + processed data + tariffs | **Missing** | Only `validate.py`; no fetchers; no processed files; tariffs config exists, source unverified. |
| M2 | Digital twin + events + hidden behavior | **Partial** | Works, fast, reproducible; synthetic only; slow_charge bug (C4); metrics need fixing. |
| M3a | Journey confidence + calibration | **Done** (synthetic) | Monotonicity and thermal tests; calibration diagnostics in `eval/`. Needs re-calibration after real data. |
| M3b | Battery stress / SoH ranges | **Partial** | Relative stress + SoH delta ranges exist; no validation against public cell data. |
| M3c | Station wait (Erlang-C) | **Partial** | Implemented; not driven by forecast arrival rate or real station list. |
| M3d | Grid forecast (seasonal-naive core; Chronos adv) | **Partial** | Diurnal synthetic quantiles only; no Chronos; no benchmark. |
| M3e | Flexibility forecast | **Partial** | `perception/flexibility.py` exists; dashboard uses a fixture. |
| M4 | Planner | **Done** | Five plan types; tested. Wrapper ignores plan-specific values (C5). |
| M5 | Safety (invariants + Cedar + fail-silent) | **Partial** | Invariants and fail-silent solid; Cedar via Python evaluator (C9). |
| M6 | Persuasion (LinTS, fatigue, uplift, propensity) | **Partial** | Implemented and tested in isolation; not learning the right behavior in the loop (C1, C3). |
| M7 | Allocator | **Partial** | Greedy, budget, cap, capacity, stagger done; OR-Tools missing. |
| M8a | Message templates (multilingual) | **Missing** | No `templates.py`. |
| M8b | Bedrock + verifier | **Partial** | Code and verifier exist; no live Bedrock test. |
| M8c | Strands copilot | **Partial** | Tool functions exist; no Strands Agent; UI copilot answers are canned. |
| M9 | Pipeline + StateStore | **Done / Partial** | `InMemoryStore` + `DynamoStore` exist; `DynamoStore` untested on AWS; policy wrapper hard-codes (C5). |
| M10 | AWS infra + handlers | **Partial** | SAM template + 7 handlers + client; **not deployed**; no integration run. |
| M11 | Evaluation harness | **Partial** | CRN, CIs, calibration, stress tests, replay exist; metric bugs (C7), baselines not distinct (C6), no OPE. |
| M12 | Dashboard | **Partial** | All pages built visually; **numbers hard-coded or fixture-based (C2)**; no live adapter; `npm run build` unverified by me. |
| M13 | README, assumptions, demo script, video | **Missing / Partial** | No README; ASSUMPTIONS/SOURCES exist but not reflecting real data; no video. |
| M14 | Test Drive (engine + UI) | **Partial** | UI + fixtures only; no engine. |

---

## 3. Completion plan: stages (in order)

> **Stage rule:** finish a stage's acceptance gate before starting the next. If time runs out, stop at the end of a stage; the project is still truthful.
> **Sizing:** hours are agent-assisted estimates (prompting, reviewing, running, fixing).

| Stage | Goal | Est. h | Owner split |
|---|---|---|---|
| **A** | Truth and a learning loop that works (fix C1 to C7) | 6 to 9 | Vishal |
| **B** | Wire the dashboard to real results; remove fabricated numbers (C2) | 3 to 4 | Vishal (Sneha QA) |
| **C** | Real data integration (M1) | 4 to 6 | Sneha scripts, Vishal loaders |
| **D** | AWS deployment and live path (M10, M9) | 5 to 7 | Vishal |
| **E** | Advanced engines (all planned items) | 14 to 20 | Vishal (Sneha: templates, UI) |
| **F** | Dashboard completion and live mode | 3 to 4 | Vishal + Sneha |
| **G** | Docs, video, submission (M13) | 4 to 6 | Sneha (Vishal numbers) |

---

## 4. Stage A: Truth and a learning loop that works (Vishal)

**Goal:** B4 either truly beats the baselines on the headline metric, or you know exactly why not and report that honestly. Benchmarks must measure what they claim.

### A1. Fix the twin's plan effects (M2)
- Fix `slow_charge`: apply a **per-session** power cap (store `charger_kw_cap` on the active plan and restore the user's nominal `charger_kw` at unplug/new session). Never mutate the base charger power permanently.
- Define what each plan does physically and make **kWh moved out of the peak window** the shared measure of effect:
  - `delay`: energy that would have been drawn in 18:00 to 22:00 but is moved later.
  - `slow_charge`: energy moved out of the peak window only if the session's longer duration actually leaves the peak (compute it; don't assume).
  - `top_up_now` and `relocate`: define and account for their effects, or record zero shift honestly.
- Record `kwh_shifted_from_peak` in outcomes for every plan type, computed from the user's default-vs-actual charging timeline.
- **Acceptance:** unit tests that a `slow_charge` adoption does not permanently reduce charger power; `kwh_shifted_from_peak` matches a hand-computed example for each plan type.

### A2. Make the policy wrapper use plan data (M9, C5)
- In `create_pipeline_policy`, pass the **planner's** `delay_hours`, `cost_saving_inr` and plan type through to `world.apply_decisions`. Remove the hard-coded 3.5 / 65 / 12.0 / 30.
- Read `capacity_mw` and the commute/departure from the world.
- **Acceptance:** a test shows two plans with different delays produce different `delay_hours` in the applied decision.

### A3. Align the reward with the objective (M6)
- The objective is **peak shaving that is safe and low-fatigue**. Make the reward mostly `grid_value × kwh_shifted_from_peak` (+ savings), with battery stress as a **small** tie-breaker (e.g. `w_b` ≤ 0.1) and a fatigue/opt-out penalty.
- **Normalize reward scale** (e.g. divide by a fixed constant so typical rewards are in about [−1, 1]) so exploration variance `v` is meaningful. Document the weights once; **freeze them before the final benchmark**.
- **Acceptance:** with a toy world where only `delay` shifts energy, the bandit chooses `delay` + `cost` for price-sensitive users and `none` for routine-locked users, and regret decreases (extend `tests/test_persuasion.py`).

### A4. Help the bandit learn in a week of data (M6)
- **Warm-start:** run a short "pre-training" phase in the twin (e.g. days 0 to 1) with higher exploration, then evaluate on days 2 to 6 only; report both.
- Reduce ε after warm-up; tune discount `γ` and `v` once on **development seeds**, then freeze.
- Add **ablation policies** (cheap, very informative): `B4a` = B4 restricted to `delay` plans only; `B4b` = B4 without fatigue features; `Oracle` = twin-informed upper bound. These locate failures fast.
- **Acceptance:** learning curve (regret vs time) trends down; frame choice for price-sensitive archetype posteriors concentrates on `cost`.

### A5. Make baselines distinct and honest (M11, C6)
- B2 must differ from B1: e.g. B2 = "safe rule" that respects journey-confidence (use the same safety invariants) and limits nudges per user per day; B1 = broadcast to everyone.
- Add **B3** as a plain (context-free) bandit and make sure it doesn't use the allocator.
- **Acceptance:** B1 ≠ B2 on peak reduction and nudges/user/day in the same seeds.

### A6. Fix metrics (M11, C7)
- `mean_uplift_per_nudge`: compute from the oracle `true_uplift` of **nudged** outcomes and from the policy's own uplift estimate; report both. Add a test that fails if the value is 0.00 for a policy with adoptions.
- **Stranded trips (real measurement):** at each departure, compute actual SOC at departure vs required energy for the trip; count a **stranded trip** when SOC at departure < trip need + reserve **and** an adopted nudge changed the charging timeline for that session (compare against the counterfactual default timeline). Report `stranded_attributable` and `stranded_any` separately. The safety claim is only valid if this measurement could have been nonzero (add a test with an unsafe plan that triggers it).
- **Acceptance:** tests above pass; `summary.csv` has real uplift values and the new stranded columns.

### A7. Re-run the benchmark properly (M11)
- Iterate on a **small config** (400 users, 2 days, 3 seeds; a few minutes). Run the full config (2,000 users, 7 days, ≥ 5 seeds, ideally 10) **in the background**; note that a full multi-policy run exceeds a few minutes.
- Use **development seeds** for tuning and **untouched seeds** for the final numbers.
- **Acceptance gate (decides what you may claim; see §11):**
  - GridNudge's evening peak reduction beats B1/B2/B3 with non-overlapping 95% CIs, **and**
  - nudges per user per day ≤ B1's, **and** opt-out rate ≤ B1's, **and**
  - real `stranded_attributable` = 0.

If the gate fails after Stage A, don't hide it: use §11 "If B4 does not win".

---

## 5. Stage B: Make the dashboard tell the truth (Vishal; Sneha QA)

**Goal:** every number on screen traces to a run file. Remove all fabricated values (C2).

### B1. Remove hard-coded numbers (M12)
Search and replace all literals; feed values from data:
- `ConcentricGauge.tsx` (`broadcastPct = 118`, GridNudge %), `PeakReductionCircle.tsx` (`reductionPct: 14.2`), `AlertsPopover.tsx` (118% / 14.2 MW / 62% / ₹12.5), `EventInjector.tsx` ("14.2 MW"), and anywhere else `grep -rn "14\.2\|118\|62%\|0\.8\b" dashboard/src` finds.
- Compute: feeder % of capacity, peak reduction, nudges/user/day, vetoes, silent share, budget used and shadow price from the replay/summary JSON.

### B2. Replace the fake Copilot (M8c UI)
- `OperatorCopilotDrawer.tsx` currently returns canned text that claims verification. Replace with: (a) answers built from real data via the same functions as `agent/tools.py` (precomputed to JSON for replay mode), or (b) a clearly labeled **"sample answers"** mode. Never claim "verified from current run" unless it is.

### B3. Generate fixtures from real runs
- Change `eval/make_fixtures.py` so fixtures are **derived from `results/`** (summary, timeline, calibration, decisions sampled from a real run), not hand-written. Keep a separate `fixtures/_demo_placeholders/` only for UI development, never displayed in replay or the public URL.
- One export command: `python -m eval.make_replay` writes everything to `results/replay/`; a copy step puts it in `dashboard/public/replay/`.

### B4. Build checks
- Add a test (Python or a small Node script) that fails the build if the dashboard source contains known demo literals (e.g. `14.2`, `118`) outside tests/docs, and that every replay file exists with provenance `Simulation`.
- Run `npm run build` and `npm run lint` and fix issues; add a dashboard job to CI.

**Acceptance:** with the real replay loaded, `/live` shows the **real** peak percentages and counters; `/evaluation` shows the real `summary.csv` numbers with CIs; the Copilot never states an unsourced number; no demo literal remains.

---

## 6. Stage C: Real data integration (M1)

**Time cap: about 90 minutes of data work before moving on.** Use the `--synthetic` fallbacks and document them if anything blocks. (Dataset links and details: `03_DATASETS.md`.)

### C1. Fetch and prepare (Sneha; scripts in `data/scripts/`)
| Script | Output | Notes |
|---|---|---|
| `fetch_weather.py` | `data/processed/weather_delhi.parquet` | Open-Meteo archive API (no key); hourly `temp_c`, `shortwave_radiation` |
| `fetch_grid.py` | `data/processed/grid_series.parquet` | Grid-India hourly demand/solar/wind (Mendeley), normalized columns `demand_norm`, `solar_norm`, `wind_norm` |
| `fetch_sessions.py` | `data/processed/sessions_profile.parquet` | Harvard Dataverse CSV (no token) or ACN-Data via `acnportal` (token needed): `arrival_hour`, `dwell_hours`, `kwh` |
| `fetch_stations.py` | `data/processed/stations_delhi.parquet` | Ministry of Power list (Dataful), filtered to Delhi; columns per the master plan |
| `tariffs` | `config/tariffs.yaml` | choose one state order or label assumed slots |
| `validate.py` | schema check | already exists; extend to the new files |
- Each script supports `--synthetic`, writes provenance to `data/raw/SOURCES.md`, and appends any fallback to `data/ASSUMPTIONS.md`. Never commit raw datasets.

### C2. Loaders and integration (Vishal)
- `twin/data_loader.py`: loads processed files if present; otherwise returns documented synthetic defaults and logs a warning.
- Wire into: `twin/users.py` (arrival/departure and dwell distributions, charger kW mix, energy), `twin/grid.py` (demand shape and solar curve from `grid_series`), `twin/world.py` (temperature → HVAC energy and heatwave definition), `twin/stations.py` (Delhi station list: connectors, kW), `config/tariffs.yaml` (ToU slots).
- Add `provenance` fields to run metadata: which datasets were real vs synthetic in this run, shown on `/about`.

### C3. Re-validate everything after data changes
- Re-fit the journey calibrator on trips from the **new** twin; re-run tests and the benchmark (stage A gate again); update `ASSUMPTIONS.md` and the README's real-vs-simulated table to match what you actually used.

**Acceptance:** `python data/scripts/validate.py` passes; `twin` runs with and without processed data; run metadata lists real vs synthetic sources; the benchmark is re-run on the new fleet.

---

## 7. Stage D: AWS deployment and the live path (M10, M9)

**Before anything:** set an AWS Budgets alert ($20 and $50), use a named profile with least privilege, pick the region where your Bedrock model is enabled. **Ask for confirmation before any `sam deploy`/delete** (your rules require it).

### D1. Deploy the decision path (Vishal)
1. `sam validate` → `sam build` → `sam deploy --guided` (stack: tables, bucket, queue, API, 7 Lambdas).
2. Confirm packaging: numpy/pydantic/pyyaml available to Lambda (layer or container image). Keep the decide path numpy-only.
3. Smoke-test each endpoint with `curl`/Postman: `POST /decide`, `POST /outcomes`, `GET /metrics`, `GET /decision/{id}`, `POST /explain`, `POST /events`.
4. **Integration test:** `GridNudgeClient` in remote mode drives a short twin run against the deployed API; confirm `Decisions` table fills and **model state persists across invocations** (single-writer `RewardUpdateFn` updates `ModelState`).
5. Add `moto`/localstack tests (or a documented manual checklist) for `DynamoStore` so it doesn't first run in the cloud.
- **Fallback (kill rule):** if SQS/reward update misbehaves, process rewards synchronously inside `/outcomes` and describe SQS honestly as the scale path.

### D2. Observability
- CloudWatch structured metrics (`veto_count`, `fail_silent_count`, `nudges_sent`) verified in the console; keep a screenshot for the README.

### D3. Dashboard live adapter (Vishal; see Stage F)
- Add a data adapter with three modes (Replay default, Live via `NEXT_PUBLIC_API_BASE`, Fixtures dev-only) so the UI doesn't read files directly.

**Acceptance:** a run against AWS completes; decisions and model updates are visible in DynamoDB/S3; `/metrics` returns what the dashboard needs; a screenshot of the deployed stack and CloudWatch metrics exists.

---

## 8. Stage E: Advanced engines (everything already planned; in this order)

Each item is gated by: **core loop still passes tests and the Stage A gate.** Time-box each to ~90 minutes; document blockers in `BUILD_LOG.md`.

### E1. Chronos grid forecasting (M3d) **[Vishal]**
- Use **Chronos-2** (zero-shot, quantiles; verify the current API on the model card) on the real Grid-India series; compare with seasonal-naive on held-out windows (pinball loss or MASE).
- Keep Chronos only if it wins; otherwise keep seasonal-naive and **report the result honestly**.
- Feed forecast quantiles into `perception/grid.py` (stress quantiles, Grid Stress Windows, Green Charging Windows). Add a Chronos/seasonal toggle on `/twin`.
- **Acceptance:** a benchmark table and chart; the pipeline runs with either forecaster.

### E2. Station forecast + `relocate` plan (M3c, M4) **[Vishal]**
- Forecast station arrival rate from the twin's session history (time-of-day profile), feed Erlang-C with the **planned** load; predicted wait at the user's ETA.
- Make `relocate` outcomes depend on real Delhi stations; compare predicted vs simulated waits (calibration check).
- **Acceptance:** `relocate` appears in plans when queue wait is high; test that predicted wait tracks simulated wait within a tolerance.

### E3. Battery stress and SoH ranges validated (M3b) **[Vishal]**
- Validate the semi-empirical aging shape against one public cell dataset (BatteryML packages several). Show the fit chart on `/twin`.
- Keep the caption: "relative difference under stated assumptions, not a lifespan prediction."
- **Acceptance:** a validation plot; unit tests that stress increases with C-rate, high-SOC dwell, temperature.

### E4. Flexibility forecast from the real model (M3e) **[Vishal]**
- Compute `Σ envelope × P(adopt | nudge)` from the **run's** plugged-in EVs and the learned uplift model; Monte Carlo over adoption draws → MW ± MW; budget-sweep table (precomputed).
- Replace `flexibility.json` fixture with generated output; `/flexibility` reads it.
- **Acceptance:** the page's numbers match `perception/flexibility.py` output for the replay run.

### E5. OR-Tools allocator comparison (M7) **[Vishal]**
- Solve the same per-interval selection as an assignment/CP-SAT problem; report the **greedy-vs-optimal gap** over a few intervals/seeds. Keep greedy as the default in Lambda (no heavy dependency); OR-Tools offline or in a container.
- **Acceptance:** a gap table in `/evaluation` (or the README) and a test that both respect budget, caps and capacity.

### E6. Off-policy evaluation (M11) **[Vishal]**
- Implement **inverse propensity** and **doubly-robust** estimators on the logged `(context, action, propensity, reward)`; compare estimates with the twin's true policy value; show the candidate-policy panel.
- **Acceptance:** DR estimate within CI of the true value in the twin for at least one candidate policy; plots on `/evaluation`.

### E7. Stress tests wired to the UI (M11) **[Vishal]**
- `eval/stress.py` exists; run misspecification (behavior A→B), non-stationarity (mid-run tariff change) and a small sensitivity sweep on key assumed parameters; export `stress_tests` into `evaluation.summary.json`.
- Optional: fit response curves on the openICPSR randomized-trial replication data and compare with your assumed priors.
- **Acceptance:** `/evaluation` stress-test panel shows real degradation numbers.

### E8. Real Cedar (M5) **[Vishal]**
- Try `cedarpy` (or Amazon Verified Permissions); add a **parity test** that the Cedar engine and the Python evaluator agree on a grid of contexts; keep the Python evaluator as the documented fallback.
- Be explicit in the README about what runs where.
- **Acceptance:** parity test passes; CI runs it (skipped with a clear message if the binding is unavailable).

### E9. Language layer (M8a/M8b) **[Sneha: templates; Vishal: Bedrock]**
- **Sneha:** write `gridnudge/language/templates.py` (per frame: cost, green, battery, convenience, reassurance; English + one Indian language such as Tamil or Hindi) with **named placeholders only** (`{saving_inr}`, `{start_time}`, `{window}`); `render.py` should import it.
- **Vishal:** enable Bedrock model access, test `converse` live; confirm the numeric verifier rejects invented numbers and falls back to templates; cache by `(plan, frame, tone, lang, bucketed numbers)`. Time words (e.g. "10:30") must be present in the facts so the verifier accepts them.
- **Acceptance:** tests for template fills in both languages; a live Bedrock call (or documented fallback) with `source` and `verified` recorded in decisions.

### E10. Strands operator copilot (M8c) **[Vishal]**
- Wrap `agent/tools.py` functions as Strands tools in an `Agent` with Bedrock; system prompt: answer only from tool output, cite decision IDs, never invent numbers. Validate `inject_scenario` output against the event schema before it reaches the twin.
- Expose via `POST /copilot` (Lambda) and a precomputed Q&A set for replay mode; update the drawer to show **tool-used** and **citation** chips.
- **Acceptance:** five example questions answered from real data with citations; the schema validator rejects a malformed scenario.

### E11. Digital Test Drive engine (M14) **[Vishal engine, Sneha UI polish]**
- Engine: run the twin for a simulated year for a user profile (commute km, weekend trips, home charging, climate, tariff) with Monte Carlo over traffic/temperature/behavior; output **Ownership Confidence** (share of weeks with no range-risk event and acceptable cost), public-charging dependency, expected energy cost vs entered current cost, relative battery stress, and plain reasons.
- Must include a real **"not suitable"** path produced by the engine (not only a fixture).
- API: `POST /testdrive`; replay mode: three precomputed sample profiles from the engine.
- **Acceptance:** all three sample profiles render, with the negative case generated by the engine; disclaimers present.

---

## 9. Stage F: Dashboard completion and live mode (M12)

**Owner:** Vishal builds the adapter; Sneha reviews UI and copy.

1. **Data adapter:** `src/lib/data/` with `replay.ts`, `live.ts`, `fixtures.ts` behind one interface (`getMetrics`, `getDecision`, `getEvaluation`, `getCalibration`, `getFlexibility`, `getTwin`, `getTestDrive`, `askCopilot`). Screens never know the mode.
2. **Mode and run selector** (Replay default; Live with connection status; Fixtures hidden in production builds).
3. **Time controller markers** from `events.json` and notable decisions (first veto, budget exhausted, peak start).
4. **Per-screen checks against the spec** (`GRIDNUDGE_DASHBOARD_SPEC.md`): every panel's source field, tooltips from `glossary.ts`, states (loading, empty, error), accessibility (aria labels, contrast, keyboard, reduced motion).
5. **Decision card:** show real veto, silent and fail-silent examples **picked from the real run** (the replay should include at least one of each); counterfactual uplift line; related-decisions strip.
6. **`/about`:** real vs simulated table generated from run metadata; sources and assumptions registry from the actual files.
7. Remove the "Simulation · sample data" wording where data is a real run, replace with "Simulation · run <id>".

**Acceptance:** switching `NEXT_PUBLIC_API_BASE` flips to live without code changes; a recorded walk-through uses only real values; `npm run build` and lint pass.

---

## 10. Stage G: Documentation, video and submission (M13)

### G1. Root `README.md` **[Sneha, numbers from Vishal]**
Structure: problem → solution (one diagram) → **real vs simulated table (matches actual data used)** → architecture + AWS map (with the deployed stack screenshot) → results table **copied from `results/summary.csv`** with CIs → safety and calibration evidence (reliability plot, stranded-trip measurement definition) → honest limitations → how to run (3 commands) → future work (from `docs/FUTURE.md`).

### G2. Assumptions and sources **[Sneha]**
- `data/ASSUMPTIONS.md`: every assumed parameter (behavior priors, station reliability, traffic noise, feeder capacity, battery aging, tariff if assumed) with source or "assumed" and how to replace.
- `data/raw/SOURCES.md`: URL, access date, license, citation for each dataset actually used.

### G3. Demo script and video **[Sneha records; Vishal supplies a clean run]**
Script (3 minutes): problem → idea ("ML decides, LLM phrases") → inject Heatwave and show the **real** baseline vs GridNudge curves → a **real** safety veto on the decision card → proof screen with CI and calibration → AWS map and honest limits. Record at 1440×900 from the replay, no dev overlays; keep the take deterministic.

### G4. Repo hygiene **[Vishal]**
- Replace `CODEOWNERS` placeholders with real GitHub handles; enable the pre-push hook in each clone; ensure the dashboard CI job runs; tag `m3-freeze` and `submission`; keep secrets and raw data out of git.

### G5. Submission checklist
- [ ] Gate in §4 A7 satisfied, or the "B4 does not win" narrative in §11 used
- [ ] No fabricated numbers on any screen, in the README or in the video
- [ ] AWS stack deployed with a smoke-test record
- [ ] Public dashboard URL works in replay mode
- [ ] README, assumptions, sources, demo script complete
- [ ] Video uploaded; portal form filled **before the deadline**

---

## 11. What you may claim (depends on the Stage A result)

| Outcome | What you can say | What you must not say |
|---|---|---|
| **B4 beats B1/B2/B3 with non-overlapping CIs, stranded attributable = 0** | "In simulation, GridNudge reduces evening peak by X% vs broadcast with fewer nudges per user and zero attributable stranded trips (N seeds, 95% CI)." | Anything about real users or guaranteed savings |
| **B4 matches baselines on peak but with far fewer nudges / less fatigue / safer** | "Comparable peak reduction with N× fewer nudges per user, lower opt-out, and a verified safety gate." Show the attention-efficiency angle (uplift per nudge). | Claims of superior peak reduction |
| **B4 does not win** | "We built a safety-gated decision system with a causal loop; in our twin it currently does X vs baseline Y; we diagnosed why (reward alignment / plan effects) and here is the ablation." Lead with safety, calibration, auditability, silence, and the honest evaluation method. | Any of the fabricated headline numbers (14.2%, 118%, 0.8 vs 4.0) |

---

## 12. Ownership and sequencing for two people (≈ 80/20)

**Vishal (hard, sequential):** Stage A (twin fixes, wrapper, reward, bandit, baselines, metrics, benchmark) → B (remove fabricated numbers, real fixtures) → C2 (loaders) → D (AWS) → E1 to E8, E10, E11 (engines) → F1 to F3 (adapter) → G4.

**Sneha (light, parallel from now, no dependency on Stage A except final numbers):**
1. C1 data fetch scripts (`data/scripts/*`), SOURCES/ASSUMPTIONS updates.
2. E9 `templates.py` (English + one Indian language), tests for placeholders.
3. QA of the dashboard against the spec and against real files once Stage B lands (a checklist: every number traces to a file).
4. Test the deployed API with a Postman collection and file issues.
5. G1 to G3 (README, assumptions, demo script, video) after Vishal publishes the final `results/summary.csv` and replay.
6. Proofread claims against §11.

**Git:** keep the existing rules (feature branches `v/…` and `s/…`, PRs into `dev`, squash merges, ownership hook). Note the repo shows the dashboard was built under Vishal's ownership override; restore the original ownership map for the remaining work, and give Sneha explicit paths: `data/scripts/**`, `gridnudge/language/templates.py`, `README.md`, `docs/**` (non-engineering), and dashboard text/styling review via PRs.

---

## 13. Ordered checklist (copy into `docs/BUILD_LOG.md` as you go)

**Stage A (truth + learning loop)**
- [x] A1 per-session slow_charge cap; per-plan `kwh_shifted_from_peak`
- [x] A2 policy wrapper uses planner `delay_hours`/`cost_saving_inr`; no hard-coded 3.5/65/12/30
- [x] A3 reward realigned and normalized; weights frozen
- [x] A4 warm-start, tuning on dev seeds, ablations (`B4a`, `B4b`, Oracle)
- [x] A5 B1 ≠ B2; B3 is a plain bandit
- [x] A6 uplift metric fixed; real stranded-trip measurement + test that can fail
- [x] A7 benchmark on dev seeds → final run on untouched seeds → gate decision

**Stage B (truth in the UI)**
- [x] B1 remove all hard-coded demo numbers
- [x] B2 replace canned copilot claims
- [x] B3 fixtures derived from `results/`
- [x] B4 build check for demo literals; `npm run build`; dashboard CI

**Stage C (data)**
- [x] C1 five fetch scripts with `--synthetic` fallbacks; sources logged
- [x] C2 `twin/data_loader.py` wired into users, grid, world, stations, tariffs
- [x] C3 re-calibrate, re-test, re-benchmark; update assumptions and README table

**Stage D (AWS)**
- [ ] Budget alert; deploy; smoke tests; integration run; `DynamoStore` tests; CloudWatch evidence

**Stage E (advanced)**
- [ ] E1 Chronos vs seasonal-naive · E2 station forecast + relocate · E3 battery validation · E4 real flexibility · E5 OR-Tools gap · E6 OPE · E7 stress tests in UI · E8 real Cedar + parity test · E9 templates + Bedrock · E10 Strands copilot · E11 Test Drive engine

**Stage F (dashboard live mode)**
- [ ] Adapter, mode selector, markers, spec checks, real decision examples, `/about` from metadata

**Stage G (submission)**
- [ ] README · assumptions/sources · demo script · video · hygiene (CODEOWNERS, tags) · portal submission

---

## 14. Handy commands

```bash
# Tests (≈17 s)
pytest -q

# Small, fast iteration run (a few minutes); use real config only in the background
python -m eval.run --seeds 3 --users 400 --days 2 --scenario heatwave

# Full benchmark (long): run in the background and write to a log
nohup python -m eval.run --seeds 5 --users 2000 --days 7 --scenario heatwave > results/full_run.log 2>&1 &

# Find fabricated demo numbers in the dashboard
grep -rn "14\.2\|118\b\|62%" dashboard/src

# Dashboard
cd dashboard && npm ci && npm run build && npm run lint
```

**Diagnostic used in this analysis (what plan types and frames the policy applies):**
```python
# diag.py — run from the repo root
import collections
from twin.world import World
from twin.runner import run_simulation
from eval.baselines import create_policy_b4

pol = create_policy_b4(seed=7)
types, frames = collections.Counter(), collections.Counter()
def wrapped(w):
    ds = pol(w)
    for d in ds:
        types[d["plan"].get("type")] += 1
        frames[d["frame"]] += 1
    return ds

w = World(seed=7, n_users=400)
r = run_simulation(world=w, n_steps=192, policy_fn=wrapped)
print("plan types", dict(types)); print("frames", dict(frames))
```
In my run this printed `{'delay': 182, 'top_up_now': 2, 'slow_charge': 648, 'default': 19}` and a near-uniform frame mix. Re-run it after Stage A: the goal is mostly `delay` (and `none`), with `cost` dominating for price-sensitive users.
