# GridNudge: Gap-Fill Implementation Plan (after the 4th repo review)

**Repo analysed:** `gridnudge-dev__3_.zip` (4th version)
**Goal:** turn it into a working, defensible, fresh-clone-reproducible project. Every item below has a cause, a fix, and an acceptance check.
**Deadline:** check the portal. Today is Oct 11, so the plan is ordered so that stopping after any stage still leaves a truthful state.

---

## 0. What I verified and what I did not

**Verified (ran it myself):**
- Unzipped the repo, diffed it against the previous version, read results, README, SOURCES, build log.
- **Fresh-clone test run:** `pytest` stops with **4 collection errors** (`NameError: name 'Optional' is not defined` in `eval/baselines.py`). With that one import patched in a scratch copy: **148 passed, 5 failed**. After also installing `pyarrow` and running the six data scripts: **152 passed, 1 failed** (the weather dataset, see G2).
- `scripts/check_claims.py` passes (README/DEMO numbers match `results/summary.csv`).
- Read `results/summary.csv`, `results/pareto.csv`, `results/calibration.json`.
- Checked every `data/scripts/fetch_*.py` to see whether it downloads or generates.

**Not verified:** the live AWS stack (my sandbox cannot reach it), `npm run build` on this version (the build log says 16/16 routes compile), the git history (no `.git` in the zip).

---

## 1. What is now genuinely good (keep it)

- **Honesty improved a lot.** README now states B1/B2 beat GridNudge on peak reduction at higher nudge volume; SOURCES labels synthetic datasets "Synthetic, shaped after ..."; AWS account ID removed; `scripts/check_claims.py` guards claim drift.
- **Calibration fixed:** ECE 0.0101 and 80% interval coverage 0.804 (was 0.0291 and 0.596). Max calibration error is still 0.2409; report it.
- **Pareto evaluation exists** (`eval/pareto.py`, `results/pareto.csv`), the right way to compare policies at different attention levels.
- **Pretraining, shiftable-energy feature, allocator change, ablation policies** are implemented.
- **AWS hardening landed earlier** (Decimal codec, compact model storage, numpy-only calibrator, Lambda build script, `ENABLE_BEDROCK` switch).

### The current honest result
| Policy | Peak reduction | Nudges/user/day | kWh shifted per nudge |
|---|---|---|---|
| B1 broadcast | 17.72% | 0.67 | 1.29 |
| B2 rule-based | 15.94% | 0.54 | 1.44 |
| B3 plain bandit | 10.38% | 0.22 | 1.87 |
| **B4 GridNudge** | **9.38%** | **0.14** | **2.65** |

Pareto sweep (smaller config, 500 users, 1 day): at matched volume B4 is about equal to B2 (5.26% at 0.33 vs 5.01% at 0.32 nudges/user/day) and clearly better than B3 (3.17% at 0.30), with the highest energy per nudge (3.7 vs 3.07 for B2). **But B4 plateaus near 6% when its budget grows** (12%: 6.01%, 18%: 5.97%) while broadcast keeps rising (10.9% at full volume). So the true story is: *most energy per nudge, lowest fatigue and opt-out, but it cannot yet use extra attention to reach rule-based peak reduction.*

---

## 2. Gap register

| # | Severity | Gap | Evidence | Fix (section) |
|---|---|---|---|---|
| **G1** | **Blocker** | **Fresh clone is broken.** `eval/baselines.py` uses `Optional` without importing it (line 125), so `import eval` fails, 4 test modules fail to collect, CI would be red and the benchmark cannot run. | `NameError: name 'Optional' is not defined`; 4 collection errors | Stage 1 |
| **G2** | **Blocker (honesty)** | **`fetch_weather.py` crashes** (`NameError: name 'Tuple' is not defined`), yet README/SOURCES say "Live fetched Open-Meteo API series". The claim is unsupported until the script runs and records provenance. | script run, `validate.py` fails on `weather_delhi.parquet` | Stage 2 |
| **G3** | High | **Dependencies/tests not reproducible.** `pyarrow` (a parquet engine) is not declared, so every fetch script fails on a clean machine; `data/processed/` is not in the repo, and `tests/test_dataset_grounding.py` fails until you generate it; CI never generates it. | `Import fastparquet failed`; 5 failures before data generation | Stage 1 |
| **G4** | High | **Deployed stack vs new code mismatch.** `FEATURE_DIM` changed **121 → 135**, the contracts changed (`context` field added), and `LinTS.load_state` has no dimension guard. The model already stored in the live `ModelState` table is 121-dimensional and will conflict with the new code. | `features.py:178`, `contracts.py` diff | Stage 4 |
| **G5** | High | **B4 cannot scale its attention.** Peak reduction saturates around 6% as budget grows; B3 (plain bandit) beats B4 on peak reduction at 0.22 vs 0.14 nudges/user/day. | `results/pareto.csv`, `summary.csv` | Stage 3 |
| **G6** | Medium | **Two benchmarks, two configs.** `summary.csv` (headline) and `pareto.csv` use different fleet size/duration (`pareto.py` defaults: 500 users, 96 steps; `run.py`: 2000 users, 1 day default) and give different B4 volumes (0.14 vs 0.33). Readers will not know which to trust. | `eval/pareto.py`, `eval/run.py` | Stage 3 |
| **G7** | Medium | **Most "datasets" are generators.** All of grid, sessions, stations, RCT, battery and VED are produced by numpy generators with seed 42 (RCT hard-codes the published summary numbers, e.g. a 0.49 mean reduction, with noise). Labels are now honest, but the build log still calls them "datasets implemented" and the bandit is **pretrained on the synthetic RCT**, so it mostly learns the assumed priors. | `fetch_rct.py`, `fetch_grid.py`, ... | Stage 2 |
| **G8** | Medium | **Build-log style claims** ("153/153 passing", "ALL CLAIMS VERIFIED") do not match a fresh clone. | G1, G3 | Stage 1 |
| **G9** | Medium | **Advanced items still unproven or missing**: no OR-Tools run, no Strands agent, no live Bedrock call, Cedar engine status unclear, no real data for stations/sessions. | greps in earlier rounds | Stage 5 |
| **G10** | Low | Max calibration error 0.2409 is high in sparse bins; stranded-trip metric is 0 for all policies including broadcast, so the safety claim is only as strong as that measurement's ability to fail. | `calibration.json`, `eval/metrics.py` | Stage 3 |
| **G11** | Low | **Live AWS evidence not captured** (README says deployed). | n/a | Stage 4 |
| **G12** | Low | Video and final submission not done. | n/a | Stage 6 |

---

## 3. Stage 1: Make the repo green from a fresh clone (about 1 hour)

**Owner:** Vishal. Branch `v/fresh-clone-green`.

1. **Fix imports.**
   - `eval/baselines.py`: `from typing import Any, Dict, List, Optional`.
   - `data/scripts/fetch_weather.py`: `from typing import Any, Dict, Tuple`.
2. **Declare dependencies.** Add `pyarrow>=14` (and `requests` only if you use it) to `pyproject.toml` dependencies. Keep Lambda deps separate in `build/lambda/requirements.txt` (numpy, pydantic, pyyaml only).
3. **Make data generation part of verification.** Add `scripts/prepare_data.sh`:
   ```bash
   set -euo pipefail
   for s in grid sessions stations rct battery ved weather; do python data/scripts/fetch_$s.py; done
   python data/scripts/validate.py
   ```
   Update `.github/workflows/ci.yml`: install deps, run `bash scripts/prepare_data.sh` (weather falls back to synthetic when offline; see Stage 2), then `pytest -q` and `python scripts/check_claims.py`.
4. **One command to prove the repo works:** `scripts/verify_all.sh` = prepare data → `pytest -q` → `check_claims.py` → `python scripts/check_ownership.py` → `cd dashboard && npm ci && npm run build`.
5. **Add an import smoke test** (`tests/test_imports.py`) that imports every top-level package (`eval`, `twin`, `gridnudge`, `services`, `agent`) so a missing import can never reach a commit again.

**Acceptance:** on a fresh clone (new folder, new virtualenv), `bash scripts/verify_all.sh` ends green with the full suite passing. Update `docs/BUILD_LOG.md` with the real command output, not a claim.

---

## 4. Stage 2: Truth about data (about 1.5 to 2 hours)

**Owner:** Sneha (scripts and docs), Vishal (loader/provenance).

### 2.1 Weather: make "live fetched" true or remove the claim
- Fix the crash (Stage 1), run `python data/scripts/fetch_weather.py` on a machine with internet, confirm `is_synthetic: False` in the provenance JSON, and keep the file or its provenance in the results metadata.
- The script must **fall back to synthetic with a loud warning** when the API fails, and the run metadata must record which one was used.
- README/SOURCES: say "live Open-Meteo" **only** for runs whose provenance says so.

### 2.2 Relabel and add real downloads where cheap
Do these in order and stop at your time cap (about 90 minutes total):
1. **Harvard Dataverse workplace charging CSV** (no token, doi `10.7910/DVN/NFPQLW`): download by hand, put it in `data/raw/` (do not commit), extend `fetch_sessions.py` with `--source harvard` that reads it and writes the same parquet schema, with provenance `is_synthetic: False`.
2. **Grid-India hourly series** (Mendeley, doi `10.17632/y58jknpgs8`): download by hand, add `--source mendeley` to `fetch_grid.py`.
3. **openICPSR 202941** (registration required): if you can download it, add a real loader to `fetch_rct.py`; **otherwise leave it synthetic and label it exactly as README already does.**
- Anything not downloaded stays "Synthetic, shaped after X". Never name a real dataset in a build-log sentence as if it were used.

### 2.3 Pretraining disclosure and leakage check
- The bandit is pretrained from `rct_nudge_response.parquet`, which is generated from hard-coded published numbers. That is a **prior from the literature, not learning from data.** State this in the README.
- Add `tests/test_no_leakage.py`: assert that neither `fetch_rct.py` nor `pretrain.py` imports `twin.behavior_hidden` or reads `config/behavior_assumed.yaml` (the simulator's hidden truth), so the learner cannot "know" the answer.
- Report B4 **with and without** pretraining in `docs/engineering/POLICY_REPORT.md` so readers see the effect of the prior.

**Acceptance:** `validate.py` passes for all 7 datasets; every README/SOURCES "live/real" claim has a matching provenance file; `tests/test_no_leakage.py` passes.

---

## 5. Stage 3: Strengthen and clarify the core result (about 3 to 4 hours)

**Owner:** Vishal. This is the most valuable stage for how the project is judged.

### 3.1 One benchmark config
- Pick **one** config for all published numbers (suggest 2,000 users, 3 simulated days after a 1-day pretrain/warm-up, 5 final seeds) and use it for **both** `eval.run` and `eval.pareto`. Store it in `config/benchmark.yaml` and print it at the top of both outputs.
- README must state the config next to every table.

### 3.2 Find out why B4 plateaus (experiments, in this order; stop when you find it)
Run each on the small config with development seeds (>= 100), then confirm on final seeds.
1. **Count unused budget:** log per interval `eligible`, `positive_uplift`, `selected`. If most eligible users are dropped by the `uplift_mean <= 0` filter in `allocator.py`, the allocator is starving itself.
2. **Uplift calibration:** compare B4's estimated uplift with the twin's true uplift per user (the oracle exists in outcomes). If estimates are biased low, the bandit underestimates how many users are worth nudging.
3. **Exploration:** raise epsilon and `v` after warm-up for one run; if reduction rises, the bandit is under-exploring.
4. **Plan mix:** print the plan/frame distribution again (it was 78% `slow_charge` before). Confirm `delay` + `cost` dominate for price-sensitive users now.
5. **Ablations:** compare B4, B4a (delay only), B4b (no fatigue features), and Oracle. If Oracle also plateaus, the limit is the twin/behavior, not the learner.
6. **Fill the budget by value:** try ranking by `max(uplift_mean, 0) * shiftable_peak_kwh * grid_value` **and** allow lower-uplift candidates when budget remains and fatigue is low. Report whether peak reduction rises without raising opt-out.

### 3.3 Statistical comparison you can defend
- Add a matched-volume table: for B1, B2, B3, B4 at about 0.15, 0.30 and 0.50 nudges/user/day, report peak reduction, kWh per nudge, opt-out, with 95% CI over seeds, plus a paired test (same seeds) for B4 vs B2 and B4 vs B3.
- Report both: "B4 delivers the most energy per nudge" and "B4 saturates at X% peak reduction; broadcast reaches Y% at Z× the notifications and Nx the opt-out."

### 3.4 Safety measurement that can fail
- Add a test that forces an unsafe plan through (bypassing the veto) and asserts `stranded_attributable > 0` is detected. The metric must be shown capable of returning non-zero before "0 stranded trips" counts as evidence.
- Report max calibration error and the bins that cause it; show bin counts in the reliability plot.

### 3.5 Targets and what you may claim
| Result after 3.2 to 3.3 | Claim |
|---|---|
| B4 reaches B2-level peak reduction at fewer nudges, CI-separated | "Same peak reduction with N× fewer notifications" |
| B4 matches B2 at matched volume and has more kWh per nudge, but saturates lower | "Most efficient per nudge; best at low attention budgets; does not scale to broadcast-level reduction (here is why)" (current honest position) |
| B4 below B2 at matched volume | Lead with safety, calibration, auditability and fatigue; state the efficiency numbers precisely |

**Acceptance:** one config, one set of tables, matched-volume table with paired tests, safety-metric test, written `POLICY_REPORT.md` with diagnosis and ablations. No tuning on final seeds.

---

## 6. Stage 4: AWS: redeploy the new code and capture evidence (about 1 to 1.5 hours)

**Owner:** Vishal. Ask before any `sam deploy` / delete.

1. **Dimension safety.** In `LinTS.load_state` raise a clear error when `A.shape != (FEATURE_DIM, FEATURE_DIM)`; in the decide path catch it and **fall back to a fresh model + log a warning** (or fail-silent) so a stale model can never crash the stack. Add a unit test.
2. **Reset stale state.** Before/after deploying the new code, delete the existing `lints` item in `gridnudge-model-state-prod` (and clear old `UserState` items if their schema changed). Or bump the model id (`lints_v135`).
3. **Rebuild and redeploy:** `bash scripts/build_lambda.sh` (or `python scripts/build_lambda.py`) → `sam build` → `sam deploy`. Confirm the package imports in a clean env with only numpy/pydantic/pyyaml (the earlier check passed on the previous version; repeat it).
4. **Contract sync:** the `DecisionRecord` gained a `context` field; regenerate `contracts/*` and make sure the dashboard types and fixtures still validate.
5. **Smoke test and evidence:** `API=<url> python scripts/smoke_aws.py`; verify DynamoDB `model-state` `update_count` rises after outcomes; verify SQS drains; capture CloudWatch metrics; screenshots for the README.
6. **Bedrock:** keep `EnableBedrock=false` unless a live call works; README says which.
7. **Dashboard hosting:** Amplify (see runbook); test the `fs`-reading risk; keep replay as default.

**Acceptance:** smoke script passes against the **new** code; `update_count` increments; evidence screenshots saved; README AWS section matches reality.

---

## 7. Stage 5: Remaining advanced items (each time-boxed to about 90 minutes; only after Stages 1 to 4)

| Item | What to do | Acceptance |
|---|---|---|
| Real Cedar engine | `pip install cedarpy` (check Linux wheel), add parity test (engine vs Python evaluator) | parity test passes; README says which engine runs in Lambda |
| Strands agent | Wrap `agent/tools.py` as Strands tools in an `Agent` with Bedrock (check API); expose via `/copilot`; precompute answers for replay | 5 questions answered with decision-ID citations; schema validator rejects bad scenarios |
| Bedrock live | Enable model access, one verified live render with `source="llm"` | recorded decision with `verified=true` |
| OR-Tools allocator | Solve the per-interval selection exactly; report greedy-vs-optimal gap | gap table + test that both respect budget/caps |
| Chronos | Benchmark vs seasonal-naive on the (real, if downloaded) grid series; keep only if it wins | benchmark table and chart |
| Real station/session data | Harvard CSV and Grid-India as in Stage 2 | provenance `is_synthetic: False` for those files |

---

## 8. Stage 6: Docs, video, submission

- Regenerate replay/fixtures from the final results; `cd dashboard && npm run build`; confirm every number on screen traces to a file (`tests/test_no_demo_literals.py`, `check_claims.py`).
- README: one benchmark config per table, matched-volume table, Pareto plot, honest limitations (plateau, synthetic data, hidden-behavior assumptions), real vs simulated table that matches provenance files.
- `docs/DEMO_SCRIPT.md`: lead with what is true: safety veto, calibration, attention efficiency, the Pareto trade-off, honest limits. Do not say "comparable" or "half the nudges" unless the matched-volume table supports it.
- Record the video from replay at 1440×900; keep takes deterministic.
- Final checklist: `verify_all.sh` green on a fresh clone · AWS evidence captured · claims audited · video uploaded · portal form submitted before the deadline.

---

## 9. Ordered checklist

**Stage 1 (fresh clone green)**
- [ ] `Optional` import in `eval/baselines.py`; `Tuple` import in `fetch_weather.py`
- [ ] `pyarrow` declared; `prepare_data.sh`; CI generates data
- [ ] `tests/test_imports.py`; `verify_all.sh` green on a clean folder

**Stage 2 (data truth)**
- [ ] Weather script runs live and records provenance (or claim removed)
- [ ] Harvard sessions and Grid-India real loaders (stop at time cap)
- [ ] Leakage test; pretraining disclosed; with/without-pretrain comparison

**Stage 3 (core result)**
- [ ] One benchmark config for `run` and `pareto`
- [ ] Plateau diagnosis (6 experiments) and any fix
- [ ] Matched-volume table with paired tests
- [ ] Stranded-trip metric proven able to fail
- [ ] `POLICY_REPORT.md`

**Stage 4 (AWS)**
- [ ] Dimension guard in `load_state`; stale `ModelState` reset
- [ ] Rebuild, redeploy, smoke test, evidence screenshots
- [ ] Contracts and fixtures in sync

**Stage 5 (advanced, time-boxed)**
- [ ] Cedar engine parity · Strands · Bedrock live · OR-Tools gap · Chronos benchmark · real station/session data

**Stage 6 (submit)**
- [ ] Replay/fixtures regenerated · README/DEMO truthful · video · submission

---

## 10. Ready-to-paste prompt for your coding agent (Stages 1 and 4 dimension guard)

```text
Read AGENTS.md. Work on branch v/fresh-clone-green.
1. Fix `eval/baselines.py` (import Optional) and `data/scripts/fetch_weather.py` (import Tuple, Dict, Any).
2. Add pyarrow to pyproject dependencies. Create scripts/prepare_data.sh and scripts/verify_all.sh
   (prepare data -> pytest -q -> scripts/check_claims.py -> scripts/check_ownership.py -> dashboard npm ci + npm run build).
3. Update .github/workflows/ci.yml to run prepare_data.sh before pytest.
4. Add tests/test_imports.py importing eval, twin, gridnudge, services, agent.
5. In gridnudge/persuasion/lints.py make load_state raise ValueError when the stored A matrix shape is not
   (FEATURE_DIM, FEATURE_DIM); in the decide path catch it, log a warning and start a fresh bandit
   (or fail-silent). Add a unit test.
6. In a NEW empty folder with a NEW virtualenv, run `bash scripts/verify_all.sh` and paste the real
   output into docs/BUILD_LOG.md. Do not write "verified" unless you ran it. Ask me before any AWS command.
```
