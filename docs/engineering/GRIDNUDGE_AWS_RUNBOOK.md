# GridNudge: AWS Deployment Runbook

**Goal:** get the decision path running on AWS, prove it with a real run, and connect the dashboard.
**Why this matters:** the hackathon requires *at least one AWS open-source tool, or deployment on AWS*, to be prize-eligible. Right now the repo has `sam validate` only: no deployed stack.
**Based on:** analysis of `gridnudge-dev__1_.zip` (138 tests pass; `npm run build` passes; nothing deployed).

> **Safety rules for this runbook:** use your own AWS account with a budget alert first; never commit credentials; let an agent run `sam deploy`/`aws ... delete` only after you read the command and confirm.

---

## 0. Verified blockers (found by running the code, not guessing)

These would break or degrade the deployment. Fix them **before** `sam deploy` (Section 2).

| # | Blocker | Evidence | Fix |
|---|---|---|---|
| **B1** | **`DynamoStore` fails on real DynamoDB.** boto3 rejects Python floats. `put_users` raises `TypeError: Float types are not supported`; `put_model` fails the same way and is then **mis-reported as a `ConcurrencyError`**. Unit tests pass only because they use mocks that don't enforce this. | Reproduced with `moto`: `put_users FAILED: TypeError Float types are not supported`, `put_model FAILED: ConcurrencyError ... Float types are not supported` | Fix 1 (codec) |
| **B2** | **Bandit state is large for one DynamoDB item.** `LinTS.get_state()` stores a 121×121 matrix as nested lists (about 74 KB as JSON; as DynamoDB Numbers it grows further toward the 400 KB item limit once values become dense). | `LinTS(seed=1).get_state()` → 74,158 bytes JSON | Fix 2 (compact base64 float64, about 156 KB) |
| **B3** | **Errors are swallowed.** `DynamoStore.get_users` has `except Exception: pass`, so a failing read silently returns "no user state" and the system keeps running on empty state. | `gridnudge/state.py` | Fix 3 |
| **B4** | **Lambda would import scikit-learn.** `gridnudge/perception/journey.py` imports `sklearn.isotonic` at module load, which pulls in scipy and is too heavy for a normal zip Lambda. | `journey.py:10` | Fix 4 (numpy-only runtime calibration) |
| **B5** | **Packaging is not deployable as written.** Every function uses `CodeUri: ..` (the whole repo, including `dashboard/`), and there is no `requirements.txt`, so `sam build` has nothing to install (numpy, pydantic, pyyaml would be missing). | `infra/template.yaml`, repo root | Fix 5 (build script + CodeUri) |
| **B6** | **Bedrock is never called in the decision path.** `services/decide.py` hard-codes `render_llm=False`, so deploying Bedrock permissions changes nothing. | `services/decide.py:51` | Fix 6 (env switch) |
| **B7** | **Cedar is a Python fallback** unless `cedarpy` is installed (it is not in `pyproject.toml`). | `safety/cedar_check.py` | Optional Fix 7 |

**Already fine (checked):** `decide_batch` loads the bandit from the store when none is passed; the Lambda code only needs numpy, pydantic and pyyaml (no pandas, scipy, twin or eval imports) once B4 is fixed; the reward handler is wired as single-writer in the template (`ReservedConcurrentExecutions: 1`).

---

## 1. Prerequisites and account hygiene (30 minutes)

1. **Tools:** AWS CLI v2, AWS SAM CLI, Python 3.11, Docker (optional, for `sam build --use-container`).
2. **Profile:**
   ```bash
   aws configure --profile gridnudge        # access key, secret, default region, json
   export AWS_PROFILE=gridnudge             # PowerShell: $env:AWS_PROFILE="gridnudge"
   aws sts get-caller-identity              # confirms the account
   ```
3. **Budget alert first** (console: Billing → Budgets → Create budget → Cost budget → monthly **$20**, email alerts at 50% and 100%; repeat at **$50**). Claim the free-tier/hackathon credits from your event page.
4. **Pick one region** and keep everything in it. Choose it **after** checking where your Bedrock model is available (Section 3). Examples below use `ap-south-1`; replace as needed.
5. **No always-on resources:** this stack is all pay-per-request (Lambda, DynamoDB on-demand, SQS, S3, HTTP API). Do not add NAT gateways, SageMaker real-time endpoints or provisioned capacity.

---

## 2. Pre-deploy code fixes (about 2 to 3 hours)

Each fix lists the change and the test that proves it. Commit on a feature branch (`v/m10-aws-fixes`), keep tests green.

### Fix 1: DynamoDB float/Decimal codec (B1)
Create `gridnudge/state_codec.py`:
```python
"""Convert Python values to and from DynamoDB-safe types (floats <-> Decimal)."""
import math
from decimal import Decimal
from typing import Any


def to_dynamo(obj: Any) -> Any:
    if isinstance(obj, bool) or obj is None or isinstance(obj, (int, str)):
        return obj
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError(f"Non-finite float cannot be stored in DynamoDB: {obj}")
        return Decimal(repr(obj))
    if isinstance(obj, dict):
        return {str(k): to_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_dynamo(v) for v in obj]
    if isinstance(obj, bytes):
        return obj
    return obj


def from_dynamo(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)
    if isinstance(obj, dict):
        return {k: from_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [from_dynamo(v) for v in obj]
    return obj
```
In `DynamoStore`, wrap **every** write with `to_dynamo(...)` and **every** read with `from_dynamo(...)` (`put_users`, `put_model`, `put_decisions`, `get_users`, `get_model`, `get_decision`, `query_decisions_by_run`).

### Fix 2: Compact model storage (B2)
In `DynamoStore.put_model`, convert the large arrays to base64 before writing, and reverse on read:
```python
import base64
import numpy as np

def pack_model(state: dict) -> dict:
    s = dict(state)
    for key in ("A", "b"):
        arr = np.asarray(s.pop(key), dtype="<f8")
        s[f"{key}_b64"] = base64.b64encode(arr.tobytes()).decode("ascii")
        s[f"{key}_shape"] = list(arr.shape)
    return s

def unpack_model(item: dict) -> dict:
    s = dict(item)
    for key in ("A", "b"):
        if f"{key}_b64" in s:
            raw = base64.b64decode(s.pop(f"{key}_b64"))
            shape = tuple(int(x) for x in s.pop(f"{key}_shape"))
            s[key] = np.frombuffer(raw, dtype="<f8").reshape(shape).tolist()
    return s
```
Use `put_item(Item=to_dynamo(pack_model(model)) | {"model_id": ..., "version": ...})` and `unpack_model(from_dynamo(item))` in `get_model`. Size check: 121×121×8 bytes ≈ 117 KB raw, about 156 KB base64, under the 400 KB item limit. If the feature dimension grows later, move the blob to S3 and store its key in `ModelState`.

### Fix 3: Make failures loud and precise (B3)
- Remove `except Exception: pass` in `get_users`; log and re-raise (a missing user is `"Item" not in resp`, not an exception).
- In `put_model`, only treat **`ConditionalCheckFailedException`** as `ConcurrencyError`:
  ```python
  from botocore.exceptions import ClientError
  except ClientError as e:
      if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
          raise ConcurrencyError(...) from e
      raise
  ```

### Fix 4: numpy-only calibration at runtime (B4)
In `gridnudge/perception/journey.py`, remove the top-level sklearn import. Keep sklearn for **offline fitting only** and store the fitted knots:
```python
class JourneyCalibrator:
    def __init__(self):
        self._is_fitted = False
        self._knots_x = None
        self._knots_y = None
        self._default_x = np.array([0.0, 0.1, 0.3, 0.5, 0.7, 0.85, 0.90, 0.95, 1.0])
        self._default_y = np.array([0.0, 0.09, 0.28, 0.49, 0.70, 0.86, 0.90, 0.96, 1.0])

    def fit(self, predicted_probs, observed_outcomes):
        x = np.asarray(predicted_probs, dtype=float)
        y = np.asarray(observed_outcomes, dtype=float)
        if len(x) >= 10:
            from sklearn.isotonic import IsotonicRegression   # offline use only
            reg = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(x, y)
            self._knots_x = np.asarray(reg.X_thresholds_, dtype=float)
            self._knots_y = np.asarray(reg.y_thresholds_, dtype=float)
            self._is_fitted = True
        return self

    def calibrate(self, raw_prob: float) -> float:
        p = max(0.0, min(1.0, float(raw_prob)))
        if self._is_fitted:
            out = float(np.interp(p, self._knots_x, self._knots_y))
        else:
            out = float(np.interp(p, self._default_x, self._default_y))
        return max(0.0, min(1.0, out))
```
**Test:** existing calibration tests still pass; add one that imports `gridnudge.perception.journey` in a subprocess with `sklearn` blocked (`sys.modules["sklearn"] = None`) and checks `calibrate()` works. *(Decide whether the Lambda should use the default anchors or the fitted knots; if fitted, export the knots to `config/journey_calibration.json` from the benchmark and load them at import.)*

### Fix 5: Package only what Lambda needs (B5)
Create `scripts/build_lambda.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
rm -rf build/lambda && mkdir -p build/lambda/config
cp -r gridnudge services agent build/lambda/
cp config/safety.yaml build/lambda/config/
cat > build/lambda/requirements.txt <<'EOF'
numpy>=1.24
pydantic>=2.0
pyyaml>=6.0
EOF
find build/lambda -name "__pycache__" -type d -prune -exec rm -rf {} +
echo "Lambda package staged in build/lambda"
```
In `infra/template.yaml`, change every `CodeUri: ..` to `CodeUri: ../build/lambda/`. Run the script before every `sam build`. (`boto3` is already in the Lambda runtime. `config/safety.yaml` is read relative to the package, so it must sit in `config/` next to `gridnudge/`; the code resolves it as `<package root>/config/safety.yaml`.)

**If numpy fails to import in Lambda logs** (wheel/platform mismatch): rebuild with `sam build --use-container` (needs Docker) or attach the managed *AWS SDK for pandas* layer for your region instead of bundling numpy.

### Fix 6: Make Bedrock opt-in (B6)
In `services/decide.py` replace `render_llm=False` with:
```python
render_llm=os.environ.get("ENABLE_BEDROCK", "false").lower() == "true",
```
In `infra/template.yaml` add a parameter and env var (default off):
```yaml
Parameters:
  EnableBedrock:
    Type: String
    Default: "false"
    AllowedValues: ["true", "false"]
Globals:
  Function:
    Environment:
      Variables:
        ENABLE_BEDROCK: !Ref EnableBedrock
```
Keep the numeric verifier gate and template fallback as they are. Bedrock failures must never break `/decide` (the code already falls back; confirm with a test that forces a Bedrock exception).

### Fix 7 (optional): Real Cedar engine (B7)
Either add `cedarpy` to `build/lambda/requirements.txt` (check it provides a Linux wheel for your Lambda architecture), or move policy checks to Amazon Verified Permissions. Add the **parity test** (Cedar engine vs Python evaluator agree on a grid of contexts) and keep the Python evaluator as the documented fallback. The README must say exactly which engine ran in the deployed stack (`get_cedar_engine_status()`).

### Add API protection (small, recommended)
The HTTP API has no authorizer and `AllowOrigins: '*'`. For a demo, at least add throttling:
```yaml
  Api:
    Type: AWS::Serverless::HttpApi
    Properties:
      StageName: !Ref StageName
      DefaultRouteSettings:
        ThrottlingBurstLimit: 20
        ThrottlingRateLimit: 10
```
Optionally require a shared secret header (`x-api-key` value from an environment variable) in `services/common.py` and send it from the client and dashboard server code. Say in the README that auth is a demo-level control.

### Tests to add (moto)
```python
# tests/test_dynamo_store_moto.py   (pip install "moto[dynamodb]")
import boto3, pytest
from moto import mock_aws
from gridnudge.state import DynamoStore, ConcurrencyError
from gridnudge.persuasion.lints import LinTS

@pytest.fixture
def store(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "x"); monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "x")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        db = boto3.resource("dynamodb")
        db.create_table(TableName="u", KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
                        AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}], BillingMode="PAY_PER_REQUEST")
        db.create_table(TableName="m", KeySchema=[{"AttributeName": "model_id", "KeyType": "HASH"}],
                        AttributeDefinitions=[{"AttributeName": "model_id", "AttributeType": "S"}], BillingMode="PAY_PER_REQUEST")
        db.create_table(TableName="d", KeySchema=[{"AttributeName": "decision_id", "KeyType": "HASH"}],
                        AttributeDefinitions=[{"AttributeName": "decision_id", "AttributeType": "S"}], BillingMode="PAY_PER_REQUEST")
        yield DynamoStore(user_table="u", model_table="m", decision_table="d", dynamodb_resource=db)

def test_users_roundtrip_floats(store):
    store.put_users({"1": {"fatigue": 0.4, "nudges_today": 1}})
    got = store.get_users(["1"])["1"]
    assert abs(got["fatigue"] - 0.4) < 1e-9 and got["nudges_today"] == 1

def test_model_roundtrip_exact(store):
    st = LinTS(seed=1).get_state()
    store.put_model("lints", st, 0)
    back = store.get_model("lints")
    import numpy as np
    assert np.allclose(np.array(back["A"]), np.array(st["A"]))

def test_model_version_conflict(store):
    st = LinTS(seed=1).get_state()
    store.put_model("lints", st, 0)
    with pytest.raises(ConcurrencyError):
        store.put_model("lints", st, 0)      # already exists, expected_version=0 must fail

def test_decision_roundtrip(store):
    store.put_decisions([{"decision_id": "d1", "run_id": "r", "score": 0.5}])
    assert store.get_decision("d1")["score"] == 0.5
```
**Gate:** all four pass, plus the full suite (`pytest -q`).

---

## 3. Bedrock (optional, 30 minutes; skip if blocked)

1. Console → **Amazon Bedrock → Model access** (in your chosen region) → request/enable the model you will use.
2. The template default `apac.amazon.nova-micro-v1:0` is a cross-region **inference profile** ID, so use an APAC region where it is available; otherwise set `BedrockModelId` to a model ID that is enabled in your region. Verify the current ID and availability in the console.
3. Test outside the repo first:
   ```python
   import boto3, os
   brt = boto3.client("bedrock-runtime", region_name="ap-south-1")
   r = brt.converse(modelId=os.environ["BEDROCK_MODEL_ID"],
                    messages=[{"role": "user", "content": [{"text": "Say hello in one short sentence."}]}],
                    inferenceConfig={"maxTokens": 40, "temperature": 0.2})
   print(r["output"]["message"]["content"][0]["text"])
   ```
4. Only if this works, deploy with `EnableBedrock=true`. If not, leave it `false` and **say so** in the README ("templates only; Bedrock path implemented and gated by a numeric verifier").

---

## 4. Deploy (30 to 60 minutes)

```bash
bash scripts/build_lambda.sh
sam validate --lint -t infra/template.yaml
sam build -t infra/template.yaml            # add --use-container if numpy import fails later
sam deploy --guided --profile gridnudge
```
Answers for `--guided`:
- Stack name: `gridnudge-prod` · Region: your chosen region
- `StageName`: `prod` · `BedrockModelId`: your model ID · `EnableBedrock`: `false` (first deploy)
- Confirm changes before deploy: **Y** · Allow SAM CLI IAM role creation: **Y** · Disable rollback: **N**
- Warnings that functions have no authorization: **Y** (demo; mitigated by throttling) · Save arguments to `samconfig.toml`: **Y**

Read the changeset before approving. Then capture outputs:
```bash
aws cloudformation describe-stacks --stack-name gridnudge-prod \
  --query "Stacks[0].Outputs" --output table
export API=https://<id>.execute-api.<region>.amazonaws.com/prod    # the ApiUrl output (includes the /prod stage)
```
**Acceptance:** stack status `CREATE_COMPLETE`; the three DynamoDB tables, the S3 bucket and the FIFO queue exist.

---

## 5. Smoke tests (30 minutes)

### 5.1 Raw endpoint checks
```bash
curl -s -X POST "$API/events" -H "Content-Type: application/json" \
  -d '{"event_type":"heatwave","parameters":{"intensity":1.18}}'
curl -s "$API/metrics?run_id=smoke1"
```
(If an endpoint expects a different body shape, read `contracts/api.openapi.yaml` and `services/*.py` for the exact fields.)

### 5.2 End-to-end script (`scripts/smoke_aws.py`)
```python
import os, sys, uuid
from services.client import GridNudgeClient

api = os.environ["API"]
c = GridNudgeClient(base_url=api)
run_id = f"smoke_{uuid.uuid4().hex[:6]}"

cands = [{
    "user_id": str(i),
    "ev": {"battery_kwh": 40.0, "current_soc": 0.55, "charger_kw": 7.4},
    "trip": {"commute_km": 30.0, "departure_step": 120},
    "context": {"archetype": "price_sensitive", "fatigue": 0.0, "last_frame": "none", "nudges_today": 0},
} for i in range(20)]
req = {"run_id": run_id, "sim_time": "2026-10-11T18:30:00",
       "grid_forecast": {"feeder_load_mw": 11.0, "capacity_mw": 12.0, "grid_stress": 0.9},
       "candidates": cands}

decisions = c.decide(req)
print("decisions:", len(decisions), "nudges:", sum(1 for d in decisions if d["allocation"]["selected"]))
assert len(decisions) == 20

d0 = decisions[0]
print("decision id:", d0["decision_id"], "fail_silent:", d0.get("fail_silent"))
fetched = c.get_decision(d0["decision_id"])
assert fetched is not None

print(c.post_outcome({"decision_id": d0["decision_id"], "user_id": d0["user_id"], "adopted": True,
                      "kwh_shifted": 8.0, "savings_inr": 65.0, "battery_stress_delta": -0.05,
                      "opted_out": False, "realized_value": 30.0, "true_uplift": 0.4}))
print(c.get_metrics(run_id))
print(c.explain(d0["decision_id"]))
```
Run: `API=$API python scripts/smoke_aws.py`.

### 5.3 What to verify in the console/CLI
- **DynamoDB `gridnudge-decisions-prod`** has items (`aws dynamodb scan --table-name gridnudge-decisions-prod --max-items 3`).
- **DynamoDB `gridnudge-model-state-prod`** has a `lints` item whose `version`/`update_count` **increases after outcomes** (proves reward updates persist and the next `/decide` loads the updated model).
- **SQS** `gridnudge-rewards-prod.fifo` drains (messages in flight returns to 0); **RewardUpdateFn** logs show no errors.
- **S3** log bucket contains audit JSON under the keys the reward handler writes.
- **CloudWatch Logs** for each function show requests and no tracebacks. If the structured metrics are emitted via logs, find `veto_count`, `fail_silent_count`, `nudges_sent` with a Logs Insights query on the decide function's log group.
- **Failure tests:** send a malformed body (expect 400, not 500); send candidates with very low SOC and a tight departure (expect vetoes, no unsafe nudge); confirm a forced error path yields `fail_silent=true` and **no message**.

### 5.4 Full simulated run against AWS
Reuse the request-building code from `create_pipeline_policy` (refactor it into `build_request(world)`) and drive the twin with `GridNudgeClient(base_url=API)`: decide each interval, apply nudges in the twin, post outcomes. Start small (400 users, 1 to 2 days) to limit Lambda/DynamoDB cost, then compare its summary with the local run. Differences should be small; note any in the README.
**Acceptance:** the run completes; decisions and model updates are visible in AWS; metrics endpoint returns data the dashboard needs.

---

## 6. Dashboard on AWS

1. **Data mode:** the dashboard now has an adapter controlled by `NEXT_PUBLIC_API_BASE` and `NEXT_PUBLIC_DATA_MODE` (`replay`, `live`, `fixtures`). **Keep `replay` as the default** for the public URL and the video; use `live` for a clearly labeled live-check page or demo segment.
2. **Amplify Hosting:** Console → Amplify → Host web app → connect the repo → choose the branch → **monorepo app root: `dashboard`**. Use this `amplify.yml` at the repo root:
   ```yaml
   version: 1
   applications:
     - appRoot: dashboard
       frontend:
         phases:
           preBuild:
             commands: [npm ci]
           build:
             commands: [npm run build]
         artifacts:
           baseDirectory: .next
           files: ['**/*']
         cache:
           paths: [node_modules/**/*, .next/cache/**/*]
   ```
   Environment variables: `NEXT_PUBLIC_DATA_MODE=replay`, `NEXT_PUBLIC_API_BASE=$API`.
3. **Known risk to test after deploy:** the dashboard's server code reads files with `fs` from `public/`. On Amplify's server-side hosting, `public/` assets are served from the CDN and may **not** exist on the server filesystem. If pages show "Failed to load timeline data", switch those reads to `fetch()` of the site's own `/replay/...` and `/fixtures/...` URLs, or import the JSON files at build time.
4. **Fallback hosting:** static export to S3 + CloudFront only works if routes don't need server rendering (`/decision/[id]` is dynamic), so prefer fixing Amplify.
5. **CORS:** allowed origins are `*` for the demo; tighten to the Amplify URL if time allows.
**Acceptance:** public URL loads in replay mode with the real numbers; a `?mode=live` (or env-flipped build) fetches from API Gateway; no console errors.

---

## 7. Evidence to capture (for README, video and judges)

- [ ] Screenshot: CloudFormation stack `CREATE_COMPLETE` with the resource list
- [ ] Screenshot/CLI: DynamoDB `model-state` item showing `update_count` increasing across a run
- [ ] Screenshot: SQS queue drained, RewardUpdateFn logs
- [ ] Screenshot/Insights query: `veto_count`, `fail_silent_count`, `nudges_sent` from CloudWatch
- [ ] The smoke script output and the AWS-run summary next to the local-run summary
- [ ] The Amplify URL, and the `get_cedar_engine_status()` output for the README
- [ ] Architecture diagram in the README that marks exactly what is deployed vs local-only

---

## 8. Service-by-service status (what to claim)

| Service | Claim only if... |
|---|---|
| API Gateway (HTTP API), Lambda, DynamoDB, S3, SQS FIFO | Stack deployed and smoke tests pass |
| CloudWatch | Metrics/logs visible (screenshot) |
| Bedrock | `EnableBedrock=true` and a live call recorded in a decision (`language.source="llm"`, `verified=true`); otherwise say "templates only" |
| Cedar | Real engine active and parity test passes; otherwise say "policy file + Python evaluator" |
| Strands | Agent actually wraps the tools (not built yet); otherwise don't claim it |
| EventBridge, Cognito, SageMaker | Not in the template; don't list them as used |
| Amplify | Public URL works |

---

## 9. Cost, cleanup and troubleshooting

**Cost:** everything is pay-per-use. A short demo run costs cents; the main risks are leaving test loops running and Bedrock calls at scale. Keep the budget alert on.

**Cleanup after judging (not before):**
```bash
aws s3 rm s3://gridnudge-logs-<account>-<region>-prod --recursive    # bucket must be empty
sam delete --stack-name gridnudge-prod --profile gridnudge
```
Delete the Amplify app separately.

| Symptom | Likely cause | Fix |
|---|---|---|
| `Float types are not supported` | codec missing | Fix 1 |
| `ConcurrencyError` on first model write | masked boto3 error | Fix 3, then check the underlying error |
| `Runtime.ImportModuleError: numpy` | wrong-platform wheel or deps not installed | `sam build --use-container` or the managed pandas/numpy layer; check `build/lambda/requirements.txt` |
| `No module named sklearn` | Fix 4 not applied | remove the top-level import |
| `/decide` returns 500 with Bedrock errors | model access or region | leave `EnableBedrock=false`, or fix access (Section 3) |
| RewardUpdate runs in parallel / model version conflicts | reserved concurrency missing | confirm `ReservedConcurrentExecutions: 1` in the deployed function |
| 403 / `AccessDenied` on DynamoDB/S3 | policy missing for that function | check the function's SAM `Policies` block |
| Dashboard "Failed to load timeline data" on Amplify | `fs` reading `public/` on server | Section 6 risk item |
| Slow first request | Lambda cold start (about 1 to 3 s with numpy) | warm with one call before recording |

---

## 10. Definition of done (AWS)

- [ ] B1 to B6 fixed, moto tests added, `pytest -q` green
- [ ] Stack deployed from `build/lambda`; outputs captured
- [ ] Smoke script passes; model state persists and updates across calls
- [ ] A short twin run completed against the deployed API
- [ ] Dashboard publicly hosted in replay mode; live mode verified at least once
- [ ] Evidence captured; README AWS section matches reality (deployed vs local)
- [ ] Budget alert active; cleanup plan noted
