# GridNudge: 3-Minute Demo Script

> **Hackathon:** Environmental Hacks — WeMakeDevs × AWS  
> **Track:** Waste & Energy → EV Nudges  
> **Team:** VibeSync — Vishal & Sneha  
> **Duration:** 180 seconds (3:00)  
> **Resolution:** 1440×900

---

## 00:00 – 00:40 | Beat 1: The Core Thesis ("ML Decides, LLM Phrases, Safety Enforces")

- **Screen:** `/live` (Live Twin Telemetry & Concentric Feeder Gauge)
- **Speaker:**
  > "Urban EV adoption is exploding in cities like Delhi. If left uncontrolled, thousands of electric vehicles plug in simultaneously between 6 PM and 10 PM, risking distribution transformer overloads.
  >
  > Simple solutions broadcast nudges to everyone, creating rebound peaks elsewhere and exhausting driver attention.
  >
  > Enter **GridNudge**: a safety-gated, uplift-aware EV charging decision system.
  > Our golden rule is simple: **Physics and forecasts decide what is safe and beneficial; contextual bandits decide whether and how to persuade; LLMs only phrase approved facts.**"

---

## 00:40 – 01:25 | Beat 2: Disturbance Injection & Fleet Peak Flattening

- **Screen:** Event Injector on `/live` (Trigger "Heatwave" scenario) → Fleet Load Modal
- **Speaker:**
  > "Let's watch GridNudge respond to a stress event. We inject a 45°C Delhi summer Heatwave.
  > Notice the uncontrolled baseline spike: surging AC demand combined with unmanaged EV charging breaches feeder capacity by up to 18%.
  >
  > Now look at GridNudge's response curve: rather than dumping all shifted demand into a single slot, our allocator staggers interventions across 15-minute intervals.
  >
  > Across multi-seed runs, GridNudge achieves **5.6% evening peak reduction** and shifts **3,131 kWh** with nearly **half the nudge volume** of broadcast baselines (0.53 vs 0.99 nudges per driver per day)."

---

## 01:25 – 02:10 | Beat 3: Safety Veto #1 & Learned Silence

- **Screen:** `/decisions` → Click on `d_002_safety_veto` (Decision Card View)
- **Speaker:**
  > "Every decision passes through an auditable 6-stage pipeline.
  >
  > Here is candidate `user_102`. A delay plan would save grid capacity, but Monte Carlo perception calculates their lower-bound journey confidence at 82%—violating our strict 90% threshold.
  >
  > Safety is a non-negotiable constraint, not a reward term. Safety Filter #1 and AWS Cedar policy instantly trigger a **HARD VETO**. No nudge is sent.
  >
  > Next, look at `user_103`. The bandit estimates their spontaneous shift probability is already high. Predicted causal uplift is near-zero. GridNudge chooses the first-class `none` action. We save attention budget for drivers who truly need a nudge."

---

## 02:10 – 02:45 | Beat 4: Calibrated Uncertainty & Operator Copilot

- **Screen:** `/evaluation` (Reliability Diagram & KPI Cards) → Drawer (`OperatorCopilotDrawer`)
- **Speaker:**
  > "On `/evaluation`, our claims are backed by rigorous statistical evidence.
  > The reliability diagram shows predicted confidence tracking empirical arrival SOC with an Expected Calibration Error under 2.5%.
  > Attributable stranded trips? Exactly **0**.
  >
  > In the drawer, our Read-Only Operator Copilot cites exact Decision IDs and Cedar policy verdicts without hallucinating numbers."

---

## 02:45 – 03:00 | Beat 5: Serverless Architecture & Conclusion

- **Screen:** Architecture map / `/about` (Real vs Simulated provenance)
- **Speaker:**
  > "The decision loop is powered by an AWS Serverless stack: API Gateway, Lambda, DynamoDB single-writer state stores, and Amazon S3 audit logs.
  >
  > GridNudge proves that sustainable grid stability doesn't require driver fatigue or compromised journeys. Thank you."
