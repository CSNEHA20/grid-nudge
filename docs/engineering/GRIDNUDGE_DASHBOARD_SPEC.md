# GridNudge Dashboard: Complete Screen and Information Spec (M12)

**Stack:** Next.js (App Router) · TypeScript · Tailwind CSS · Recharts (ECharts only if a chart needs it)
**Visual reference:** the glassmorphic canvas (Live, Decision card, Evaluation) at `https://claude.ai/artifact/GLLnx2GsHKMUKnL4C3ruvb`, built from your reference image.
**Companion docs:** `GRIDNUDGE_MASTER_PLAN.md` (M12/M13 and ownership), `GRIDNUDGE_ANTIGRAVITY_GUIDANCE.md` (DecisionRecord, API, §15 dashboard summary).
**Owner:** whoever builds `dashboard/` (per the master plan, only that path). This file tells you **what screens exist, what each one must show, where every number comes from, and what "done" looks like.**

> **Rule that overrides everything:** the dashboard never invents a number. Every value comes from a fixture, an API response, or a replay file, and every chart that shows twin output is labeled **"Simulation"**.

---

## 1. What the dashboard is for

The dashboard has two audiences, and the design serves both:

| Audience | What they need | Where it matters most |
|---|---|---|
| **Judges watching the 3-minute video** | Understand the system in seconds; see the safety veto, the flattened peak, and the proof | `/live`, `/decision/[id]`, `/evaluation` |
| **Operators / technical reviewers** | Inspect any decision, see what the fleet and grid are doing, verify the numbers | `/decisions`, `/twin`, `/flexibility`, `/about` |

**Questions the dashboard must answer, in order:**
1. *What is happening on the grid and in the fleet right now?* (`/live`)
2. *What did GridNudge do about it, and what did it cost the users in attention?* (`/live`)
3. *Why did it make this specific decision, and was it safe?* (`/decision/[id]`)
4. *Does it actually work better than the alternatives?* (`/evaluation`)
5. *How much flexible capacity does the fleet really offer?* (`/flexibility`)
6. *What is real and what is simulated?* (`/about`)

---

## 2. Design principles (apply to every screen)

1. **Honesty first.** A persistent "Simulation · sample data" badge in the top bar. Estimates always show uncertainty (±, intervals, CI whiskers). No guarantees, no "saves X in the real world."
2. **Safety is visible.** Vetoes, Cedar verdicts and fail-silent events are first-class, never hidden in logs.
3. **Explain, don't just display.** Every number has a tooltip definition (§7 glossary) and every decision has a "why."
4. **Calm premium, immersive.** Glass cards over a dusk mountain scene, big numbers, generous space, restrained motion. Information density is moderate on `/live` and higher on `/decisions`, `/evaluation`, `/twin`.
5. **Silence is a feature.** "No nudge" decisions are shown as positively as sends.
6. **Works offline.** Replay mode must work with no backend (bundled JSON). That is what the video and public URL rely on.
7. **Deterministic for video.** Replay playback is repeatable, no random jitter, no dev overlays.

---

## 3. Information architecture

| Route | Screen | Priority | Primary question |
|---|---|---|---|
| `/live` (default `/`) | **Mission Control** | **P0** | What's happening and what is GridNudge doing? |
| `/decision/[id]` | **Decision Card** | **P0** | Why this decision, was it safe? |
| `/evaluation` | **Proof / Evaluation** | **P0** | Does it beat the baselines? |
| `/about` | **Assumptions and Data** | **P0 (light)** | What is real vs simulated? |
| `/decisions` | **Decision Browser** | P1 | Which decisions happened, and which were blocked? |
| `/twin` | **Digital Twin Explorer** | P1 | What does the world (fleet, stations, grid, batteries) look like? |
| `/flexibility` | **Flexibility Forecast** | P1 | How many MW can we shift next peak? |
| `/testdrive` | **EV Test Drive (Ownership Confidence)** | P2 | Is an EV suitable for this person? |
| (drawer) | **Operator Copilot** | P2 | Ask "why" in plain language |

**Global shell (on every screen):** top bar (logo, tabs, simulation badge, run/mode selector, alerts), time controller, event injector entry, bottom dock (quick navigation), copilot launcher (P2).

---

## 4. Global shell modules

### 4.1 Top bar
| Element | Shows | Behavior |
|---|---|---|
| Logo (circle) | GridNudge mark | links to `/live` |
| Pill tabs | Live · Decisions · Evaluation · (Twin, Flexibility, Test Drive via the dock or overflow) | active tab filled; keyboard accessible |
| **Simulation badge** | "SIMULATION · SAMPLE DATA" in fixture mode; "SIMULATION · RUN <id>" in replay/live | always visible; cannot be hidden |
| Alerts bell | count of unread alerts (vetoes, fail-silent, budget exhausted, grid stress crossing) | opens an alerts popover; yellow dot when unread |

### 4.2 Run and mode selector (bottom-left chip, "Replay · Heatwave")
- **Modes:** `Replay` (bundled JSON, default), `Live` (polls the API), `Fixtures` (dev only; hidden in production build).
- **Run picker:** list of available runs (name, scenario, seeds, date). In Replay, selects among bundled replays.
- **Connection status** (Live mode): connected / reconnecting / offline, with last update time.

### 4.3 Time controller (Replay mode)
- Play / pause, speed (1×, 4×, 16×), scrubber over the simulated period with markers for **events** (heatwave injected, solar drop) and **notable decisions** (first veto, budget exhausted).
- Quick jumps: "Go to peak", "First veto", "Event start".
- Current sim time and date chips (as in the design: `18:42` and `Sat, 10 Oct`; the date shown is the **simulated** date).
- Keyboard: space = play/pause, ← / → = step one interval (15 min), `[` `]` = previous/next marker.

### 4.4 Event injector (ring of round buttons on `/live`; also reachable from the time controller)
| Event | Parameters shown in a confirm popover | Visible effect |
|---|---|---|
| **Heatwave** | start time, intensity (baseline load multiplier, temperature offset) | base load rises; baseline curve spikes; ripple animation from the center ring |
| **Solar drop** | window, drop % | green window shrinks; stress rises midday |
| **Station outage** | station(s), duration | affected stations turn grey on `/twin`; queue/wait rise |
| **Tariff change** | slot shift or peak price multiplier | tariff strip changes; savings numbers change |
- **Live mode:** `POST /events`. **Replay mode:** switches to the pre-recorded scenario track (no network). Active event shown as a badge in the top bar with a "Clear" action.
- Buttons are real `<button>`s with `aria-label`s; the active event has the orange ring.

### 4.5 Alerts (popover)
Types: `VETO` (safety blocked a plan), `FAIL_SILENT` (a service failed, no nudge sent), `BUDGET` (attention budget exhausted), `STRESS` (feeder stress crossed a threshold), `EVENT` (event injected). Each row: time, type tag, one line, link to the decision or time marker.

### 4.6 Bottom dock
Round icon buttons: Insights (Evaluation), Schedule (time controller), **Dashboard** (center, larger, `/live`), Flexibility, Settings (About/assumptions, units, reduced motion). Plus: left chip = run/mode; right chip = "latest safety event" (e.g. "u_2310 vetoed · journey_conf_lb 0.82 < 0.90") linking to that decision.

---

## 5. Screen specifications

Each screen lists: **purpose, layout, modules (panels), data, interactions, states, acceptance.** "Source" names the fixture/endpoint field (see §8).

---

### 5.1 `/live`: Mission Control (P0)

**Purpose:** show the grid event, GridNudge's response, and the cost in attention, in one glance. This is the hero of the video.

**Layout (desktop 1440×900):** 3 columns (left 340px, center fluid, right 340px), top bar, bottom dock row. Dusk scene background.

#### Module L1: Grid Ring (center hero)
- **Shows:** feeder load as % of capacity at the peak window. Outer ring = **broadcast baseline** (orange, with the overshoot beyond 100% highlighted); inner ring = **GridNudge** (yellow). Center: GridNudge peak load %, "of capacity at peak".
- **Chips under/over the ring:** "Feeder zone 7 · Delhi", "Broadcast 118%", "GridNudge 96%".
- **Toggle: Ring | Timeline.** The Timeline view is the full-width load chart over the day: baseline (orange), GridNudge (yellow), dashed capacity line, shaded peak window (18–22), event markers, solar share curve as a subtle area, tariff strip along the bottom, hover tooltip with all values at that time.
- **Source:** `metrics.timeline` (`load_baseline`, `load_gridnudge`, `capacity`, `events[]`), `metrics.peak` (`baseline_pct_of_capacity`, `gridnudge_pct_of_capacity`).
- **Interaction:** hover the ring arcs for exact values; click a chip to isolate that series; during replay the ring animates with sim time.

#### Module L2: Peak Reduction Orb (right column, top)
- **Shows:** **Peak reduction %** vs the selected reference policy (default Broadcast), "10 seeds" note, tooltip with definition.
- **Source:** `evaluation.summary` (headline row) in replay; `metrics.peak.reduction_pct` live.
- **Interaction:** reference policy dropdown (B0 No nudges, B1 Broadcast, B2 Rule-based, B3 Plain bandit).

#### Module L3: Attention Cost panel (right column)
- **Shows:** **Nudges per user per day** (GridNudge vs broadcast), and three round stats: **Vetoed** (count), **Silent** (% of eligible decisions where the best action was "none"), **Stranded** (trips stranded because of nudges; must be 0, highlighted yellow).
- **Source:** `metrics.counters` (`nudges_per_user_day`, `vetoed`, `silent_share`, `stranded_attributable`).
- **Interaction:** click "Vetoed" → `/decisions?status=vetoed`; click "Silent" → `/decisions?status=silent`.

#### Module L4: Event Injector (right column, bottom)
As §4.4: three round event buttons (Heatwave, Solar drop, Station outage) with "Inject event" label; Tariff change reachable via the time controller or an overflow.

#### Module L5: Fleet Load card (left column)
- **Shows:** current fleet charging load (MW) as a waveform of recent intervals, "peak window in 0h 18m" countdown.
- **Source:** `metrics.timeline` last N points; `metrics.next_peak.starts_in_min`.

#### Module L6: Confidence gauges (left column)
Two round gauges, fleet-level:
- **Journey confidence** = share of plugged-in EVs whose predicted journey confidence lower bound is at least 90%.
- **Charging confidence** = share of recommended charging plans with predicted wait at arrival of 10 minutes or less and station reliability above threshold.
- **Source:** `metrics.fleet.journey_ok_share`, `metrics.fleet.charging_ok_share`.
- **Tooltip:** definitions above and "calibrated on held-out simulated trips".

#### Module L7: Attention Budget bar (left column)
- **Shows:** budget used % (gradient bar with a bubble marker), **shadow price** (marginal value of the last selected nudge), budget rule ("8% of plugged-in EVs per interval").
- **Source:** `metrics.budget` (`used_pct`, `shadow_price`, `rule`).
- **State:** turns orange and raises a `BUDGET` alert at 100%.

#### Module L8: Time and date chips (top of left column)
Power/status chip, sim clock chip, simulated date chip. Replay clock is interactive (§4.3).

#### Module L9: Latest safety event chip (bottom right)
Latest veto or fail-silent: user id, reason in monospace, shield icon, links to the decision card.

#### Module L10: Live decision ticker (optional strip, P1)
Scrolling last 5 decisions: user id, plan + frame, status tag (SENT / SILENT / VETOED / FAIL-SILENT). Click → decision card.

**States:** loading (skeleton rings), no run selected (prompt to pick a replay), Live disconnected (banner + last known data), event active (badge + ripple).
**Acceptance:** with `fixtures/` only, the screen renders the ring, orb, counters, gauges, budget, event buttons and chips; clicking Heatwave in Replay mode switches to the heatwave track and the baseline overshoot appears; all numbers trace to a file; "Simulation" label visible.

---

### 5.2 `/decision/[id]`: Decision Card (P0)

**Purpose:** make one decision fully explainable, especially the **safety veto**. This is the memorable moment of the video.

**Layout:** header + six stage cards in two rows, plus a context strip and an outcome footer.

#### Header
Decision id, user id, sim time, status tag (SENT / SILENT / VETOED / FAIL-SILENT), headline sentence generated from the record (e.g. "Why the cheaper plan was blocked."), and an **Explain** button (P2; calls `/explain`; narrates only record fields).

#### Stage 1: Perception
| Field | Source |
|---|---|
| Journey confidence (calibrated), shown big, color by risk | `journey.p_arrive_above_reserve` |
| Arrival SOC q10 / q50 / q90 | `journey.arrival_soc_q10/q50/q90` |
| Battery stress score (0 to 1) and plan SoH delta range (simulated) | `battery.stress_score`, `battery.soh_delta_range_pct` |
| Station wait at ETA (q50 to q90) and reliability (assumed) | `station.eta_wait_min_q50/q90`, `station.reliability` |
| Grid stress (q50 to q90), green window | `grid.stress_q50/q90`, `grid.green_window_*` |
- **Mini chart:** SOC trajectory over the next day under the default plan vs the chosen plan, with the departure time and the reserve line marked (shows *why* delaying was risky).

#### Stage 2: Candidate plans
Table, one row per plan: plan id and type, start, power, location, cost (₹), journey confidence lower bound, grid value, battery stress delta, wait, and a status tag: SAFE, VETOED, CHOSEN. The vetoed row is highlighted in light blue with its reason inline.
- **Source:** `plans[]` (`outcomes.*`), `safety.vetoed[]`.

#### Stage 3: Safety gate (visually dominant, light-blue glow)
- **Veto reasons** in monospace (e.g. `p1: journey_conf_lb 0.82 < 0.90`).
- Checklist rows: invariants PASS/FAIL (per plan), **Cedar verdict** (ALLOW / DENY / ERROR), nudges today (e.g. 1 / 3), quiet hours (yes/no), opt-out (yes/no), vehicle supports plan (yes/no).
- A "Policy" link opens a plain-language list of the Cedar rules (from `/about`).
- **Source:** `safety.*` plus the Cedar context attributes included in the record.

#### Stage 4: Persuasion
Chosen plan, **frame** (cost, green, battery, convenience, reassurance, or none), timing, **uplift** (mean and p10 as a small range bar around zero), **propensity** (probability of this action), exploration flag. Short plain-language line: "Chosen because it has the highest expected extra behavior change among safe plans."
- **Source:** `persuasion.*`.

#### Stage 5: Allocation
Slot (staggered time), shadow price, selected yes/no, and why not selected if applicable (budget, cap, capacity).
- **Source:** `allocation.*`.

#### Stage 6: Message
Phone-style bubble with the final message; **source tag** (template or LLM) and **verified** check; list of facts used (numbers shown as chips) so reviewers can see nothing was invented.
- **Source:** `language.*`.

#### Outcome footer (when available)
Adopted yes/no, kWh shifted, savings (₹), opted out, reward. For replay runs where the outcome is known, also show **counterfactual uplift** ("what happens without a nudge").
- **Source:** `outcome.*`.

#### Related decisions strip
Same user's recent decisions (fatigue history): time, frame, status; fatigue score gauge.

**Variants:** **Silent** (shows "Why we stayed quiet": low uplift, high fatigue, or user would shift anyway), **Fail-silent** (shows the error and "safe default: no nudge"), **Sent** (full flow).
**Acceptance:** the sample veto fixture renders all six stages; the vetoed plan and reason are the most visually prominent element; every value maps to a record field; silent and fail-silent fixtures render without errors.

---

### 5.3 `/evaluation`: Proof (P0)

**Purpose:** prove GridNudge beats the baselines, safely and with calibrated confidence. This is where skeptical judges look.

**Layout:** scenario/seeds bar, four headline proof cards, then a two-column area of charts, then detail tables.

#### Controls
Scenario selector (Heatwave, Solar drop, Outage, Tariff change), seed set, reference policy, "Export CSV / PNG".

#### Module E1: Proof cards (top row)
- **Stranded trips caused by nudges** (target 0, highlighted yellow when 0)
- **Uplift per nudge** (kWh caused per nudge)
- **Calibration error** (expected calibration error, %)
- **Uplift estimation error** (estimator vs the twin's true uplift)
- **Source:** `evaluation.summary.headline`.

#### Module E2: Policy scoreboard (bars with CI whiskers)
Five policies: No nudges (B0), Broadcast (B1), Rule-based (B2), Plain bandit (B3), **GridNudge (B4)**. Metric switcher: peak load reduction %, kWh shifted, nudges per user per day, opt-out rate, ₹ saved per participant. Bars show mean with 95% CI; GridNudge in yellow, baseline in orange, others steel blue.
- **Source:** `evaluation.policies[]` (`metric`, `mean`, `ci_low`, `ci_high`).

#### Module E3: Calibration reliability diagram
"When we say 90%, how often is it right?" Predicted vs observed frequency, diagonal reference, binned points with counts, interval coverage figure beneath.
- **Source:** `calibration.bins[]`, `calibration.coverage`.

#### Module E4: Learning curves
Regret vs time (GridNudge vs plain bandit), and uplift-estimation quality (Qini/AUUC curve vs oracle).
- **Source:** `evaluation.regret[]`, `evaluation.qini`.

#### Module E5: Safety panel
Vetoes by reason (bar), fail-silent count, and "stranded attributable to nudges: 0".
- **Source:** `evaluation.safety`.

#### Module E6: Stress tests (P1)
Misspecification (learn under behavior A, evaluated under B): degradation table. Non-stationarity: recovery curve after a mid-run tariff change. Sensitivity sweep: small multiples.
- **Source:** `evaluation.stress_tests`.

#### Module E7: Reproducibility card
Seeds used, run id, git commit hash, config hash, date, and "common random numbers: yes".
- **Source:** `evaluation.meta`.

**Acceptance:** scoreboard and calibration render from fixtures; GridNudge is visibly best on the headline metric; CI whiskers shown; stranded-trips card present; every metric has a tooltip definition.

---

### 5.4 `/about`: Assumptions and Data (P0 light)

**Purpose:** build trust by stating what is real and what is simulated.

**Modules:**
- **Real vs simulated table:** *Real:* architecture, safety logic, learning loop, AWS deployment, public datasets used for grounding. *Simulated/assumed:* user response behavior, station reliability, traffic noise, feeder capacity, battery aging parameters, tariff slots unless taken from an order.
- **Data sources list:** dataset name, what it was used for, license/citation (from `SOURCES.md`).
- **Assumptions register:** searchable table (parameter, value, source or "assumed", how to replace) from `ASSUMPTIONS.md`.
- **Safety policy in plain language:** the Cedar rules rendered as sentences (e.g. "A nudge is never sent if the journey confidence lower bound is below 90%.").
- **Architecture diagram:** the Plan → Persuade → Learn flow and the AWS map.
- **Build info:** version, commit, build date.
- **Source:** `assumptions.json`, `sources.json`, `policies.json` (static files).
**Acceptance:** every assumption listed in `ASSUMPTIONS.md` appears; real vs simulated table is explicit.

---

### 5.5 `/decisions`: Decision Browser (P1)

**Purpose:** find any decision, especially blocked and silent ones.
- **Filters:** status (Sent, Silent, Vetoed, Fail-silent), plan type, frame, time range, station, search by user id; saved filter chips.
- **Summary chips:** counts per status; share of decisions vetoed; mean uplift of sent nudges.
- **Table columns:** time, user id, status tag, chosen plan and frame, journey confidence lower bound, uplift (mean), propensity, slot, outcome (adopted/ignored/opt-out/unknown). Sortable; virtualized for large runs; click row → `/decision/[id]`.
- **Do not show the hidden behavior archetype truth.** The learner's *posterior* archetype may be shown as a labeled estimate.
- **Source:** `GET /decisions?run_id&status&...` (live) or `decisions.index.json` (replay).
- **States:** empty ("No decisions match these filters"), loading skeleton, pagination.

---

### 5.6 `/twin`: Digital Twin Explorer (P1)

**Purpose:** let people see the world GridNudge acts in: fleet, stations, grid and batteries.

**Layout:** four panels in a grid, sharing the time controller.

- **T1 Fleet panel:** counts by status (driving, plugged, charging, waiting, done); **flexible vs inflexible EVs** (physical envelope based, not behavior); cohort bars by hour of day; fleet size; headline "plugged-in now."
- **T2 Station map and list:** Delhi stations on a simple map/schematic (from the processed station list): occupancy, queue length, predicted wait, outage state; click a station → detail drawer (connectors, kW, wait forecast q50/q90, reliability *assumed*).
- **T3 Grid panel:** demand, solar share, tariff slot strip, **Grid Stress Windows** and **Green Charging Windows** highlighted; forecast bands with a toggle **Seasonal-naive | Chronos** (P2; only if built); event markers.
- **T4 Battery panel:** distribution of battery stress scores across the fleet; for a selected plan comparison, **simulated SoH delta range** with a permanent caption: "Relative difference under stated assumptions, not a lifespan prediction."
- **Source:** `twin.snapshot` (per interval): `fleet`, `stations[]`, `grid`, `battery.stress_hist`. Station geometry from `stations.json`.
- **Acceptance:** each panel renders from fixtures; no absolute battery lifespan claim appears anywhere.

---

### 5.7 `/flexibility`: Flexibility Forecast (P1, advanced)

**Purpose:** show how many MW of charging could be shifted in the next peak, with honest uncertainty.
- **F1 Forecast band:** time axis for the next peak, median line and 10 to 90% band, headline "4.2 MW ± 0.6" (values from data), label "Simulation-based estimate."
- **F2 Decomposition:** **physical flexibility envelope** (what is possible without breaking deadlines) vs **adoption-weighted** (what users are expected to do), side by side, so the audience sees both the physical and behavioral limits.
- **F3 Breakdown:** by hour and by cohort (flexible/inflexible, archetype posterior groups).
- **F4 What-if control:** slider for attention budget (e.g. 4% to 16%) that switches among **precomputed** results (no live recompute unless the backend supports it); shows expected shiftable MW and nudges per user.
- **Source:** `flexibility.json` (`envelope`, `adoption_weighted`, `band`, `by_hour`, `by_cohort`, `budget_sweep[]`).
- **Acceptance:** band and both decomposition views render; "Simulation" label present.

---

### 5.8 `/testdrive`: EV Test Drive / Ownership Confidence (P2)

**Purpose:** answer "should I even buy an EV?" honestly.
- **Inputs (form):** daily commute km, weekend trip frequency and length, home charging access (yes/no), climate/season, current vehicle monthly fuel cost (optional), tariff.
- **Outputs:** **Ownership Confidence** (share of simulated weeks with no range-risk event and manageable cost), weekly risk timeline (a year of weeks colored by risk), expected public-charging dependency, expected monthly energy cost vs the user-entered current cost, battery stress profile (relative), and **plain reasons** behind the score.
- **Honest negative path:** when confidence is low, show "An EV may not suit this use case right now" with the top reasons (e.g. no home charging, long commute, low local station reliability). This must exist.
- **Disclaimers:** decision support under stated assumptions, not advice, not a guarantee.
- **Source:** `POST /testdrive` (live) or `testdrive.samples.json` (replay with 3 samples: good fit, borderline, not suitable).
- **Acceptance:** all three sample profiles render, including the negative one.

---

### 5.9 Operator Copilot drawer (P2)

- **Launcher:** icon button in the shell; opens a right-side drawer.
- **Content:** chat with suggested questions ("Why did you nudge fewer people at 7 PM?", "Why was u_2310 blocked?", "Compare GridNudge with broadcast under the heatwave").
- **Answers** show citations as chips linking to decision ids; a collapsible "Tools used" list for transparency.
- **Scenario creation:** natural-language event ("heatwave plus an outage at station 4") is shown as a **structured preview** the user must confirm before it is injected.
- **Guardrails in UI:** if the copilot has no data, it says so; never shows a number without a source chip.
- **Source:** `POST /copilot` (Strands agent) or `copilot.samples.json` in replay.

---

## 6. Cross-cutting UX modules

### 6.1 Motion and immersion
- Page load: ring arcs draw in over about 1 s; numbers count up.
- Event injected: a soft ripple from the ring center; baseline overshoot pulses once.
- Scene: very slow background parallax (a few px) and floating bokeh bubbles; **disabled under `prefers-reduced-motion`**.
- Veto: the safety card glows once on entry.
- Never autoplay audio. No flashing above 3 Hz.

### 6.2 States (every data-driven module)
| State | Design |
|---|---|
| Loading | glass skeleton matching the final layout |
| Empty | short explanation + one action |
| Error | inline message, "Retry", and fallback to replay mode when Live fails |
| Stale (Live) | timestamp + subtle "stale" tag |
| Partial data | show what exists; missing fields show "n/a" with a tooltip, never a made-up value |

### 6.3 Responsiveness
Primary target **1440×900 desktop** (the video size). Support 1280 to 1920 wide. Below 1180px, collapse the side columns beneath the hero. Phone layout is out of scope; show a friendly "best viewed on desktop" note.

### 6.4 Accessibility
- Text contrast on glass cards at least 4.5:1 (verify against the scene; strengthen the card tint if needed).
- All icon buttons have `aria-label`s; charts have `role="img"` with a summary label and a data table fallback.
- Full keyboard navigation (tabs, dock, event buttons, time controller).
- Color is never the only signal: status tags carry text (SENT, SILENT, VETOED).

### 6.5 Performance
Bundle replay JSON under about 5 MB (downsample timelines to 15-minute points; paginate decisions); memoize chart data; poll Live at 1 to 2 s with backoff; lazy-load `/twin`, `/flexibility`, `/testdrive`.

### 6.6 Units and formats
Time in IST with simulated date labeled "sim"; power in MW (fleet) and kW (charger); energy in kWh; money in ₹ with no decimals for small amounts; percentages with one decimal for headline metrics; confidence as whole percent; uncertainty shown as `± value` or interval.

---

## 7. Metric glossary (use as tooltips; do not paraphrase loosely)

| Metric | Definition |
|---|---|
| **Peak load reduction %** | `(peak of reference policy − peak of GridNudge) / peak of reference`, measured over 18:00 to 22:00, mean over seeds, with 95% CI |
| **Feeder load % of capacity** | highest feeder load in the peak window divided by feeder capacity |
| **kWh shifted** | energy moved out of the peak window compared with the default plan |
| **Nudges per user per day** | nudges delivered divided by user-days |
| **Opt-out rate** | share of users who muted notifications during the run |
| **Attention budget used** | nudges delivered in the interval divided by the interval's budget |
| **Shadow price** | marginal value of the last nudge the budget allowed (how expensive attention is right now) |
| **Journey confidence** | calibrated probability that arrival SOC stays above the reserve for the next planned trip |
| **Fleet journey confidence** | share of plugged-in EVs whose journey-confidence lower bound is at least 90% |
| **Charging confidence** | share of recommended charging plans with predicted wait at arrival at or below 10 minutes and reliability above threshold |
| **Uplift** | expected extra benefit caused by the nudge: outcome with the nudge minus outcome with no nudge |
| **Uplift per nudge** | kWh caused per nudge sent (twin oracle and estimator both reported) |
| **Propensity** | probability that the policy chose this action in this context (logged for off-policy evaluation) |
| **Silent share** | share of eligible decisions where the best action was "no nudge" |
| **Stranded trips attributable to nudges** | trips where a nudge-driven plan left SOC below the reserve at departure; target 0 |
| **Calibration error** | gap between predicted confidence and observed frequency, averaged over bins |
| **Flexibility (MW ± MW)** | expected shiftable charging power in the next peak = sum over EVs of physical envelope × probability of adoption, with Monte Carlo uncertainty |
| **Ownership Confidence** | share of simulated weeks with no range-risk event and acceptable cost for the entered usage profile |

---

## 8. Data contract: where every element gets its data

Types come from `contracts/ts/decision-record.d.ts` (read-only). Everything below is read from `fixtures/` (dev), `public/replay/` (replay) or the API (live). Missing files are requested from the backend owner (see §11).

| File / endpoint | Used by | Key fields |
|---|---|---|
| `decisions.sample.json` / `GET /decision/{id}` | Decision Card | full `DecisionRecord` |
| `decisions.index.json` / `GET /decisions` | Decision Browser, ticker | id, time, user, status, plan, frame, journey lb, uplift mean, propensity, slot, outcome |
| `metrics.timeline.json` / `GET /metrics` | Live ring/timeline, waveform, counters | `t[]`, `load_baseline[]`, `load_gridnudge[]`, `capacity`, `solar_share[]`, `tariff[]`, `events[]`, `counters`, `fleet`, `budget`, `peak`, `next_peak` |
| `evaluation.summary.json` | Orb, Evaluation | `headline`, `policies[]`, `regret[]`, `qini`, `safety`, `stress_tests`, `meta` |
| `calibration.json` | Reliability diagram | `bins[{pred, obs, n}]`, `coverage` |
| `flexibility.json` | Flexibility | `band`, `envelope`, `adoption_weighted`, `by_hour`, `by_cohort`, `budget_sweep[]` |
| `twin.snapshot.json` (per interval or sampled) | Twin Explorer | `fleet`, `stations[]`, `grid`, `battery.stress_hist` |
| `stations.json` | Station map | id, lat, lon, charger type, kW, connectors |
| `events.json` | Event injector, time markers | scenario tracks with start/params |
| `assumptions.json`, `sources.json`, `policies.json` | About | register rows, dataset list, Cedar rules in plain text |
| `testdrive.samples.json` / `POST /testdrive` | Test Drive | inputs and result for 3 sample profiles |
| `copilot.samples.json` / `POST /copilot` | Copilot | Q&A with citations |

**Shape sketches (informational; the authoritative schema is in `contracts/`):**
```ts
type MetricsTimeline = {
  run_id: string; step_minutes: number;
  t: string[];                       // ISO sim times
  load_baseline: number[]; load_gridnudge: number[];   // MW
  capacity: number;                  // MW
  solar_share: number[]; tariff: ("low"|"mid"|"peak")[];
  events: { type: "heatwave"|"solar_drop"|"station_outage"|"tariff_change"; start: string; end?: string; params: Record<string, number|string> }[];
  peak: { baseline_pct_of_capacity: number; gridnudge_pct_of_capacity: number; reduction_pct: number };
  counters: { nudges_per_user_day: number; baseline_nudges_per_user_day: number; vetoed: number; silent_share: number; stranded_attributable: number; opt_out_rate: number };
  fleet: { plugged: number; charging: number; journey_ok_share: number; charging_ok_share: number };
  budget: { used_pct: number; shadow_price: number; rule: string };
  next_peak: { starts_in_min: number };
};
type PolicyMetric = { policy: "B0"|"B1"|"B2"|"B3"|"B4"; metric: string; mean: number; ci_low: number; ci_high: number };
```

---

## 9. Copy, labeling and honesty rules

- Persistent badge: **"Simulation · sample data"** (or run id). On any chart: small "Simulation" caption.
- **Allowed phrases:** "in simulation", "under our assumptions", "calibrated on held-out simulated trips", "relative difference between plans", "estimate".
- **Forbidden:** "guaranteed", "your battery will last…", "saves X% in the real world", "proven on real users", any lifespan number.
- Uncertain values always show uncertainty. If a value is missing, show "n/a" with a tooltip.
- Messages shown to users must come from `language.message` and display their **source** and **verified** state.
- The **hidden behavior parameters and true archetypes are never shown**, except the twin-oracle uplift on `/evaluation`, clearly labeled "Simulator ground truth".

---

## 10. Visual system (matches the canvas design)

**Typeface:** Outfit (Regular 400, Medium 500; 300 and 600 sparingly). Numbers use Outfit Medium with tight tracking.

**Color tokens**
| Token | Hex | Role |
|---|---|---|
| `--orange` | `#FF8524` | baseline/broadcast, peak, active event, alerts |
| `--yellow` | `#FFEE69` | GridNudge, success, key numbers |
| `--steel` | `#6583A8` | secondary series, rings, muted accents |
| `--navy` | `#203F57` | glass base, deep backgrounds |
| `--white` | `#FFFFFF` | text, chips, primary contrast |
| `--ice` | `#A9C4E4` (derived tint of steel) | safety / veto highlight |

**Glass recipe:** background navy at about 46% opacity, `backdrop-blur` about 18px, 1px white border at about 20%, soft dark shadow, radius 26 to 30px (pills fully rounded). Tailwind: `bg-[#203F57]/45 backdrop-blur-xl border border-white/20 rounded-[28px] shadow-xl`.

**Scene:** dusk gradient (navy → steel → warm orange at the horizon), layered mountain silhouettes, a glowing sun behind the right peak, a few translucent bokeh circles. A real background image can replace it later; keep a dark overlay so text contrast holds.

**Type scale:** hero numbers 64 to 84px; big stats 34 to 48px; card titles 20px; body 16 to 17px; captions 12 to 13px.

**Charts (Recharts):** thin gridlines at about 15% white, no chart borders, rounded line caps, series colors per the tokens, tooltips as glass cards, axis labels in 12px muted white.

**Component inventory (build once, reuse):** `GlassCard`, `PillTabs`, `RoundStat`, `GaugeRing`, `GridRing`, `WaveformBars`, `BudgetBar`, `EventButton`, `StatusTag`, `DecisionChip`, `Stepper`, `PlanRow`, `MessageBubble`, `CIBar`, `ReliabilityPlot`, `TimeController`, `Dock`, `ScenePanel`, `Tooltip`, `Skeleton`, `AlertsPopover`, `Drawer`.

**Dashboard folder layout**
```
dashboard/
├─ src/app/ live/ decision/[id]/ evaluation/ about/ decisions/ twin/ flexibility/ testdrive/ api/fixtures/
├─ src/components/ ui/ charts/ shell/ panels/
├─ src/lib/ data/ (fixture, replay, live adapters) format.ts glossary.ts
├─ src/types/ (generated, read-only)
└─ public/replay/ timeline.json decisions.index.json ...
```
Use a single data-adapter interface (`getMetrics()`, `getDecision(id)`, `getEvaluation()`, ...) with three implementations (fixtures, replay, live) so screens never know which mode they're in.

---

## 11. Build order, acceptance and requests to the backend owner

### Build order
1. **Shell:** tokens, scene, glass components, top bar, dock, mode/run selector, simulation badge, data adapters (fixtures first).
2. **`/live` (P0):** L1 ring, L2 orb, L3 counters, L4 events, L5 to L9 side modules. Timeline toggle.
3. **`/decision/[id]` (P0):** six stages, veto emphasis, silent/fail-silent variants.
4. **`/evaluation` (P0):** proof cards, scoreboard with CI, calibration plot, safety panel.
5. **`/about` (P0 light):** real vs simulated, sources, assumptions, policies.
6. **Time controller and event tracks** (replay mode), alerts.
7. **P1:** `/decisions`, `/twin`, `/flexibility`.
8. **P2:** `/testdrive`, Copilot drawer, stress-test panels, Chronos toggle.

### Global acceptance checklist
- [ ] Every P0 screen renders from fixtures with **no backend running**
- [ ] Switching to live data requires only an environment variable change
- [ ] "Simulation" labeling visible on every screen and chart
- [ ] No number on screen that is not traceable to a file or response
- [ ] Safety veto is the most prominent element of the decision card
- [ ] Contrast, keyboard navigation, and reduced-motion checks pass
- [ ] Replay is deterministic and recorded cleanly at 1440×900 (no dev overlays, no console errors)
- [ ] Glossary tooltips exist for every headline metric

### Video-readiness (record in this order)
`/live` baseline spike → inject Heatwave → GridNudge flattens → open the veto on `/decision/[id]` → `/evaluation` proof and calibration → (if built) `/flexibility` → `/about` honesty close.

### Requests to the backend owner (send as `REQUEST(dashboard→backend)`, don't edit their files)
1. Fixtures for every file in §8, including **three decision variants** (sent, silent/vetoed, fail-silent).
2. In `/metrics`: `fleet.journey_ok_share`, `fleet.charging_ok_share`, `budget.shadow_price`, `counters.silent_share`, `counters.stranded_attributable`, `next_peak.starts_in_min`.
3. A decisions index file/endpoint with filter-friendly fields (§5.5).
4. `twin.snapshot`, `stations.json`, `events.json` for `/twin` and the time controller markers.
5. Replay bundle in `results/replay/` with the files listed in §8 (under about 5 MB).
6. Confirmation of event parameter schemas (names, ranges) for the injector popovers.
