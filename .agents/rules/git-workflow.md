# Git & Execution Workflow Rule

- **Pull dev before execution**: Always fetch and pull the latest `dev` branch before starting execution (`git checkout dev && git pull origin dev`).
- **Separate feature branch**: Always work in a dedicated feature branch (`v/m*-...` for Vishal, `s/m*-...` for Sneha).
- **Zero Errors**: Always run all relevant tests (`python -m pytest tests/ -q`) and verify zero errors before committing or pushing.
- **Push & Merge**: Push the feature branch to origin, open PR or merge into `dev`, and push `dev` to origin.
