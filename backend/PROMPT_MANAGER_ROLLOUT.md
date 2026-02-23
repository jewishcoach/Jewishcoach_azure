# BSD V2 Prompt Manager Rollout

This rollout switches BSD V2 from legacy compact prompt loading to modular markdown stages via `prompt_manager.py`, while preserving a rollback path.

## What Is Included

- Runtime uses stage-aware prompt assembly (`core + current stage`) in:
  - `backend/app/bsd_v2/single_agent_coach.py`
  - `backend/app/bsd_v2/single_agent_coach_streaming.py`
- Full collected-data schema in prompt response format.
- Hebrew and English modular prompt trees.
- Local validation scripts:
  - `test_prompt_manager.py`
  - `test_prompts_simple.py`
  - `test_prompt_pipeline_local.py`

## Runtime Flag

Use env var `BSD_V2_PROMPT_MODE`:

- `markdown` (default): modular prompt manager
- `compact`: legacy compact prompt mode (fallback)

## Pre-Deploy Checks

Run from repo root:

```bash
python3 test_prompt_manager.py
python3 test_prompt_pipeline_local.py
python3 test_prompts_simple.py
```

Note: these scripts resolve paths relative to repository root and are CI-runner friendly.

## CI/CD

Backend deployment pipeline:

- Workflow: `.github/workflows/azure-backend-deploy.yml`
- Trigger:
  - push to `main` with changes under `backend/**`
  - manual `workflow_dispatch`
- Added validation step before deploy zip creation:
  - prompt-manager tests
  - local prompt-state integration test
  - markdown prompt validation

If validations fail, deployment stops before publishing.

## Deploy Options

### Option A: CI/CD (recommended)
1. Commit and merge to `main`.
2. GitHub Actions runs backend deploy workflow automatically.
3. Verify app health:
   - `https://jewishcoach-api.azurewebsites.net/health`

### Option B: Manual backend deploy
From `backend/`:

```bash
./deploy_to_azure.sh
```

## Rollback

Fast rollback without code revert:

1. Set `BSD_V2_PROMPT_MODE=compact` in backend app settings.
2. Restart backend app.

This restores legacy prompt behavior while keeping new files in repository.

## Post-Deploy Validation

- Open V2 chat flow (including stream endpoint).
- Verify stage progression and stable JSON output.
- Verify no drift between streaming and non-streaming responses.
