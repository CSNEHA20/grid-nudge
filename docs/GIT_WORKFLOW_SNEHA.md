# Git & PR Workflow for Sneha (M1 & Beyond)

## 1. Start from latest `dev`
```bash
git checkout dev
git pull origin dev
git checkout -b s/m1-data
```

## 2. Edit files
Work on files in your assigned scope:
- `data/scripts/`
- `data/raw/SOURCES.md`
- `data/ASSUMPTIONS.md`
- `config/tariffs.yaml`
- `dashboard/` (for M12)

## 3. Verify locally before commit
```bash
python data/scripts/validate.py
python -m pytest -q
python scripts/check_ownership.py
```

## 4. Stage, commit, and push
```bash
git add .
git commit -m "feat(data): complete M1 datasets and scripts"
git push -u origin s/m1-data
```

## 5. Create and merge PR

### Option A: Using GitHub CLI (`gh`)
```bash
# Create PR targetting dev
gh pr create --base dev --head s/m1-data --title "feat(data): complete M1 datasets and scripts" --body "M1 data download and validation complete."

# View CI status
gh pr checks

# Squash-merge into dev after CI passes
gh pr merge --squash --delete-branch
```

### Option B: Using GitHub Web UI
1. Open: https://github.com/Vishallakshmikanthan/gridnudge
2. Click **"Compare & pull request"**.
3. Set **base: `dev`** and **compare: `s/m1-data`**.
4. Click **"Create pull request"**.
5. Wait for green checkmark (CI passed).
6. Click **"Squash and merge"**, then **"Confirm"**.
