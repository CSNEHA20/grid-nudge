# AGENTS.md — GridNudge Agent Constitution

> **Project:** GridNudge  
> **Team:** VibeSync — Vishal + Sneha  
> **Hackathon:** Environmental Hacks — WeMakeDevs × AWS  
> **Track:** Waste & Energy → EV Nudges  
> **Build window:** Oct 8–11, 2026  
>
> This file is the **authoritative engineering constitution for every coding agent** working in this repository.
> Read it completely before making changes.
>
> Companion engineering references:
> - `docs/engineering/01_V2_CRITIQUE.md`
> - `docs/engineering/02_ANTIGRAVITY_GUIDANCE.md`
> - `docs/engineering/03_DATASETS.md`
> - `docs/engineering/GRIDNUDGE_MASTER_PLAN.md`

---

## 0. Mission

Build **GridNudge**, a safety-gated, uplift-aware EV charging decision system.

The system must:

1. Simulate an EV-energy environment through a digital twin.
2. Estimate calibrated journey confidence, battery stress, station wait, grid stress and green windows.
3. Generate feasible charging plans.
4. Remove unsafe plans **before** persuasion.
5. Use a contextual bandit with a first-class `none` action to decide whether and how to persuade.
6. Allocate a limited nudge budget while avoiding rebound peaks.
7. Apply a second safety verification before sending anything.
8. Use an LLM only for language generation, never for decisions.
9. Learn from simulated outcomes through a causal reward loop.
10. Run locally first, then deploy the decision path to AWS.
11. Produce auditable records and a judge-friendly dashboard.
12. Produce a reproducible 3-minute demo replay.

### Core thesis

> **Physics and forecasts decide what is safest and beneficial.  
> The causal bandit decides whether, to whom and how to persuade.  
> The digital twin provides the controlled environment for learning and evaluation.**

---

# 1. NON-NEGOTIABLE AGENT RULES

These rules override convenience, speed and agent assumptions.

### 1.1 Never invent numbers

Any number displayed in:

- UI
- README
- charts
- demo
- logs presented to judges
- submission text

must come from a logged run or an explicitly documented assumption.

Never fabricate benchmark results.

Never write:

> "GridNudge reduces peak demand by 18%"

unless the current repository contains a run that produced exactly that result.

If a value is simulated, label it:

> **Simulation**

If a value is assumed, label it:

> **Assumption**

If a value comes from an external dataset, record the source.

---

### 1.2 Safety is a constraint, never a reward term

A plan that violates a safety invariant must be removed **before** the bandit sees it.

The bandit must never be allowed to trade safety for reward.

Required order:

```text
candidate plans
    ↓
plan outcome prediction
    ↓
SAFETY FILTER #1
    ↓
only safe plans reach bandit
```

The final selected output must pass:

```text
SAFETY FILTER #2
```

If the second safety check fails:

```text
NO NUDGE
```

---

### 1.3 Fail silent

If any critical component:

- throws
- times out
- returns malformed output
- produces impossible values
- fails Cedar verification
- fails numeric verification
- fails final safety validation

then:

```text
send no nudge
log the failure
return a safe result
```

Never degrade into an unsafe recommendation.

---

### 1.4 The LLM never decides

The LLM may:

- phrase a message
- translate a message
- make wording more natural
- choose among already-approved wording variants

The LLM may NOT:

- choose a charging plan
- override safety
- calculate safety
- invent savings
- invent battery/range values
- choose whether a user is eligible
- change a numerical decision
- override Cedar
- override Python invariants

Decision-making belongs to deterministic/ML/optimization code.

---

### 1.5 One shared contract

`DecisionRecord` is the single contract between stages.

Do not create hidden side channels between:

- twin
- perception
- planner
- safety
- bandit
- allocator
- language
- outcome learning
- dashboard

If a new piece of information matters across stages, add it to the contract through the contract-change process.

---

### 1.6 No scope creep

Only implement:

- CORE
- then ADVANCED in the specified order

Anything else goes into:

```text
docs/FUTURE.md
```

Do not add:

- random AI agents
- unrelated dashboards
- mobile apps
- deep RL
- multi-agent RL
- GNNs
- LSTM/TFT training
- battery XGBoost trained on self-generated labels
- Kinesis
- always-on SageMaker endpoints
- payment systems
- real charger control

unless the project owner explicitly changes scope.

---

### 1.7 Test everything

A module is not "done" because code exists.

A module is done only when:

1. implementation exists,
2. tests exist,
3. tests pass,
4. the module works in the actual pipeline,
5. assumptions are documented,
6. no contract is silently broken.

---

### 1.8 Reproducibility

All randomness must originate from explicit seeded RNG streams.

Preferred:

```python
rng = np.random.default_rng(seed)
```

Do not use uncontrolled:

```python
np.random.*
random.*
```

for simulation decisions.

Baselines and GridNudge must use **common random numbers (CRN)** so comparisons are fair.

Same seed + same configuration must produce reproducible results.

---

### 1.9 Secrets

Never:

- hardcode AWS keys,
- commit `.env`,
- print secrets,
- put credentials in fixtures,
- embed tokens in source,
- expose credentials in frontend code.

Use:

- environment variables,
- AWS profiles,
- IAM roles,
- AWS Secrets Manager where appropriate.

---

### 1.10 AWS cost safety

Prefer:

- Lambda
- API Gateway
- DynamoDB on-demand
- S3
- SQS
- CloudWatch
- Amplify

Avoid always-on resources.

Do not create:

- NAT Gateway
- provisioned capacity without explicit reason
- always-on SageMaker endpoint
- expensive persistent compute

Set an AWS Budget alert before serious deployment work.

---

### 1.11 Local-first

The core Python package must run without AWS.

Architecture:

```text
gridnudge/
    pure decision logic
          ↑
          |
    InMemoryStore
          |
    local runner/tests

AWS Lambda
    same pipeline
          |
    DynamoStore
```

Do not duplicate decision logic inside Lambda handlers.

Lambda handlers are thin adapters.

---

### 1.12 Keep a build log

Update:

```text
docs/BUILD_LOG.md
```

after meaningful milestones.

Record:

- date/time
- phase
- files changed
- tests
- result
- known issue
- fallback used
- AWS action if any

---

# 2. PROJECT ARCHITECTURE — DO NOT BREAK THIS SPINE

```text
DIGITAL TWIN
    ↓
PERCEPTION
    ↓
PLANNER
    ↓
SAFETY #1
    ↓
PERSUASION / BANDIT
    ↓
ALLOCATOR
    ↓
SAFETY #2
    ↓
LANGUAGE
    ↓
NUDGE
    ↓
SIMULATED RESPONSE
    ↓
CAUSAL REWARD
    ↓
POLICY UPDATE
    ↓
EVALUATION
```

The conceptual architecture is:

### Layer 1 — Physical world

- EV users
- batteries
- trips
- stations
- queues
- grid
- solar
- tariffs
- events

### Layer 2 — Planner

Decides:

> What charging plan is feasible and beneficial?

Candidate plans:

```text
default
delay
relocate
slow_charge
top_up_now
```

### Layer 3 — Persuasion

Decides:

> Should we spend attention on this user?

Action:

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

### Layer 4 — Safety

Two checks:

```text
Python invariants + Cedar
```

### Layer 5 — Language

Preferred:

```text
template
```

Advanced:

```text
Amazon Bedrock
    ↓
numeric verifier
    ↓
template fallback
```

### Layer 6 — Learning

```text
simulated outcome
    ↓
causal reward
    ↓
bandit posterior update
    ↓
evaluation
```

---

# 3. CORE SCOPE

CORE must work before any advanced feature is attempted.

## 3.1 Digital twin

Implement a reproducible vectorized simulator with approximately:

```text
2,000 EVs
15-minute simulation interval
```

World includes:

- users
- user archetypes
- trips
- SOC
- battery
- charging behavior
- stations
- queues
- grid load
- solar
- tariffs
- events

Events:

```text
heatwave
solar_drop
station_outage
tariff_change
```

---

## 3.2 Perception

Required:

### Journey confidence

Output:

```text
P(arrival SOC >= reserve)
arrival SOC q10
arrival SOC q50
arrival SOC q90
```

Must be calibrated.

### Battery stress

Simple semi-empirical model.

Never claim absolute battery lifespan.

### Station intelligence

Estimate wait at the user's expected arrival time.

Do not only show "wait now".

### Grid intelligence

Estimate:

- grid stress
- green window
- expected load

---

## 3.3 Planner

Generate feasible plans.

Safety-sensitive plans must be filtered.

Planner responsibilities:

```text
enumerate
→ simulate/predict outcomes
→ score
→ safety filter
→ return safe plans
```

Planner does not decide messaging.

---

## 3.4 Contextual bandit

Use:

```text
Linear Thompson Sampling
```

with:

```text
none
```

as a first-class action.

Must support:

- contextual features
- propensity logging
- exploration
- fatigue state
- uplift estimate
- posterior updates
- holdout/control behavior

A user who would shift without a nudge should ideally receive:

```text
none
```

---

## 3.5 Allocator

Must respect:

- total nudge budget
- per-user cap
- station capacity
- grid capacity
- timing
- anti-herding / staggering

Do not create a new peak by moving everyone to the same "green" slot.

CORE allocator may be greedy.

OR-Tools is advanced.

---

## 3.6 Safety

Must include:

```text
Python invariants
Cedar policy
fail-silent wrapper
```

The canonical safety threshold for the core demo is:

```text
journey_confidence_lower_bound >= 0.90
```

Do not hardcode this in multiple files.

Put it in configuration.

---

## 3.7 Evaluation

Compare:

```text
B0 — uncontrolled/default behavior
B1 — simple rule-based shifting
B2 — safe planner without learned persuasion
B3 — bandit without allocator
B4 — full GridNudge
```

Use:

- common random numbers
- multiple seeds
- confidence intervals
- calibration metrics
- peak load
- shifted kWh
- nudges/user
- safety violations
- stranded trips attributable to nudges

---

# 4. ADVANCED SCOPE — STRICT ORDER

Only after CORE works.

Implement in this order:

```text
1. Chronos forecast vs seasonal-naive
2. Station queue forecast + relocate plan
3. Bedrock rendering + numeric verifier
4. Strands operator copilot
5. Flexibility Forecast
6. Doubly-robust OPE + misspecification stress test
7. OR-Tools allocator
8. Digital Test Drive
```

If an earlier item destabilizes CORE, stop and revert/fix before proceeding.

---

# 5. TECHNOLOGY CONTRACT

Use:

| Area | Technology |
|---|---|
| Backend | Python 3.11 |
| Numerics | NumPy |
| Data | pandas |
| Scientific | SciPy |
| ML | scikit-learn |
| Optional quantile model | LightGBM |
| Contracts | Pydantic v2 |
| Bandit | Own Linear Thompson Sampling implementation |
| Policy | AWS Cedar / Verified Permissions fallback |
| LLM | Amazon Bedrock |
| Agent | Strands Agents SDK — advanced |
| AWS IaC | AWS SAM |
| API | API Gateway |
| Compute | Lambda |
| State | DynamoDB |
| Logs | S3 |
| Reward queue | SQS FIFO |
| Frontend | Next.js App Router |
| Frontend language | TypeScript |
| Styling | Tailwind CSS |
| Charts | Recharts |
| Testing | pytest + Hypothesis |
| Formatting/lint | Ruff + Black |
| Environment | uv or venv |

Do not introduce another framework unless there is a documented reason.

---

# 6. REPOSITORY CONTRACT

Target structure:

```text
gridnudge/
├── AGENTS.md
├── GEMINI.md
├── README.md
├── pyproject.toml
├── CODEOWNERS
├── .gitignore
├── .githooks/
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── contracts/
│   ├── decision_record.schema.json
│   ├── api.openapi.yaml
│   └── ts/
│       └── decision-record.d.ts
│
├── config/
│   ├── sim.yaml
│   ├── safety.yaml
│   ├── behavior_assumed.yaml
│   └── tariffs.yaml
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── scripts/
│   ├── SOURCES.md
│   └── ASSUMPTIONS.md
│
├── fixtures/
│   ├── decisions.sample.json
│   ├── metrics.timeline.json
│   ├── evaluation.summary.json
│   ├── calibration.json
│   └── flexibility.json
│
├── gridnudge/
│   ├── contracts.py
│   ├── state.py
│   ├── pipeline.py
│   ├── planner.py
│   ├── allocator.py
│   ├── perception/
│   │   ├── journey.py
│   │   ├── battery.py
│   │   ├── station.py
│   │   ├── grid.py
│   │   └── flexibility.py
│   ├── persuasion/
│   │   ├── features.py
│   │   ├── lints.py
│   │   ├── fatigue.py
│   │   └── uplift.py
│   ├── safety/
│   │   ├── invariants.py
│   │   ├── cedar_check.py
│   │   ├── failsilent.py
│   │   └── cedar_policies/
│   └── language/
│       ├── templates.py
│       ├── render.py
│       └── verify.py
│
├── twin/
│   ├── world.py
│   ├── users.py
│   ├── battery_truth.py
│   ├── stations.py
│   ├── grid.py
│   ├── events.py
│   ├── behavior_hidden.py
│   └── runner.py
│
├── eval/
│   ├── baselines.py
│   ├── metrics.py
│   ├── calibration.py
│   ├── plots.py
│   ├── stress.py
│   └── make_fixtures.py
│
├── services/
│   ├── decide.py
│   ├── outcomes.py
│   ├── reward_update.py
│   ├── explain.py
│   └── metrics.py
│
├── infra/
│   └── template.yaml
│
├── dashboard/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── tests/
│
├── results/
│   ├── summary.csv
│   ├── replay/
│   └── plots/
│
└── docs/
    ├── BUILD_LOG.md
    ├── FUTURE.md
    └── engineering/
```

Do not create duplicate packages such as:

```text
backend/
server/
ml/
ai/
engine/
core/
```

unless explicitly approved.

---

# 7. DECISION RECORD IS THE SPINE

Every decision must be representable by a typed `DecisionRecord`.

Minimum conceptual structure:

```text
decision_id
sim_time
ev
perception
plans
plan_outcomes
safety
persuasion
allocation
language
outcome
```

The record must make the entire decision auditable.

Example conceptual flow:

```json
{
  "decision_id": "d_000123",
  "sim_time": "2026-10-10T18:45",
  "perception": {
    "journey": {
      "p_arrive_above_reserve": 0.94
    }
  },
  "plans": [],
  "safety": {
    "cedar": "ALLOW",
    "invariants_ok": true,
    "vetoed_plans": []
  },
  "persuasion": {
    "chosen_plan": "p1",
    "frame": "cost",
    "timing": "at_plug_in",
    "propensity": 0.17
  },
  "allocation": {
    "selected": true
  },
  "language": {
    "verified": true
  },
  "outcome": {
    "adopted": null,
    "reward": null
  }
}
```

Never make dashboard-specific shadow schemas.

---

# 8. DATA HONESTY

Real-world data is used to ground the simulation.

Known gaps must remain visible.

Important examples:

- Indian EV session-level behavior is not publicly available in the required form.
- Indian nudge-response experimental data is not available.
- Battery datasets are primarily cell-level laboratory data.
- Station reliability is assumed/simulated.

Use the documented hierarchy:

```text
REAL DATA
    ↓
REAL PROXY
    ↓
CALIBRATED SYNTHETIC
```

Every synthetic/assumed parameter goes into:

```text
data/ASSUMPTIONS.md
```

Every external source goes into:

```text
data/SOURCES.md
```

Never describe simulated behavior as observed Indian user behavior.

---

# 9. REQUIRED SAFETY INVARIANTS

At minimum:

### Journey safety

No chosen plan may violate the configured lower-bound journey threshold.

### Battery sanity

Reject:

- SOC < 0
- SOC > 1
- impossible energy transitions
- negative battery capacity
- impossible charging power

### Station sanity

Reject:

- negative wait
- capacity below zero
- impossible connector allocation

### Grid sanity

Reject:

- allocation beyond configured capacity
- accidental rebound peak where capacity is feasible

### Language sanity

Every numeric claim in generated text must be traceable to the structured facts payload.

Forbidden claims include:

```text
guaranteed
your battery will last X years
proven on real users
saves X% in the real world
```

---

# 10. TEST REQUIREMENTS

Required tests:

```text
test_safety_veto
test_failsilent
test_verifier
test_crn
test_bandit_toy
test_allocator
test_no_new_peak
test_calibration
test_contracts
```

Expected assertions:

### `test_safety_veto`

No selected plan has a journey confidence lower bound below the configured threshold.

### `test_failsilent`

Injected failures in:

- perception
- Cedar
- verifier

produce:

```text
fail_silent = true
message = none
```

### `test_verifier`

Reject any number that does not exist in the approved facts payload.

### `test_crn`

Same seed produces identical baseline trajectories.

### `test_bandit_toy`

On a known synthetic uplift problem:

- regret decreases,
- `none` is preferred when uplift is non-positive.

### `test_allocator`

Must respect:

- total budget
- per-user cap
- station capacity
- grid capacity
- staggering

### `test_no_new_peak`

No allocated load exceeds configured capacity when a feasible allocation exists.

### `test_calibration`

Reliability error stays below the configured threshold on held-out simulation data.

### `test_contracts`

DecisionRecord:

- serializes,
- deserializes,
- validates against JSON Schema,
- matches generated TypeScript types.

---

# 11. PHASE EXECUTION POLICY

Agents must work **one phase at a time**.

Never ask an agent to build the entire project in one prompt.

## P0 — Foundation

Build:

- repository structure
- pyproject
- pytest
- contracts
- JSON schema
- TypeScript contract
- fixtures
- BUILD_LOG
- CI
- ownership checks

Do not touch AWS deployment.

Done when:

```bash
pytest -q
```

passes.

---

## P1 — Twin + baselines

Build:

- twin
- seeded RNG
- CRN
- events
- B0/B1/B2
- first fleet-load comparison

Done when:

- twin runs,
- heatwave works,
- baselines produce curves,
- reproducibility test passes.

---

## P2 — Local brain

Build:

- journey confidence
- calibration
- planner
- safety
- LinTS
- uplift
- fatigue
- allocator
- local pipeline
- B3/B4

Done when:

```text
decide → outcome → reward → update → improved decision
```

runs locally.

---

## P3 — AWS

Build:

- SAM
- API Gateway
- Lambda
- DynamoDB
- S3
- SQS FIFO
- reward update
- AWS runner

AWS commands require explicit human review.

---

## P4 — Dashboard

Build:

- fleet load chart
- event injector
- nudge budget
- decision card
- safety veto
- confidence rings
- calibration plot
- metrics
- replay mode

Mock API first.

Real API second.

---

## P5 — Proof

Build:

- multi-seed evaluation
- confidence intervals
- calibration plot
- stress tests
- Cedar in actual decision path
- final result files

---

## P6 — Advanced

Strict order:

```text
Chronos
→ station forecast
→ Bedrock + verifier
→ Strands
→ flexibility
→ DR-OPE + misspecification
→ OR-Tools
→ Test Drive
```

---

## FREEZE

After feature freeze:

Allowed:

- bug fixes
- reliability fixes
- copy fixes
- deployment fixes
- benchmark reruns
- video improvements

Not allowed:

- new architecture
- new major feature
- new model
- new dependency without necessity

---

# 12. KILL RULES

These rules protect the submission.

### If local closed loop is not working by the end of Day 1

Drop ALL advanced features.

### If AWS is broken midway through Day 2

Deploy:

```text
decide
DynamoDB
S3
```

and process rewards synchronously if required.

Do not waste the entire hackathon fighting infrastructure.

### If Bedrock blocks the build

Use templates.

The system remains valid.

### If Cedar packaging blocks the build

Use:

- documented Cedar policy files,
- a tested Python evaluator,
- or Amazon Verified Permissions.

State exactly what is actually running.

### If data download blocks the build

Use:

```text
--synthetic
```

fallback.

Never wait indefinitely for data.

### NEVER CUT

```text
baselines
safety veto
calibration plot
replay mode
```

---

# 13. AWS SAFETY POLICY

Agents must treat these as potentially destructive:

```bash
sam deploy
aws ...
sam delete
aws cloudformation delete-stack
aws dynamodb delete-table
aws s3 rb
```

Before executing any AWS-mutating command:

1. explain what it changes,
2. show the exact command,
3. request human confirmation.

Local commands may run automatically when safe.

Examples normally safe:

```bash
pytest -q
ruff check .
python -m ...
npm test
npm run build
sam validate
sam build
```

Still stop if a command has destructive side effects.

---

# 14. GIT / OWNERSHIP

Do not modify another person's owned module unless explicitly requested.

Conceptual ownership:

### Vishal

- core Python
- twin
- perception
- planner
- safety
- persuasion
- allocator
- AWS
- evaluation
- infrastructure

### Sneha

- dashboard
- data scripts
- message templates
- documentation
- README
- demo/video

### Shared

- contracts
- integration interfaces

Contract changes require explicit review.

Never silently modify the contract to make your own code easier.

---

# 15. AGENT WORKFLOW

Before coding:

```text
1. Read AGENTS.md
2. Read relevant engineering reference
3. Inspect current repository state
4. Identify exact files you will change
5. State implementation plan
6. Check dependencies/interfaces
7. Implement
8. Run focused tests
9. Run full relevant test suite
10. Inspect git diff
11. Update BUILD_LOG
12. Report files + tests + remaining risks
```

Do not:

```text
edit → hope → claim done
```

---

# 16. DEFINITION OF DONE

The submission is done only when all of these are true:

- [ ] local closed loop works
- [ ] baselines run
- [ ] GridNudge comparison is reproducible
- [ ] safety veto is demonstrable
- [ ] no nudge is emitted on critical failure
- [ ] journey confidence is calibrated
- [ ] `none` action exists
- [ ] allocator respects capacity
- [ ] AWS decision path works
- [ ] dashboard works
- [ ] replay mode works
- [ ] final results come from logged runs
- [ ] real vs simulated table exists
- [ ] assumptions register exists
- [ ] no secrets are committed
- [ ] 3-minute video is ready
- [ ] final repository is tagged for submission

---

# 17. JUDGE-CREDIBILITY RULE

The four moments that the demo must make obvious:

### 1. Safety veto

A cost-saving delay plan is blocked because journey confidence becomes unsafe.

### 2. Learned silence

A user who would shift anyway does not receive a nudge.

### 3. Peak flattening

A heatwave increases baseline peak demand; GridNudge staggers interventions and reduces the simulated peak.

### 4. Calibrated uncertainty

Show:

```text
Journey Confidence
Battery confidence
Charging confidence
Calibration plot
Flexibility forecast
```

with all numbers labeled according to their provenance.

---

# 18. FINAL COMMUNICATION STYLE FOR AGENTS

When reporting work, use:

```text
PHASE:
GOAL:
CHANGED:
TESTS:
RESULT:
KNOWN LIMITATIONS:
NEXT SAFE STEP:
```

Never say:

```text
"Everything is perfect."
"Production ready."
"Real-world proven."
```

unless the repository contains evidence supporting the statement.

The goal is not maximum code.

The goal is a **working, auditable, safe, reproducible hackathon system that survives skeptical judging.**
