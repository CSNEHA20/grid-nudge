# GridNudge v2: Skeptical Review and Final Recommended Architecture

**Team:** VibeSync | **Track:** Waste & Energy → EV Nudges | **Event:** Environmental Hacks (WeMakeDevs x AWS)

> **v2 thesis in one sentence:**
> *GridNudge is a safety-gated decision system for EV charging: physics and forecasts decide what the **safest beneficial plan** is, a causal bandit decides **whether, to whom, and how** to persuade, and everything is learned and audited in an EV-energy digital twin.*

---

## 0. Verdict up front (read this if nothing else)

Your 15-concept list is strong as a *vision*, but as a *build* it has four problems a skeptical judge will find in under five minutes:

1. **The AI is learning from our own simulator.** If we hand-write the user behavior model, the bandit "discovers" what we typed. This is the single biggest attack surface. v2 adds explicit defenses (§9).
2. **Several models have no data to train on** (LSTM/GRU/TFT, battery XGBoost, GNN). Training them on synthetic data we generated ourselves is circular. v2 replaces them with physics-based models, queueing theory, and a pretrained zero-shot forecaster.
3. **Concept #5 mixes two different decisions.** "Delay charging" and "cost-saving nudge" are not the same kind of action: one is *what to do*, the other is *how to talk about it*. v2 separates them. This is the biggest architectural fix.
4. **Too many "engines" with no spine.** 15 modules can look like 15 demos. v2 gives them one spine: a typed **Decision Record** that every component reads from and writes to.

**What v2 keeps:** journey confidence, battery stress, station prediction, grid forecasting, flexibility forecast, digital twin, bandit + uplift, Cedar safety, LLM-for-communication-only, ownership suitability (as a demo mode).

**What v2 cuts or demotes:** LSTM/GRU/TFT training, battery XGBoost, GNN, multi-agent RL, causal forests, separate "fatigue model" (folded into state), Kinesis, a standalone ownership product.

**What v2 adds:** Amazon's Chronos-2 for zero-shot probabilistic forecasting, conformal calibration of all confidence numbers, a plan-then-persuade two-layer design, OR-Tools for capacity-aware allocation, common-random-numbers evaluation, a simulator-misspecification stress test, and a "fail-silent" safety principle.

---

## 1. Critical review of the 15 concepts

| # | Concept | Verdict | Reasoning |
|---|---|---|---|
| 1 | Battery health / degradation twin | **KEEP (simplified), merge with #2** | Valuable as the *source of the "battery-health" reason* and a stress score. Do **not** claim lifespan. Use a semi-empirical physics model with Monte Carlo parameter uncertainty. |
| 2 | Physics + ML battery stress | **DEMOTE the ML part** | Physics-inspired stress features are solid. XGBoost on top needs real degradation data; training on our own synthetic labels is circular. Use XGBoost only if validated on a public cell dataset (Advanced). |
| 3 | Probabilistic journey confidence | **KEEP, make it the safety backbone** | Best "judge-visible" feature and the thing that makes safety quantitative. Must be *calibrated* (conformal / reliability plot), otherwise "94%" is meaningless. |
| 4 | Charging-station occupancy/queue | **KEEP, simplify** | Queueing model + forecast. It matters because nudges change arrivals, which changes queues, which is a real feedback loop and makes anti-herding genuine. |
| 5 | Contextual bandit | **KEEP as core, re-formulate** | Split *plan choice* from *persuasion choice* (see §3). 11 flat arms was a design flaw. |
| 6 | Causal uplift | **KEEP, but merge with #5** | A separate uplift model *and* a bandit duplicate each other. The bandit's reward model, with "none" as an arm and randomized exploration, *is* the uplift estimator. Use doubly-robust estimation for evaluation. Causal forests: Future. |
| 7 | Notification fatigue | **MERGE into #5** | Fatigue is a state feature and a reward penalty, not a separate model. Cleaner and more defensible. |
| 8 | Grid + renewable forecasting | **KEEP, replace the models** | TFT/LSTM need data we don't have. Use **Chronos-2** (Amazon, open-source, zero-shot, probabilistic, supports covariates) plus a seasonal-naive baseline to prove it adds value. |
| 9 | Fleet flexibility forecast | **KEEP, sharpen** | Define it as *physical flexibility envelope × behavioral adoption probability*. This is the headline "MW ± MW" number. |
| 10 | Full EV-energy digital twin | **KEEP, it is the foundation** | Vectorized NumPy, 2K to 5K EVs. Also the demo engine and safe test bed. |
| 11 | EV ownership suitability | **DEMOTE to a "Test Drive" mode** | It is a different product and could dilute the story. But it reuses the same engines and gives you the honesty differentiator ("an EV may not suit you"). Build it *after* the core loop works. |
| 12 | Confidence indicators | **KEEP as the UX layer, not a model** | It's the translation of #3/#4/#1 into 3 numbers. Calibration is what makes it credible. |
| 13 | EV swarm / collective intelligence | **REFRAME, cut MARL** | The valuable part is cohorts + anti-herding, which is a *congestion/allocation* problem, solved with optimization (OR-Tools), not multi-agent RL. Say this explicitly. |
| 14 | Safety / Cedar | **KEEP, tighten** | Cedar evaluates *attribute-based policies*; it does not compute probabilities. Compute numbers in code, pass them as attributes. Add a code-level invariant check and **fail-silent** default. |
| 15 | LLM + agentic | **KEEP, constrain** | Add a **numeric verifier**: every number in LLM output must exist in the structured fact payload, else fall back to a template. |

**Dropped entirely:** Graph Neural Networks (future slide only), deep RL for the MVP (future slide), multi-agent RL.

---

## 2. The coherence mechanism: one Decision Record

The reason 15 modules feel like a pile is that they have no shared contract. v2's contract:

```jsonc
// DecisionRecord: created per (EV, decision moment); enriched by each stage; logged to S3 and DynamoDB
{
  "decision_id": "d_000123",
  "sim_time": "2026-10-10T18:45",
  "ev": { "soc": 0.41, "plugged": true, "next_trip": {"depart": "06:30", "km": 38} },

  "perception": {                       // all probabilistic, all calibrated
    "journey": { "p_arrive_above_reserve": 0.94, "arrival_soc_q10_q50_q90": [0.12, 0.19, 0.26] },
    "battery": { "stress_score": 0.62, "soh_delta_vs_default_pct": [-0.02, -0.01], "assumptions": "sim" },
    "station": { "eta_wait_min_q50_q90": [4, 11], "reliability": 0.97 },
    "grid":    { "stress_q50_q90": [0.71, 0.84], "green_window_start": "11:00" }
  },

  "plans": [                            // feasible charging plans, generated by planner
    { "id": "p0", "type": "default",         "start": "now",   "kw": 11, "where": "home" },
    { "id": "p1", "type": "delay",           "start": "22:30", "kw": 11, "where": "home" },
    { "id": "p2", "type": "relocate",        "start": "now",   "kw": 50, "where": "station_7" },
    { "id": "p3", "type": "slow_charge",     "start": "now",   "kw": 7,  "where": "home" }
  ],
  "plan_outcomes": { "p1": { "cost_inr": -38, "journey_conf_lb": 0.91, "grid_value": 0.8, "battery_stress": -0.1 } },

  "safety": { "cedar": "ALLOW", "invariants_ok": true, "vetoed_plans": ["p3: journey_conf_lb 0.82 < 0.90"] },

  "persuasion": { "chosen_plan": "p1", "frame": "cost", "timing": "at_plug_in",
                  "uplift_mean": 0.21, "uplift_p10": 0.04, "propensity": 0.17, "explore": false },

  "allocation": { "selected": true, "budget_shadow_price": 0.3, "slot": "22:30-23:00" },

  "language": { "message": "…", "facts_used": ["cost_inr:38","start:22:30"], "verified": true },

  "outcome": { "adopted": null, "kwh_shifted": null, "reward": null }   // filled later by the twin
}
```

**Why this matters to judges:** every claim is auditable; the LLM copilot reads this; off-policy evaluation reads this; the dashboard "Why this decision?" card *is* this. It's the difference between "15 features" and "one system."

---

## 3. The re-engineered core: Plan → Persuade → Learn

Your original loop put battery, range, grid, behavior and bandit in one chain. The cleaner structure separates **what is best** from **what to say**:

```
LAYER 1: PHYSICAL WORLD MODEL  (what is true, with uncertainty)
   EV/battery twin · journey energy model · station queue model · grid/renewable forecast
                                │
LAYER 2: PLANNER  (what is the best FEASIBLE action?)
   enumerate charging plans (when / where / how fast) → predict outcomes → SAFETY VETO →
   multi-objective score (user cost, battery stress, journey confidence, grid value, wait)
                                │
LAYER 3: PERSUASION  (should we spend attention? on whom? how?)
   uplift-aware contextual bandit:  {none} ∪ {plan × frame × timing}
   fleet attention allocator under a budget, with capacity-aware anti-herding
                                │
LAYER 4: SAFETY GATE (Cedar + invariants) → LAYER 5: LANGUAGE (Bedrock + verifier)
                                │
                          USER / SIMULATOR RESPONSE
                                │
LAYER 6: LEARNING  causal reward → posterior update → off-policy evaluation → safer policy
```

**Key design principle:** *Safety acts twice.* Once **before** the bandit (it only ever sees safe plans) and once **after** (final verification of what is actually sent). The bandit can never trade safety for reward because unsafe options don't exist in its action set.

**Second principle: fail silent.** If any forecaster, Cedar call, or verifier fails or times out, the system sends **no nudge**. Silence is always safe.

---

## 4. Action space (re-formulated)

Two small decisions instead of one big flat list.

**Decision A: Plan (what to do)** produced by the planner, always safety-filtered
- `default` (do nothing different)
- `delay` charging to a green/off-peak window
- `relocate` to a better-predicted station
- `slow_charge` (reduce power: battery-friendly, grid-friendly)
- `top_up_now` (when journey confidence is at risk, a *protective* nudge that raises SOC)

**Decision B: Persuasion (how to present it)**
- `none` (first-class), or `frame ∈ {cost, green, battery_health, convenience/time, reassurance}` × `timing ∈ {at_plug_in, +30 min, pre_peak}`

> **Note:** "Range-confidence nudge" and "charging-reliability nudge" from your list become *reassurance framing* or *protective top-up plans*, not separate arms. They're information, not behavior changes. This makes the arms comparable in outcome (all measure behavior change) and keeps the action space ~40 combinations with shared features.

**Bandit:** Linear Thompson Sampling with action-context interaction features, so arms share statistical strength.

---

## 5. Reward and causal uplift

**Primary outcome (what we want to *cause*):** the user follows the recommended plan **and** it produces value.

```
r = w_g · grid_value(t) · ΔkWh_shifted_to_green_window
  + w_u · ΔINR_saved
  + w_b · (− Δbattery_stress)
  − w_w · Δwait_minutes
  − w_f · fatigue_cost(recent_nudges, repeated_frame)
  − w_o · opt_out
```

*Note: safety is a constraint, not a reward term.* A plan that fails the journey-confidence threshold is removed upstream; it can never be "worth it."

**Uplift:**
`uplift(x, a) = E[r | nudge a, x] − E[r | none, x]`, estimated from the bandit's posterior difference (with credible intervals).

- Maintain ~5-10% randomized exploration including "none" (and a small *global holdout* that never gets nudges) so uplift is identified, not assumed.
- Log `(context, action, propensity, reward)` for every decision.
- **Doubly-robust estimator** for offline evaluation:
  `ψ̂ = mean[ μ̂(x,a) + 1{A=a}·(Y − μ̂(x,a)) / π(a|x) ]`
- **Cross-check (Advanced):** a T-learner with LightGBM as an independent uplift estimator. If the bandit and T-learner disagree, investigate. That's a real sanity test, not a duplicate.

**Why this beats "clicks":** a user who would have shifted anyway has near-zero uplift, so GridNudge stays silent for them. This is the headline behavior: *"it learned when to shut up."*

**Delayed reward detail:** simulator time ≠ wall-clock time, so do **not** use SQS delay timers. The twin emits `outcome_window_closed` events at the right *simulated* time; SQS FIFO decouples and orders the reward-processing Lambda.

---

## 6. The perception engines (what to build, honestly)

### 6.1 Battery twin (physics-inspired, with uncertainty)
- Semi-empirical aging structure: **calendar aging** (grows with time, temperature, high-SOC dwell) + **cycle aging** (grows with throughput, C-rate, depth of discharge, temperature).
- Parameters from published literature ranges; sample parameter sets (Monte Carlo) to produce SoH projections as **ranges**, e.g. "Simulated SoH after 3 years: X–Y% under plan A vs plan B."
- Output used by the system: `battery_stress_score` and `ΔSoH between plans`. The point is the **relative** difference between charging plans, which is far more defensible than an absolute lifespan.
- **Never say** "your battery will last N years." Say "under these assumptions, plan B reduces simulated degradation by a modeled amount."
- *Advanced:* validate the aging structure against a public cell-aging dataset (e.g. NASA PCoE or Oxford) to show the shape is sane. Verify dataset access/licensing before relying on it.

### 6.2 Journey energy predictor (the safety backbone)
- Physics energy model: rolling resistance + aerodynamic drag + elevation + **HVAC load as a function of temperature** + driving-style factor + regeneration.
- Uncertainty from traffic, temperature, and driver variability, via Monte Carlo and/or **LightGBM quantile regression** on simulated trips.
- **Conformal prediction** wraps the quantiles so the stated coverage actually holds on held-out data.
- Output: `P(arrival SOC ≥ reserve)` and `[q10, q50, q90]` arrival SOC. **Journey Confidence = that probability.**
- **Calibration plot** ("when we say 90%, we are right ~90% of the time") is a must-show chart.

### 6.3 Station intelligence
- Per-station demand forecast (time features + recent arrivals) feeding an **M/M/c-style queueing model** for expected wait and availability at the user's **ETA**, not now.
- Reliability = outage probability from station history (simulated; clearly labeled).
- Key coupling: nudges change arrivals, so the queue model must be fed by the *planned* load. That is why anti-herding is real.

### 6.4 Grid + renewable forecast
- **Chronos-2** (Amazon, Apache-2.0 per its model card, ~120M params, zero-shot, quantile forecasts, supports covariates, runs on CPU or GPU). It removes the need to train LSTM/TFT on data we don't have. Chronos-Bolt (9M to 205M variants) is the lighter fallback. *Verify the current model names and install instructions on the model card before the build.*
- Baseline: seasonal-naive. **Show that Chronos beats it on held-out windows**; otherwise you're adding a model for nothing.
- Outputs: grid stress quantiles, solar/renewable-share quantiles → **Grid Stress Windows** and **Green Charging Windows**.
- Honesty: input series are synthetic-but-shaped (duck curve) unless you ground them in a real public series; label them. Chronos is *useful* even then because it forecasts our perturbed/event-injected series without retraining.

### 6.5 Fleet flexibility forecast (the "MW ± MW" number)
Two clean separate quantities:

1. **Physical flexibility envelope** per plugged-in EV: energy still needed, deadline (departure), max power, plug-in window → the kWh that *could* be moved without breaking the deadline.
2. **Behavioral adoption probability** per EV from the uplift model.

`Expected shiftable MW = Σ_i envelope_i × P(adopt | nudge, x_i)`, with uncertainty from Monte Carlo over adoption draws (and the grid forecast quantiles).

Label it: **"Simulation-based estimate."**

---

## 7. Fleet attention allocator and anti-herding

- Each interval: planner + bandit give each eligible EV a `(best plan, uplift distribution)`.
- **Allocation problem:** choose which EVs get nudged and into which time slots to maximize `Σ uplift × grid_value` subject to:
  - fleet attention budget (handled by a **Lagrange multiplier / shadow price** so budget tightness is explicit and visible),
  - per-user daily cap,
  - **feeder/station capacity per slot** (prevents the "everyone charges at 11 PM" rebound peak).
- Solve with **OR-Tools** (assignment/min-cost-flow or CP-SAT over EV→slot variables). Keep a greedy fallback. Small problem sizes (hundreds of candidates per interval) solve in milliseconds.
- **This is the legitimate version of "swarm intelligence":** thousands of EVs coordinated through shared signals and capacity-aware staggering. No MARL needed, and you can say why.

---

## 8. Safety, policy, language

### 8.1 Safety layer
**Two checks, two tools:**

| Check type | Tool | Examples |
|---|---|---|
| Numeric/physical | **Python invariants + unit tests** | `journey_conf_lower_bound ≥ 0.90`, `arrival_soc_q10 ≥ reserve`, `plan power ≤ vehicle/battery limit`, `no new slot above feeder capacity` |
| Policy/authorization | **AWS Cedar** | quiet hours, max nudges/day, opt-out, nudge-type allowed for this user, vehicle supports requested charging speed |

Cedar receives the *results* of numeric checks as attributes (`context.journey_ok = true`), so policies stay declarative and auditable. Policies are version-controlled and testable, and the dashboard shows the Cedar decision on each card.

**Fail-silent rule:** any error → no nudge. Include a test that proves it.

### 8.2 Language layer (Bedrock)
1. Input: **only** the verified `DecisionRecord` fields (plan, frame, numbers).
2. LLM paraphrases into a short message in the user's language/tone.
3. **Numeric verifier:** extract all numbers from the output; each must appear in the facts payload. If not, or if forbidden claims appear (guarantees, health/safety claims), **fall back to a template**.
4. Cache by `(plan, frame, tone, language, bucketed numbers)` to control cost.
5. Same pipeline narrates the "Why this decision?" card from the record. The LLM explains; it never decides.

### 8.3 Operator copilot (Strands)
Small toolset: `get_decision(decision_id)`, `explain_veto(decision_id)`, `compare_counterfactual(policy_a, policy_b)` (reads precomputed OPE results), `inject_scenario(text → structured event)`. Tools return structured data; answers cite decision IDs.

---

## 9. Defending against the "you trained on your own simulator" attack

This is the section that separates a strong entry from a flashy one.

1. **Ground distributions in real data where possible.** Candidate: a public real EV charging-session dataset (e.g. Caltech's ACN-Data) for arrival/duration/energy distributions. It's not Indian data, so say so. Verify access and terms.
2. **Hidden-model separation.** The simulator's true response function is hidden from the learner and implemented in a different module than the learner's features.
3. **Misspecification stress test.** Train/learn under behavior model A, evaluate under perturbed model B (shifted archetype mix, changed fatigue decay, different price sensitivity). Show GridNudge still beats baselines. Report the degradation honestly.
4. **Non-stationarity test.** Mid-run, change user behavior (e.g. a tariff change or a new archetype arrives). Show the discounted posterior recovers.
5. **Oracle comparison.** Because the simulator knows the true uplift, report **estimation error of uplift** and a **Qini/AUUC curve** against truth. A real deployment can't do this; a twin can, and it is a genuine advantage.
6. **Common random numbers.** All policies (broadcast, rule-based, non-personalized bandit, GridNudge) face the *identical* random streams. Differences are then due to policy, not luck. Run ≥ 5-10 seeds and show confidence intervals.
7. **Say it plainly in the submission:** "The twin is a test bed. Our contribution is the decision system and the evaluation methodology; behavior parameters are assumptions and are swappable with real data."

---

## 10. Optional "Digital Test Drive" (Ownership Confidence), built last

Reuses the same engines; adds only an input form and a 365-day run.

- Inputs: commute distance, weekend trips, home charging access (yes/no), typical climate, daily usage, tariff.
- Run the twin for a simulated year with Monte Carlo over traffic/temperature/behavior.
- Outputs: **Ownership Confidence** (fraction of simulated weeks with zero range-risk events and manageable cost), expected public-charging dependency, expected cost vs. current vehicle (user-entered), and simulated battery-stress profile.
- **Must include an honest "not suitable" path** (e.g. no home charging + long daily commute + poor local station reliability → low confidence, with the reasons).
- Label as decision support under assumptions, not advice.

If the core loop isn't finished by Day 2 night, **skip this entirely.** It is the first thing to cut.

---

## 11. AWS architecture (only what earns its place)

### 11.1 Mapping

| Component | AWS service | Honest justification |
|---|---|---|
| Decision service | **Lambda** (+ **API Gateway**) | Stateless scoring. **Batch endpoint:** the twin sends all eligible EVs per interval in one request (not one Lambda per EV; cheaper and faster). |
| Per-user state (archetype posterior, fatigue, habituation, caps) | **DynamoDB** | Small items, low-latency reads, TTL for history. |
| Bandit model parameters | **DynamoDB** (single item) or **S3** | Updated by a **single-writer Lambda** (reserved concurrency = 1) from batched rewards to avoid race conditions. State this design explicitly. |
| Event routing (scenario events, outcomes, nudge issued) | **EventBridge** | Decouples twin, decision, reward and dashboard. |
| Reward / outcome processing | **SQS (FIFO)** → Lambda | Ordered, replayable, backpressure-safe. |
| Decision log, OPE dataset, benchmark results | **S3** (Parquet/JSON) | Source of truth for off-policy evaluation and the dashboard replay. |
| Grid/range/station forecasters | **Lambda container image** (CPU; Chronos-Bolt or Chronos-2 if size/latency fit) **or** SageMaker endpoint | Forecasts are *per zone*, not per user, so volume is low. SageMaker is optional; avoid an always-on endpoint to protect credits (use serverless/batch inference or precompute forecasts per interval). |
| LLM message + explanation | **Amazon Bedrock** | Constrained paraphrase + decision-card narration. |
| Agentic copilot | **Strands Agents SDK** (open source) | Tool-using operator assistant. |
| Policy | **Cedar** (open source) | Declarative guardrails evaluated on every nudge. |
| Operator auth | **Cognito** | Standard, cheap. |
| Observability | **CloudWatch** | Latency, veto rate, nudges/user, fatigue distribution. Dashboards double as impact evidence. |
| Frontend | **Amplify Hosting / CloudFront** | Public URL for judges. |

### 11.2 Deliberately left out
- **Kinesis:** at hackathon event rates, EventBridge + SQS suffice. Mention Kinesis as the scale-out path.
- **SageMaker training pipelines, Feature Store, Ground Truth:** no real training workload justifies them. Optional: SageMaker Processing for batch OPE if you want an extra AWS integration and have credits.
- **Per-EV Lambdas, Step Functions:** unnecessary.

### 11.3 Where the twin runs
Python process (local, or a small EC2/Fargate task) → sends batched interval requests to the AWS decision API → receives allocations → applies responses → emits outcome events. The dashboard reads aggregate metrics from API Gateway/S3. Build a **replay mode** from S3 logs so the public URL works even when the live twin is off.

### 11.4 Open-source eligibility insurance
Strands + Cedar are AWS open-source tools; the decision path is also deployed on AWS. Both eligibility conditions are met. Chronos is an additional Amazon open-source model.

---

## 12. Build tiers (honest scope for the remaining time)

### CORE MVP, must run end-to-end
1. **Digital twin** (vectorized, 2K EVs): archetypes, trips, home charging, 3-5 stations with queues, grid + solar curve, ToU tariff, event injector (heatwave, solar drop, station outage, tariff change).
2. **Journey confidence** (physics energy model + quantile/conformal calibration) and its calibration plot.
3. **Planner**: 4-5 plan types, safety veto, outcome prediction (cost, journey confidence, grid value).
4. **Persuasion bandit**: LinTS with `none` arm, fatigue state, propensity logging, exploration + holdout.
5. **Allocator**: budget + anti-herding (greedy first; OR-Tools if time).
6. **Safety**: Python invariants + **Cedar** policies (4-6 rules) + fail-silent test.
7. **Baselines** on common random numbers: broadcast, rule-based, non-personalized bandit.
8. **AWS decision path**: Lambda + API Gateway + DynamoDB + S3 + EventBridge/SQS reward loop.
9. **Dashboard** (Next.js/TypeScript/Tailwind + Recharts/ECharts): fleet load curve (baseline vs GridNudge), nudges/user, uplift, "Inject event" button, decision card with veto and Cedar verdict.
10. **3-minute video.**

### ADVANCED LAYER, if time permits (in this order)
1. Grid forecasting with **Chronos** vs seasonal-naive (and the chart proving it helps).
2. **Battery stress model** + plan-level SoH delta ranges.
3. **Station queue forecast** + `relocate` plan.
4. **Bedrock** message rendering + numeric verifier; **Strands** copilot with 2-3 tools.
5. **Flexibility forecast** widget (MW ± MW).
6. Doubly-robust OPE panel; misspecification stress test chart.
7. **Digital Test Drive**.

### FUTURE / RESEARCH (slide only, honestly labeled)
Deep/offline RL for multi-step charging control · causal forests · GNN over feeder/station topology · federated or on-device personalization · V2G · OCPP/real charger integration · real utility demand-response programs · learned battery models validated on fleet telemetry.

### Kill rules
- **End of Day 1:** twin + bandit + baselines + first comparison chart must exist. If not, cut Advanced entirely.
- **Mid Day 2:** AWS decision path must respond to the twin. If not, deploy only the decision Lambda + DynamoDB + S3 and drop EventBridge/SQS (do reward processing synchronously).
- **Day 2 night:** feature freeze. Day 3 is benchmarking, polish and the video.
- **Never cut:** baselines, safety veto, calibration plot. They are your credibility.

---

## 13. Suggested two-person split

- **Vishal:** twin core, journey model + calibration, bandit/uplift, allocator, AWS decision path, Cedar.
- **Sneha:** dashboard, decision card UI, event-injection UX, Bedrock/Strands layer, README and submission copy, video storyboard.
- **Shared early:** agree the `DecisionRecord` JSON schema on Day 1 so frontend and backend can build in parallel. This one decision saves the most integration pain.

*Heads up:* the bottom line of your registration page screenshot is cut off ("You cannot…"). It may be a team-lock or edit restriction once submissions open. Read it fully on the portal, especially since you have 2 of 4 seats filled.

---

## 14. Demo storyboard (3 minutes, optimized for video since judges don't see it live)

| Time | Beat | What the judge sees |
|---|---|---|
| 0:00-0:20 | Problem | Evening peak + range anxiety + notification spam. One crisp stat framing (labeled assumption). |
| 0:20-0:45 | Idea | "Plan → Persuade → Learn" diagram. "ML decides what; LLM only says how." |
| 0:45-1:25 | Twin + event | Fleet map, load curve forming a peak. Click **Heatwave**. Broadcast baseline curve spikes. |
| 1:25-2:00 | GridNudge | Few staggered nudges; curve bends; nudges/user stays low. Highlight **silence** on users who'd shift anyway. |
| 2:00-2:25 | **The safety veto moment** | Open a decision card: a cost-saving "delay charging" nudge was **blocked** because that user's 6:30 AM trip confidence dropped below threshold. Cedar verdict and numbers visible. *This is the memorable beat.* |
| 2:25-2:45 | Confidence + forecast | Three confidence rings (Journey / Charging / Battery), calibration chart, **Flexibility Forecast** "X MW ± Y MW (simulated)". |
| 2:45-3:00 | Honesty + AWS | AWS map, results with CIs across seeds, misspecification test result, and (if built) Test Drive: "An EV may not suit this user." |

**Killer differentiators (the two sentences to repeat):**
1. *"It never nudges unless it can prove the journey is safe, and we show the veto."*
2. *"It spends human attention only where it causes behavior change, and it learned to stay silent."*

---

## 15. Questions a skeptical judge will ask (with defensible answers)

1. **"Isn't this just learning your own simulator?"** Partly, by construction. That's why behavior is hidden from the learner, evaluated under misspecification and shift, compared to an oracle, and distributions are grounded in real session data where possible. The contribution is the decision system plus evaluation method.
2. **"Why not deep RL?"** Single-step decisions with delayed reward; fatigue handled as state. Bandits are sample-efficient and auditable. Deep RL shown as future work with a clear trigger (strong long-horizon effects).
3. **"Why Chronos instead of training LSTM/TFT?"** No data to train on, and a zero-shot probabilistic model removes that circularity; we benchmark it against seasonal-naive.
4. **"How is '94%' meaningful?"** It's calibrated (conformal + reliability plot) against held-out simulated trips. Calibration in the twin validates the pipeline, not real-world accuracy.
5. **"Can the LLM hallucinate savings?"** It receives only verified facts, and a verifier rejects any number not in the payload, falling back to a template.
6. **"What if forecasting or policy services fail?"** Fail-silent: no nudge.
7. **"How do you avoid a rebound peak?"** Capacity-aware allocation with slot staggering; the queue model sees planned load.
8. **"What's real vs simulated?"** Say it up front: behavior, grid curves and station data are simulated (partly grounded in public data). Architecture, safety logic, learning loop and AWS deployment are real and working.
9. **"Does it scale?"** Batched stateless decisions, per-user state in DynamoDB, single-writer model updates, forecasts per zone. Kinesis/partitioning is the stated scale-out path.
10. **"Why include the EV suitability mode?"** Because the same engines can answer "should I even buy this?" honestly. It is a demo of the platform's honesty, not a separate product.

---

## 16. Repo layout and key interfaces

```
gridnudge/
├─ twin/              # users, archetypes, trips, stations, grid, tariffs, event injector, CRN seeds
├─ perception/        # journey (physics + conformal), battery stress, station queue, grid (Chronos), flexibility
├─ planner/           # plan generation, outcome prediction, multi-objective scoring
├─ persuasion/        # LinTS, fatigue state, uplift/DR estimators, exploration + holdout
├─ allocator/         # budget (Lagrangian), OR-Tools assignment, anti-herding
├─ safety/            # invariants + tests, Cedar policies + schema, fail-silent wrapper
├─ language/          # Bedrock prompts, numeric verifier, templates, cache
├─ agent/             # Strands copilot + tools
├─ services/          # Lambda handlers: decide, reward_update (single writer), explain
├─ infra/             # SAM/CDK: API GW, Lambda, DynamoDB, S3, EventBridge, SQS, Cognito, Amplify
├─ eval/              # baselines, seeds, calibration plots, Qini/AUUC, misspecification + shift tests
├─ dashboard/         # Next.js + TS + Tailwind + Recharts/ECharts
└─ docs/              # DecisionRecord schema, architecture diagram, assumptions register
```

**Assumptions register:** keep one table in the README listing every simulated or assumed parameter, its source or "assumed," and where to swap in real data. Judges trust teams that show their assumptions.

---

## 17. Final recommended architecture (summary)

**Name:** GridNudge, a safety-gated, uplift-aware EV charging decision system with a digital twin.

**Spine:** the **Decision Record** (typed, auditable, shared by every component).

**Flow:** Twin state → calibrated perception (journey, battery stress, station, grid) → safe plan set (planner + safety veto) → uplift-aware contextual bandit with a first-class "none" → budgeted, capacity-aware fleet allocation → Cedar + invariants → Bedrock paraphrase with numeric verifier → user/simulator response → causal reward → posterior update + doubly-robust OPE.

**Core models:** physics-based journey and battery models with calibrated uncertainty · queueing-based station model · Chronos zero-shot grid forecasting · Linear Thompson Sampling with uplift · OR-Tools allocation.

**Not in the build (by design):** LSTM/TFT training, battery XGBoost, GNN, MARL, causal forests, deep RL, Kinesis, always-on SageMaker endpoints.

**What makes it win:** it is a *system with a safety story and an evaluation story*, not a notification app, and it shows its own limits. The veto moment, the learned silence, the calibrated confidence rings and the flexibility forecast are the four things a judge will remember.
