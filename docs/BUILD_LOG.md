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


