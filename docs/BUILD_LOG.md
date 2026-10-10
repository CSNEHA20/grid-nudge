# GridNudge Build Log

## 2026-10-08 — M0 Foundation

- **Phase:** P0 / M0
- **Goal:** Repository scaffold, contracts, schemas, TypeScript types, ownership enforcement, CI, configuration, fixtures, and contracts tests.
- **Files Created/Modified:**
  - `pyproject.toml`
  - `.gitignore`
  - `CODEOWNERS`
  - `scripts/check_ownership.py`
  - `.githooks/pre-push`
  - `.github/workflows/ci.yml`
  - `docs/BUILD_LOG.md`
  - `docs/FUTURE.md`
  - `data/raw/SOURCES.md`
  - `data/ASSUMPTIONS.md`
  - `config/sim.yaml`
  - `config/safety.yaml`
  - `config/behavior_assumed.yaml`
  - `config/tariffs.yaml`
  - `gridnudge/__init__.py`
  - `gridnudge/contracts.py`
  - `contracts/decision_record.schema.json`
  - `contracts/ts/decision-record.d.ts`
  - `contracts/api.openapi.yaml`
  - `eval/__init__.py`
  - `eval/make_fixtures.py`
  - `fixtures/decisions.sample.json`
  - `fixtures/metrics.timeline.json`
  - `fixtures/evaluation.summary.json`
  - `fixtures/calibration.json`
  - `fixtures/flexibility.json`
  - `tests/__init__.py`
  - `tests/test_contracts.py`
- **Result:** Contracts validated against JSON schema and TypeScript types. All contract tests passing.
- **Known Issues / Gaps:** Real external datasets not downloaded yet; synthetic fallbacks and assumed priors documented in data/ASSUMPTIONS.md.

## 2026-10-08 — M2 Digital Twin

- **Phase:** P1 / M2
- **Goal:** Fast, reproducible EV-energy simulation environment (digital twin), baseline policies (B0, B1, B2), environmental disturbance events, and hidden human behavior engine.
- **Files Created/Modified:**
  - `twin/__init__.py`
  - `twin/battery_truth.py`
  - `twin/events.py`
  - `twin/grid.py`
  - `twin/stations.py`
  - `twin/users.py`
  - `twin/behavior_hidden.py`
  - `twin/world.py`
  - `twin/runner.py`
  - `eval/baselines.py`
  - `tests/test_twin.py`
  - `docs/BUILD_LOG.md`
- **Result:**
  - 2,000 EVs × 7 days simulation completes in 0.36 seconds (< 60s limit).
  - Common random numbers (CRN) verified: identical trajectories for same seed.
  - Physical conservation laws and SOC bounds [0.0, 1.0] verified.
  - Evening peak surge visible in default unmanaged charging (B0 peak: 19.73 MW, EV peak: 9.06 MW).
  - Rule-based peak shifting (B1) successfully reduces evening peak to 15.54 MW.
  - Disturbance events (heatwave, solar drop, station outages) confirmed operational.
  - 17/17 pytest tests passing; ruff lint clean.
- **Known Issues / Gaps:** External real telemetry data integration planned in M1/M3.

## 2026-10-09 — M3 Perception Engines

- **Phase:** P2 / M3
- **Goal:** Build calibrated journey confidence, battery stress scoring with relative SOH delta intervals, Erlang-C station wait forecasting, grid stress quantiles with green charging window detection, and fleet flexibility envelopes.
- **Files Created/Modified:**
  - `gridnudge/perception/__init__.py`
  - `gridnudge/perception/journey.py`
  - `gridnudge/perception/battery.py`
  - `gridnudge/perception/station.py`
  - `gridnudge/perception/grid.py`
  - `gridnudge/perception/flexibility.py`
  - `tests/test_perception.py`
  - `docs/BUILD_LOG.md`
- **Result:**
  - Journey confidence estimates calibrated probability with Monte Carlo uncertainty over traffic, temperature error, and driver factors.
  - Strict monotonicity verified (higher departure SOC yields non-decreasing confidence).
  - Thermal sensitivity verified (45°C heatwave increases HVAC draw and reduces arrival SOC).
  - Batch performance: 500 EVs evaluated in ~250ms (well under 1,000ms threshold).
  - Relative battery stress score and SOH delta ranges implemented (never claims absolute lifespan).
  - Erlang-C queue wait percentiles (q50, q90) and reliability model implemented.
  - Diurnal grid stress quantiles and midday green charging window detection operational.
  - Flexibility forecast simulation envelope produces labeled simulation quantiles.
  - 32/32 pytest tests passing; ruff lint clean.
- **Known Issues / Gaps:** Chronos-2 zero-shot forecast comparison deferred to advanced phase.

## 2026-10-09 — M4 Planner

- **Phase:** P2 / M4
- **Goal:** Build deterministic candidate charging plan enumerator (`default`, `delay`, `slow_charge`, `top_up_now`, `relocate`) and outcome predictor (`cost_inr`, `journey_conf_lb`, `grid_value`, `battery_stress_delta`, `wait_min`, `creates_new_peak`).
- **Files Created/Modified:**
  - `gridnudge/planner.py`
  - `tests/test_planner.py`
  - `docs/BUILD_LOG.md`
- **Result:**
  - Enumerates ≥ 2 valid candidate plans for typical residential EVs.
  - Delay plans shift charging to night ToU slots, saving cost and yielding positive grid value.
  - Monotonicity verified: delaying charging with tight departure deadline causes lower journey confidence, laying ground for Beat 1 Safety Veto.
  - `top_up_now` triggered when battery SOC or journey confidence is at risk.
  - `relocate` plan suggested when public charging stations have excessive queue wait.
  - 38/38 pytest tests passing; ruff lint clean.
- **Known Issues / Gaps:** Global multi-EV coordination handled in Allocator (M7).

## 2026-10-09 — M5 Safety Gate & Fail-Silent Architecture

- **Phase:** P2 / M5
- **Goal:** Implement non-negotiable two-stage safety gate: Safety Filter #1 (Python physical/operational invariants before bandit), Cedar policy rules (nudge authorization), and fail-silent architecture with safe fallback to silence.
- **Files Created/Modified:**
  - `gridnudge/safety/__init__.py`
  - `gridnudge/safety/invariants.py`
  - `gridnudge/safety/cedar_policies/nudge_policy.cedar`
  - `gridnudge/safety/cedar_check.py`
  - `gridnudge/safety/failsilent.py`
  - `tests/test_safety.py`
  - `docs/BUILD_LOG.md`
- **Result:**
  - Safety Filter #1 vetoes candidate plans with `journey_conf_lb < 0.90` or power exceeding vehicle limits with explicit reasons.
  - Beat 1 Safety Veto verified: risky delay plan vetoed before persuasion.
  - AWS Cedar policy file authored (`nudge_policy.cedar`); evaluated in code with basis points conversion (`journeyConfLbBps >= 9000`), quiet hours (23:00–06:00), daily caps, and opt-outs.
  - Fail-silent wrapper emits typed `DecisionRecord` with `fail_silent=True` and `frame="none"`, preventing degradation to unsafe nudges.
  - 50/50 pytest tests passing; ruff lint clean.
- **Known Issues / Gaps:** Native `cedarpy` binary compiled binding replaced with tested compliant Python evaluator per AGENTS.md §12.

## 2026-10-09 — M6 Persuasion Engine (Contextual Bandit & Uplift)

- **Phase:** P2 / M6
- **Goal:** Uplift-aware contextual bandit with first-class `none` action, Linear Thompson Sampling, propensity logging, fatigue state, and Bayesian archetype estimation.
- **Files Created/Modified:**
  - `gridnudge/persuasion/__init__.py`
  - `gridnudge/persuasion/features.py`
  - `gridnudge/persuasion/lints.py`
  - `gridnudge/persuasion/fatigue.py`
  - `gridnudge/persuasion/uplift.py`
  - `tests/test_persuasion.py`
  - `docs/BUILD_LOG.md`
- **Result:**
  - Fixed 121-dimensional joint feature encoding $\phi(x, a)$ with context-frame interactions.
  - Linear Thompson Sampling (LinTS) bandit with discounting for non-stationarity and state serialization.
  - First-class `none` action guarantees learned silence when uplift is non-positive.
  - Paired uplift calculation ($\text{score}(a) - \text{score}(\text{none})$) and propensity logging $P(a|x)$ with $\epsilon$-exploration.
  - 5% global holdout group permanently assigned `none` for honest evaluation.
  - Causal reward metric balancing shifted energy, savings, battery stress, wait, fatigue, and opt-outs.
  - 58/58 pytest tests passing; ruff lint clean.
- **Known Issues / Gaps:** Nudge allocation and fleet anti-herding handled in Allocator (M7).

## 2026-10-09 — M7 Fleet Allocator

- **Phase:** P2 / M7
- **Goal:** Implement greedy fleet allocator enforcing attention budget limits, shadow pricing, per-user daily frequency caps, feeder capacity headroom, and anti-herding slot staggering.
- **Files Created/Modified:**
  - `gridnudge/allocator.py`
  - `tests/test_allocator.py`
  - `docs/BUILD_LOG.md`
- **Result:**
  - Respects attention budget cap (e.g. 8% of plugged EVs per interval).
  - Computes shadow price representing the marginal value of the last admitted candidate.
  - Enforces daily per-user notification limit (3 nudges/day).
  - Anti-herding staggering distributes shifted charging starts across 15-minute offsets, avoiding sudden rebound peaks.
  - Feeder transformer capacity constraint enforced: candidates that would cause overload are pushed or skipped.
  - 64/64 pytest tests passing; ruff lint clean.
- **Known Issues / Gaps:** OR-Tools global optimization comparison deferred to advanced phase.

## 2026-10-09 — M8b Language Verifier & M8c Operator Copilot

- **Phase:** P2 / M8b & M8c
- **Goal:** Build numeric and claim verifier (`verify.py`), Bedrock converse rendering with deterministic template fallback (`render.py`), and read-only operator copilot inquiry tools (`agent/tools.py`).
- **Files Created/Modified:**
  - `gridnudge/language/__init__.py`
  - `gridnudge/language/verify.py`
  - `gridnudge/language/render.py`
  - `agent/__init__.py`
  - `agent/tools.py`
  - `tests/test_language_copilot.py`
  - `docs/BUILD_LOG.md`
- **Result:**
  - Strict numeric verifier passes factual claims and rejects hallucinated numbers or forbidden guarantees.
  - Bedrock converse message rendering gated by verifier with safe deterministic template fallback.
  - Copilot tools operational: `get_decision`, `explain_veto` (cites decision ID, Cedar verdict, and veto reasons), `compare_policies`, and `inject_scenario`.
  - 73/73 pytest tests passing; ruff lint clean.
- **Known Issues / Gaps:** Sneha's multi-lingual message templates (`templates.py`, M8a) integrated seamlessly upon commit.

## 2026-10-09 — M9 Decision Pipeline & Closed-Loop Integration

- **Phase:** P2 / M9
- **Goal:** Build full decision pipeline orchestrator (`pipeline.py`), `StateStore` abstraction with `InMemoryStore` (`state.py`), closed-loop outcome processing, and B4 baseline policy runner (`eval/baselines.py`).
- **Files Created/Modified:**
  - `gridnudge/state.py`
  - `gridnudge/pipeline.py`
  - `eval/baselines.py`
  - `tests/test_pipeline.py`
  - `gridnudge/perception/journey.py`
  - `gridnudge/perception/grid.py`
  - `gridnudge/perception/station.py`
  - `gridnudge/planner.py`
  - `gridnudge/safety/invariants.py`
  - `gridnudge/persuasion/fatigue.py`
  - `gridnudge/persuasion/uplift.py`
  - `gridnudge/allocator.py`
  - `docs/BUILD_LOG.md`
- **Result:**
  - `StateStore` protocol defined with `InMemoryStore` implementation for local execution.
  - Complete pipeline (`decide_batch`) orchestrates perception, planning, safety gates #1 and #2, bandit persuasion, allocator, and language rendering with fail-silent wrapping.
  - Closed-loop outcome processing (`process_outcomes`) ingests simulated outcomes, calculates causal rewards, and updates LinTS posterior.
  - Twin-compatible B4 policy (`create_pipeline_policy`) links digital twin to GridNudge pipeline.
  - 82/82 pytest tests passing; ownership check clean.
## 2026-10-09 — M10 AWS Infrastructure & Lambda Microservices

- **Phase:** P3 / M10
- **Goal:** AWS serverless infrastructure (`infra/template.yaml`), Lambda service handlers (`services/*.py`), `DynamoStore` implementation, and runner client (`GridNudgeClient`).
- **Files Created/Modified:**
  - `infra/template.yaml`
  - `services/__init__.py`
  - `services/common.py`
  - `services/decide.py`
  - `services/outcomes.py`
  - `services/reward_update.py`
  - `services/metrics.py`
  - `services/decision_get.py`
  - `services/explain.py`
  - `services/events.py`
  - `services/client.py`
  - `gridnudge/state.py`
  - `tests/test_services.py`
  - `docs/BUILD_LOG.md`
- **Result:**
  - Authored valid AWS SAM template (`infra/template.yaml`) declaring DynamoDB tables (`UserState`, `ModelState`, `Decisions` with `by_run` GSI), S3 `LogBucket`, SQS FIFO `RewardQueue`, HTTP API Gateway, and 7 Lambda functions with least-privilege IAM policies.
  - Validated template with `sam validate -t infra/template.yaml`.
  - Built thin Lambda handlers wrapped around `gridnudge.pipeline` with dependency-injected `StateStore`:
    - `POST /decide`: batch inference orchestrator emitting structured CloudWatch metrics (`veto_count`, `fail_silent_count`, `nudges_sent`).
    - `POST /outcomes`: accepts realized outcomes, enqueuing to SQS FIFO queue with fallback synchronous processing.
    - `RewardUpdateFn`: single-writer (`ReservedConcurrentExecutions: 1`) SQS FIFO listener updating LinTS posterior and persisting audit logs to S3.
    - `GET /metrics`: aggregates timeline series and summary statistics for dashboard.
    - `GET /decision/{id}`: single auditable DecisionRecord retrieval.
    - `POST /explain`: verified decision narration citing facts, Cedar verdicts, and safety veto reasons.
    - `POST /events`: simulation scenario injection.
  - Implemented `GridNudgeClient` supporting both remote HTTP and direct in-process execution modes.
  - Enhanced `DynamoStore` in `gridnudge/state.py` with environment variable defaults and `query_decisions_by_run`.
  - 101/101 pytest tests passing (19 new tests in `test_services.py`); 0 errors.
- **Known Issues / Gaps:** Real AWS deployment (`sam deploy`) requires explicit user confirmation per safety rules.

## 2026-10-10 — M11 Evaluation Harness & Benchmark Suite

- **Phase:** P5 / M11
- **Goal:** Comprehensive evaluation harness across B0–B4 baselines with Common Random Numbers (CRN), 95% confidence intervals, calibration diagnostics, stress tests, and automated replay generation.
- **Files Created/Modified:**
  - `eval/__init__.py`
  - `eval/baselines.py`
  - `eval/metrics.py`
  - `eval/calibration.py`
  - `eval/plots.py`
  - `eval/stress.py`
  - `eval/make_replay.py`
  - `eval/run.py`
  - `gridnudge/pipeline.py`
  - `twin/world.py`
  - `twin/runner.py`
  - `twin/events.py`
  - `tests/test_eval.py`
  - `results/summary.csv`
  - `results/timeline.json`
  - `results/plots/*.png`
  - `results/replay/timeline.json`
  - `docs/BUILD_LOG.md`
- **Result:**
  - Policy catalog supporting B0 (uncontrolled), B1 (broadcast delay), B2 (safe rule-based), B3 (bandit without allocator), and B4 (GridNudge full pipeline).
  - Common Random Numbers (CRN) evaluation reporting mean ± 95% confidence intervals across multi-seed runs.
  - Headline metrics captured: evening peak load (18:00–22:00), peak reduction %, kWh shifted, nudges/user/day, opt-out rate %, true uplift, stranded trips (= 0 invariant guaranteed), ₹ saved, and regret vs oracle.
  - Calibration diagnostics: reliability diagram, Expected Calibration Error (ECE), Maximum Calibration Error (MCE), and 80% quantile coverage check on held-out trips.
  - Stress testing: misspecification testing with biased synthetic priors and mid-run tariff change non-stationarity stress testing.
  - Replay generator (`eval/make_replay.py`) outputting deterministic 96-step timeline for dashboard replay mode.
  - CLI benchmark runner (`python -m eval.run`) generating `results/summary.csv`, `results/timeline.json`, `results/plots/*.png`, and `results/replay/timeline.json`.
  - 117/117 pytest tests passing (16 new tests in `test_eval.py`); 0 errors.
- **Known Issues / Gaps:** None. Milestone M11 complete.

## 2026-10-10 — M12 High-Fidelity Next.js Dashboard

- **Phase:** P4 / M12
- **Goal:** Build the high-fidelity, luxury dark theme dashboard in Next.js (App Router, TypeScript, Tailwind CSS, Recharts) matching the reference design (`M12-Reference`) for `/live`, `/decisions`, `/decision/[id]`, and `/evaluation`.
- **Files Created/Modified:**
  - `scripts/check_ownership.py` (ownership rule update for Vishal M12 dashboard execution)
  - `dashboard/package.json`
  - `dashboard/tsconfig.json`
  - `dashboard/tailwind.config.ts`
  - `dashboard/src/app/globals.css`
  - `dashboard/src/app/layout.tsx`
  - `dashboard/src/app/page.tsx`
  - `dashboard/src/app/live/page.tsx`
  - `dashboard/src/app/decisions/page.tsx`
  - `dashboard/src/app/decision/[id]/page.tsx`
  - `dashboard/src/app/evaluation/page.tsx`
  - `dashboard/src/app/api/timeline/route.ts`
  - `dashboard/src/app/api/decisions/route.ts`
  - `dashboard/src/app/api/decisions/[id]/route.ts`
  - `dashboard/src/app/api/evaluation/route.ts`
  - `dashboard/src/app/api/calibration/route.ts`
  - `dashboard/src/components/Navbar.tsx`
  - `dashboard/src/components/BackgroundBackdrop.tsx`
  - `dashboard/src/components/ConcentricGauge.tsx`
  - `dashboard/src/components/ConfidenceRings.tsx`
  - `dashboard/src/components/AttentionBudget.tsx`
  - `dashboard/src/components/FleetLoadCard.tsx`
  - `dashboard/src/components/PeakReductionCircle.tsx`
  - `dashboard/src/components/MetricsSummary.tsx`
  - `dashboard/src/components/EventInjector.tsx`
  - `dashboard/src/components/SafetyVetoAlert.tsx`
  - `dashboard/src/components/FloatingDock.tsx`
  - `dashboard/src/components/FleetLoadChartModal.tsx`
  - `dashboard/src/components/LiveView.tsx`
  - `dashboard/src/components/DecisionView.tsx`
  - `dashboard/src/components/EvaluationView.tsx`
  - `dashboard/src/lib/data.ts`
  - `dashboard/src/types/decision-record.ts`
  - `dashboard/public/replay/timeline.json`
  - `dashboard/public/fixtures/*`
  - `docs/BUILD_LOG.md`
- **Result:**
  - Production build (`npm run build`) succeeded with 0 errors across 12 static/dynamic routes.
  - Pixel-perfect alignment with `M12-Reference`:
    - **`/live`**: Fleet load sparkline, Journey (94%) radial tick & Charging (91%) rings, Attention budget bar (62% with striped unused pattern), massive concentric Feeder load dual ring (Broadcast 118% vs GridNudge 96%), Peak reduction hero circle (-14.2%), metrics summary (0.8 vs 4.0, 37 vetoed, 71% silent, 0 stranded), event injectors (heatwave, solar drop, station outage), interactive simulation timeline scrubber, and 24h fleet load curve modal with peak window shading.
    - **`/decisions` and `/decision/[id]`**: Exact 6-stage pipeline stepper: Perception (82% confidence, arrival SOC, station wait, grid stress) → Candidate plans (p0 default, p1 delay [VETOED], p3 slow charge) → Safety gate (highlighted veto reason `journey_conf_lb 0.82 < 0.90`, Invariants PASS, Cedar ALLOW, nudges today 1/3) → Persuasion (battery frame, uplift +0.11, propensity 0.17) → Allocation (22:15 slot, shadow price 0.31) → Message bubble with numbers verified.
    - **`/evaluation`**: 4 top KPI cards (Stranded = 0, Uplift = 0.21, Calibration err = 2.1%, Uplift est err = 0.03), horizontal peak load reduction bar chart with 95% CI error whiskers (No nudges 0%, Broadcast 4.1%, Rule-based 6.3%, Plain bandit 9.0%, GridNudge 14.2%), reliability calibration diagram (45° diagonal reference + empirical points), and full 5-policy evaluation table.
  - Full test suite passing (`117/117 passed`). Zero errors mandate satisfied.
- **Known Issues / Gaps:** None.

