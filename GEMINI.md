# GEMINI.md — GridNudge Antigravity Execution Protocol

> This file is the **execution playbook for Gemini/Antigravity**.
> `AGENTS.md` is the project constitution. If this file conflicts with `AGENTS.md`, `AGENTS.md` wins.
>
> Do not treat this as a generic coding project. GridNudge is a time-boxed hackathon system where reproducibility, safety, auditability and a working demo matter more than feature count.

---

# 1. FIRST ACTION — ORIENT YOURSELF

Before writing code:

1. Read `AGENTS.md` completely.
2. Read the relevant section of:
   - `docs/engineering/01_V2_CRITIQUE.md`
   - `docs/engineering/02_ANTIGRAVITY_GUIDANCE.md`
   - `docs/engineering/03_DATASETS.md`
   - `docs/engineering/GRIDNUDGE_MASTER_PLAN.md`
3. Inspect the existing repository.
4. Do not recreate files that already exist.
5. Determine the current phase from the repository state.
6. Work only on the requested phase.
7. Do not silently jump to an advanced phase.

If the user says "build GridNudge", do NOT interpret that as permission to implement the entire system in one pass.

Instead:

```text
inspect → plan → implement one phase → test → report
```

---

# 2. PROJECT IDENTITY

## Product

**GridNudge**

## Team

**VibeSync**

## Track

**Waste & Energy → EV Nudges**

## Core idea

GridNudge is a safety-gated, uplift-aware EV charging decision system.

It separates two questions:

```text
WHAT should the user do?
        ↓
planner + physics + forecasts + safety

SHOULD we spend attention persuading them?
        ↓
contextual bandit + uplift + allocator
```

This separation is mandatory.

Never collapse plan choice and persuasion into one flat AI action space.

---

# 3. THE GOLDEN ARCHITECTURE

Always preserve:

```text
DIGITAL TWIN
    ↓
PERCEPTION
    ↓
PLANNER
    ↓
SAFETY #1
    ↓
BANDIT / PERSUASION
    ↓
ALLOCATOR
    ↓
SAFETY #2
    ↓
LANGUAGE
    ↓
SIMULATED OUTCOME
    ↓
CAUSAL REWARD
    ↓
POLICY UPDATE
    ↓
EVALUATION
```

The implementation must not accidentally become:

```text
LLM → decide everything
```

or:

```text
bandit → unsafe plan
```

or:

```text
planner → send notification directly
```

---

# 4. HOW GEMINI MUST REASON ABOUT FEATURES

Every requested feature must answer these questions before implementation:

```text
1. What decision does this feature influence?
2. What data does it require?
3. Is that data real, proxy or synthetic?
4. Where does it sit in the architecture?
5. What is its input contract?
6. What is its output contract?
7. What safety invariant applies?
8. How will it be tested?
9. How will it affect DecisionRecord?
10. How will the demo prove it works?
```

If any answer is unknown, inspect the engineering docs before coding.

Do not invent an interface.

---

# 5. PHASE DISCIPLINE

## P0 — FOUNDATION

Implement only:

```text
repo layout
pyproject.toml
pytest
contracts.py
DecisionRecord
JSON schema
TypeScript types
fixtures
BUILD_LOG
CI
```

Do not:

```text
deploy AWS
implement Bedrock
implement Strands
build advanced forecasting
```

### P0 acceptance

```bash
pytest -q
```

must pass.

Fixtures must include:

```text
one safety veto
one silence / none decision
one normal nudge
```

---

# 6. P1 — DIGITAL TWIN + BASELINES

Build:

```text
twin/world.py
twin/users.py
twin/battery_truth.py
twin/stations.py
twin/grid.py
twin/events.py
twin/behavior_hidden.py
twin/runner.py
```

Simulation requirements:

```text
~2,000 EVs
15-minute timestep
seeded NumPy RNG
common random numbers
```

Events:

```text
heatwave
solar_drop
station_outage
tariff_change
```

Baselines:

```text
B0
B1
B2
```

First proof:

```text
baseline fleet load
vs
simple intervention fleet load
```

Must produce a visible evening peak.

### P1 acceptance

Same seed produces the same trajectory.

A heatwave changes the expected load pattern.

No hardcoded fake benchmark values.

---

# 7. P2 — LOCAL BRAIN

Build in this exact dependency order:

```text
journey
    ↓
planner
    ↓
safety
    ↓
bandit
    ↓
allocator
    ↓
pipeline
    ↓
evaluation
```

## Journey

Implement:

```text
physics-inspired energy model
Monte Carlo uncertainty
arrival SOC q10/q50/q90
P(arrival SOC >= reserve)
calibration
```

Do not call an uncalibrated probability "confidence".

---

## Planner

Candidate plan types:

```text
default
delay
relocate
slow_charge
top_up_now
```

Generate plan outcomes.

Then safety-filter.

Never let the bandit see unsafe plans.

---

## Safety

Implement both:

```text
Python invariant checks
Cedar policy check
```

Then:

```text
fail-silent wrapper
```

A critical failure means:

```text
no nudge
```

---

## Bandit

Implement Linear Thompson Sampling.

Action structure:

```text
none
```

or:

```text
plan × frame × timing
```

Frames:

```text
cost
green
battery_health
convenience
reassurance
```

Timing:

```text
at_plug_in
plus_30m
pre_peak
```

Must log:

```text
context
action
propensity
reward
exploration
```

The bandit should learn silence.

---

## Allocator

Core implementation:

```text
greedy
```

Constraints:

```text
budget
per-user cap
station capacity
grid capacity
timing
anti-herding
```

Do not optimize globally with OR-Tools until the greedy allocator is proven.

---

## Local closed-loop acceptance

The following must execute:

```text
twin state
→ decide_batch
→ selected nudge
→ simulator response
→ reward
→ posterior update
→ next decision
```

A demo should be able to show that behavior changes over repeated simulated rounds.

---

# 8. P3 — AWS IMPLEMENTATION

AWS must wrap the local pipeline, not replace it.

Preferred:

```text
API Gateway
    ↓
Lambda decide
    ↓
gridnudge.pipeline
    ↓
DynamoDB
```

Reward path:

```text
POST /outcomes
    ↓
SQS FIFO
    ↓
reward_update Lambda
    ↓
DynamoDB
    ↓
S3 logs
```

Model updates must have a single writer.

Use:

```text
ReservedConcurrentExecutions = 1
```

where required for the reward update Lambda.

---

## AWS command policy

Before executing:

```bash
sam deploy
aws ...
sam delete
aws cloudformation ...
```

STOP and ask for confirmation.

Safe build/validation commands can run automatically:

```bash
sam validate
sam build
pytest -q
ruff check .
```

Never expose credentials.

Never create expensive infrastructure casually.

---

# 9. P4 — DASHBOARD

Build against fixtures/mock API first.

Only connect AWS after the UI works.

Required components:

```text
FleetLoadChart
EventInjector
NudgeBudgetGauge
DecisionCard
ConfidenceRings
CalibrationPlot
MetricsTable
ReplayMode
```

## DecisionCard must show

At minimum:

```text
decision id
user/EV context
recommended plan
journey confidence
battery stress
grid stress
safety status
Cedar verdict
vetoed plans
persuasion frame
propensity
whether a nudge was sent
```

For a veto:

```text
SAFETY VETO
```

must be visually obvious.

Do not bury the safety story in a settings page.

---

# 10. P5 — PROOF / EVALUATION

Run at least 5 seeds for final comparison.

Never copy values from an earlier run into a new report.

Generate:

```text
results/summary.csv
results/plots/
results/replay/
```

Evaluate:

```text
peak load
shifted kWh
nudges per user
safety violations
stranded trips
cost effect
grid value
calibration
```

Include uncertainty/confidence intervals where appropriate.

The benchmark must compare against baselines under common random numbers.

---

# 11. ADVANCED FEATURES

Only implement after CORE is stable.

Order:

```text
1. Chronos vs seasonal-naive
2. Station queue forecast
3. relocate plan
4. Bedrock rendering
5. numeric verifier
6. Strands copilot
7. flexibility forecast
8. doubly robust OPE
9. misspecification stress test
10. OR-Tools allocator
11. Digital Test Drive
```

Never reorder this casually.

---

# 12. BEDROCK RULES

Bedrock is a language layer.

Input should be structured verified facts.

Example:

```json
{
  "frame": "cost",
  "start": "22:30",
  "cost_saving_inr": 38,
  "journey_confidence": 0.94
}
```

The model may phrase these facts.

It may not invent:

```text
₹50
98%
500 km
```

if those values are not in the payload.

After generation:

```text
LLM output
    ↓
numeric verifier
    ↓
approved → send
rejected → template fallback
```

If Bedrock fails:

```text
template
```

not:

```text
no safety
```

---

# 13. STRANDS RULES

Strands is advanced.

The copilot must be read-only with respect to decisions unless an explicit, tested action is defined.

Preferred tools:

```text
get_decision
get_metrics
explain_decision
```

The copilot must not:

```text
change safety thresholds
send a nudge
modify bandit parameters
override Cedar
```

It explains the system.

It does not control the system.

---

# 14. DECISION RECORD DISCIPLINE

If a feature affects the decision, it belongs in `DecisionRecord`.

Do not add:

```text
frontendOnlyState
hiddenDecisionMetadata
temporaryDecisionPayload
```

to bypass the contract.

When modifying the contract:

1. explain why,
2. update Pydantic model,
3. regenerate JSON Schema,
4. regenerate TS types,
5. update fixtures,
6. update tests,
7. verify dashboard,
8. document the change.

Never silently break frontend/backend compatibility.

---

# 15. DATA / MODEL HONESTY

Use the documented data hierarchy:

```text
real dataset
    ↓
real proxy
    ↓
calibrated synthetic
```

Do not claim:

```text
Indian EV users behave like X
```

unless the data actually supports it.

Known limitations must be visible.

Examples:

```text
nudge-response data is not Indian
station reliability is simulated
battery aging is primarily cell-level validation
```

The simulator is a controlled evaluation environment.

Do not present it as a real-world deployment trial.

---

# 16. MODEL SELECTION RULES

Do not train a deep model just because it sounds impressive.

### Prefer

```text
physics
queueing theory
calibration
zero-shot probabilistic forecasting
contextual bandits
optimization
```

### Avoid unless explicitly approved

```text
LSTM
GRU
TFT
GNN
MARL
deep RL
causal forests
battery XGBoost trained only on our simulator
```

If a model has no credible training/evaluation data, do not pretend synthetic self-generated labels make it validated.

---

# 17. SAFETY-CRITICAL CODING RULES

Never use assertions as the only production safety mechanism:

```python
assert journey_confidence >= threshold
```

Instead use explicit validation:

```python
if journey_confidence < threshold:
    return veto(...)
```

Every safety function should have tests for:

```text
normal
boundary
unsafe
missing data
NaN
exception
timeout/failure
```

Check numerical sanity:

```text
NaN
inf
negative probabilities
probability > 1
negative SOC
SOC > 1
negative power
negative wait
```

Treat malformed numerical data as unsafe.

---

# 18. FAIL-SILENT IMPLEMENTATION

Use an explicit result structure.

Conceptually:

```python
DecisionResult(
    should_nudge=False,
    fail_silent=True,
    reason="cedar_timeout",
)
```

Do not represent failure as:

```python
None
```

alone if that makes failure indistinguishable from a valid `none` decision.

The system needs to distinguish:

```text
valid none
```

from:

```text
system failed → silence
```

Both send no nudge, but they must be auditable separately.

---

# 19. OBSERVABILITY

Structured logs should capture:

```text
decision_id
sim_time
stage
duration_ms
success
failure_reason
safety_verdict
fail_silent
nudge_sent
propensity
reward
```

AWS metrics should include at least:

```text
veto_count
fail_silent_count
nudges_sent
```

Do not log sensitive user information unnecessarily.

---

# 20. CODE QUALITY

Prefer:

```text
small functions
pure functions
typed interfaces
dependency injection
deterministic tests
clear names
explicit configuration
```

Avoid:

```text
giant pipeline.py
global mutable state
hidden singleton models
magic numbers
duplicate safety thresholds
copy-pasted business logic
```

The AWS layer should be thin.

The core should remain testable without AWS.

---

# 21. CONFIGURATION

Do not scatter thresholds across source files.

Use:

```text
config/safety.yaml
config/sim.yaml
config/behavior_assumed.yaml
config/tariffs.yaml
```

Examples:

```text
journey_confidence_threshold
reserve_soc
nudge_budget
per_user_nudge_cap
station_capacity
feeder_capacity
exploration_rate
```

Every assumption must be documented.

---

# 22. DEPENDENCY DISCIPLINE

Before adding a package:

1. Check whether the standard library or existing dependency is sufficient.
2. Check whether the package works with Python 3.11.
3. Check Lambda packaging implications.
4. Check installation size.
5. Check license where relevant.
6. Check whether it is actually needed for CORE.

Do not add a 300 MB dependency for a feature that can be implemented in 60 lines.

---

# 23. TERMINAL EXECUTION POLICY

Run focused commands first.

Example:

```bash
pytest tests/test_safety.py -q
```

then:

```bash
pytest -q
```

then:

```bash
ruff check .
```

For frontend:

```bash
npm run lint
npm run build
```

Do not repeatedly run the entire project after every one-line change.

---

# 24. DEBUGGING POLICY

When a test fails:

1. Read the full error.
2. Identify the first root failure.
3. Inspect the relevant implementation.
4. Reproduce with the smallest command.
5. Fix the root cause.
6. Run the focused test.
7. Run related tests.
8. Run the full suite.
9. Inspect the diff.

Do not:

```text
disable the test
weaken the assertion
hardcode expected output
catch all exceptions
delete the failing feature
```

unless the documented architecture requires it.

---

# 25. WHEN YOU ARE BLOCKED

If blocked for approximately 15 minutes:

```text
STOP.
```

Then check the documented fallback.

Examples:

### Data blocked

Use:

```text
--synthetic
```

### Bedrock blocked

Use templates.

### Cedar blocked

Use documented fallback evaluator / Verified Permissions.

### AWS SQS blocked

Use synchronous reward processing if the kill rule has been triggered.

Do not spend an hour fighting a secondary feature while CORE is unfinished.

---

# 26. PARALLEL AGENTS

Parallelize only independent modules.

Good:

```text
Agent A → twin
Agent B → dashboard fixtures
Agent C → infrastructure skeleton
```

Bad:

```text
Agent A → contracts.py
Agent B → contracts.py
Agent C → DecisionRecord
```

The contract is a synchronization boundary.

Before launching parallel work:

```text
freeze interface
```

After parallel work:

```text
integrate
→ run tests
→ inspect diff
```

---

# 27. ANTIGRAVITY PROMPT TEMPLATE

When beginning a phase, use this internal structure:

```text
Read AGENTS.md and GEMINI.md.

Current phase:
<phase>

Goal:
<one sentence>

Allowed files:
<paths>

Do not modify:
<paths>

Dependencies already available:
<list>

Acceptance criteria:
<list>

Tests required:
<list>

Implementation:
1. Inspect current state.
2. Plan changes.
3. Implement only this phase.
4. Run focused tests.
5. Run relevant full tests.
6. Report changed files, tests and remaining risks.
```

Do not use vague prompts such as:

```text
"Make the project awesome."
"Build everything."
"Add advanced AI."
"Make it production ready."
```

---

# 28. ACCEPTANCE CHECKLIST BY PHASE

## P0

```text
[ ] contracts
[ ] schema
[ ] TS types
[ ] fixtures
[ ] tests
[ ] CI
```

## P1

```text
[ ] twin
[ ] seeded RNG
[ ] CRN
[ ] events
[ ] B0/B1/B2
[ ] load chart
```

## P2

```text
[ ] journey
[ ] calibration
[ ] planner
[ ] safety
[ ] LinTS
[ ] none
[ ] uplift
[ ] allocator
[ ] local loop
```

## P3

```text
[ ] SAM
[ ] /decide
[ ] /outcomes
[ ] DynamoDB
[ ] S3
[ ] SQS FIFO
[ ] reward update
```

## P4

```text
[ ] live/replay
[ ] event injector
[ ] decision card
[ ] veto visualization
[ ] confidence
[ ] calibration
[ ] metrics
```

## P5

```text
[ ] 5+ seeds
[ ] CIs
[ ] calibration
[ ] safety tests
[ ] summary.csv
[ ] replay
```

## P6

```text
[ ] advanced feature only if CORE remains green
```

---

# 29. DEMO-FIRST ENGINEERING

Every major feature must have a way to appear in the demo.

The demo must make these four things unmistakable:

## Beat 1 — Safety veto

```text
Delay charging
      ↓
Journey confidence becomes unsafe
      ↓
VETO
      ↓
No nudge
```

## Beat 2 — Learned silence

```text
User likely shifts anyway
      ↓
uplift ≈ 0
      ↓
none
```

## Beat 3 — Peak flattening

```text
Heatwave
    ↓
baseline peak rises
    ↓
GridNudge staggers safe interventions
    ↓
peak flattens
```

## Beat 4 — Calibrated uncertainty

Show:

```text
Journey Confidence
Battery stress
Charging/station confidence
Calibration plot
Flexibility forecast
```

All values must come from a real run.

---

# 30. FINAL VIDEO CONSTRAINT

Judges do not see a live demo.

Therefore:

```text
replay mode is a first-class deliverable.
```

The dashboard must be able to reproduce a deterministic sequence.

Prefer a recorded replay dataset:

```text
results/replay/timeline.json
```

over a live API dependency for the final video.

The video should survive:

```text
AWS outage
internet outage
API latency
model latency
```

---

# 31. JUDGE Q&A PREPARATION

Agents should preserve evidence for these questions:

### "Are you learning from your own simulator?"

Answer honestly:

```text
The learning loop is evaluated inside a controlled simulator.
Behavior priors are grounded where possible in public charging-session and randomized-trial data.
We hide the behavior model from the learner and run misspecification/shift tests.
```

### "Why not deep RL?"

Because:

```text
the decision is primarily single-step,
bandits are more sample-efficient,
bandits are auditable,
safety constraints are explicit.
```

### "What does 94% mean?"

It means:

```text
a calibrated probability evaluated against held-out simulated trips.
```

Do not claim real-world 94% accuracy.

### "Can the LLM hallucinate?"

Answer:

```text
The LLM receives verified structured facts.
A numeric verifier rejects unsupported numbers.
The system falls back to deterministic templates.
```

### "What if the AI fails?"

Answer:

```text
Fail-silent: no nudge is sent.
```

### "How do you prevent rebound peaks?"

Answer:

```text
The allocator respects capacity and staggers selected interventions.
```

---

# 32. FINAL REPORT FORMAT

After completing a phase, respond with:

```text
PHASE: P?

IMPLEMENTED:
- ...

FILES CHANGED:
- ...

TESTS:
- command
- result

EVIDENCE:
- generated result/file/metric

LIMITATIONS:
- ...

NEXT:
- ...
```

Do not claim success without test evidence.

---

# 33. THE MOST IMPORTANT RULE

If forced to choose between:

```text
10 flashy features
```

and:

```text
1 feature that works, is measured, safe and demonstrable
```

choose the second.

GridNudge wins by being a coherent decision system:

```text
PLAN
→ PERSUADE
→ LEARN
```

with:

```text
SAFETY
→ AUDITABILITY
→ CALIBRATION
→ EVALUATION
```

as first-class engineering properties.
