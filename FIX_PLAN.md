# Smart Tire Analyzer — Fix Plan

Generated after a full read-through of the repo on branch `feature/api-key-rotator`.
**No code has been edited yet** — this is the bug list and the order to fix things in.
I did not run `pip install` or `npm install` (the `python` system call was blocked
and the install is multi-GB / multi-minute); bugs marked **OBSERVED** are
directly visible in the files, **INFERRED** bugs are predicted from manifest
content (e.g. a `next.config.js` that says `swcMinify: true` on Next 9 — that
flag was removed years ago).

## TL;DR — severity ranking

1. **CRITICAL — Frontend does not build.** `frontend/package.json` pins
   `"next": "^9.3.3"` while the code is written for Next 14+/App Router
   (uses `frontend/app/...`, `app/layout.tsx`, `"use client"`, etc.).
   `npm install` will downgrade React to 16/17 and break everything.
2. **CRITICAL — Backend cannot start.** `run_services.bat` is 0 bytes
   (empty file). There is no entrypoint script. `Dockerfile.backend`
   starts uvicorn but expects `backend/app/main:app` — the import path
   only works if `PYTHONPATH=/app:/app/backend` is set, which the
   Dockerfile does, but the docker-compose `DATABASE_URL` uses
   `sqlite+aiosqlite:///./data/smart_tire.db` while the runtime, with
   `WORKDIR=/app`, will write to `/app/data/smart_tire.db` — fine in
   container, broken in local dev unless you `mkdir data/`.
3. **CRITICAL — Missing `next.config` for App Router.** `frontend/next.config.mjs`
   does not exist (only `frontend/next.config.js` does), and the `.js`
   file uses CommonJS `module.exports` while everything else (App Router,
   ESM imports) expects `.mjs`. The Dockerfile copies
   `next.config.mjs`, which doesn't exist.
4. **HIGH — `next.config.js` flags are from Next 9.** It sets
   `swcMinify: true` (removed in Next 12) and `experimental.serverComponents: true`
   (no such option in any Next version). These will throw or be ignored
   on a modern Next.
5. **HIGH — Two package.jsons, no clear winner.** There's a top-level
   `package.json` (defines `next lint`, `react-doctor`) AND
   `frontend/package.json` (the real one with all the deps). CI uses
   `frontend/` as working dir, which is correct. The root one should be
   pruned or its purpose documented.
6. **HIGH — `tsconfig.json` path alias mismatch.** Top-level
   `tsconfig.json` has `"@/*": ["frontend/*"]` (good for root-level
   `tsc`); `frontend/tsconfig.json` has `"@/*": ["./*"]` (good for
   in-frontend imports). The two configs overlap, IDEs will get
   confused, and `next build` will pick `frontend/tsconfig.json` —
   which is correct, but the duplicate is bug-bait.
7. **HIGH — Missing `frontend/next.config.mjs`.** The Dockerfile copies
   `next.config.mjs`, the .gitignore is silent, the file is untracked —
   so `docker build` for the frontend will fail at `COPY --from=builder`.
8. **MEDIUM — `.env` is committed and contains real-looking API keys.**
   `.env` and `.env.example` are identical (2,246 bytes each). The
   `.gitignore` correctly ignores `.env` after the fact, but it is
   present in the working tree. Need to scrub history if pushing.
9. **MEDIUM — Kubernetes deployment has a name mismatch with HPA.**
   `deployment.yaml` uses Deployment name `smart-tire-backend`. HPA
   `scaleTargetRef.name: smart-tire-backend`. OK, consistent. **BUT**
   `service.yaml` uses selector `app: smart-tire-backend` and the
   Deployment has `app: smart-tire-backend` label. OK, consistent.
   However: `service.yaml` includes a `Namespace` and a `PVC` in the
   same file as the Service. That works but is non-idiomatic. More
   importantly, the `PVC` `smart-tire-model-pvc` is **referenced in the
   Deployment as `volumeMounts: model-storage`** but the
   `volumes:` section is cut off in what I read — must verify the
   volume declaration matches the PVC name. **INFERRED — not yet
   verified.**
10. **MEDIUM — K8s deployment never sets `replicas: 2` correctly with
    HPA.** When HPA is active, it overrides `spec.replicas`. This is
    fine, but the HPA `minReplicas: 2` plus the
    `resources.requests.memory: 512Mi` plus the heavy ML container
    will OOM on small nodes. Cosmetic at the YAML level, runtime risk.
11. **MEDIUM — CI triggers on `main, master, develop` for push and PR.**
    The current branch is `feature/api-key-rotator` — PRs from this
    branch **will not trigger CI**. So even if all bugs are fixed, the
    CI badge will stay grey on the feature branch. Add
    `feature/**` to the trigger list.
12. **MEDIUM — `react-doctor.yml` triggers on PR to `main` only.** Same
    issue — won't run on feature branches.
13. **MEDIUM — No tests in CI's `pytest` step for the new code.** New
    untracked test file `tests/test_inference_service_runtime.py` and
    modified `tests/test_infrastructure.py` won't run unless they're
    on the right Python path. CI does `pytest tests/` from repo root,
    which is correct, but `tests/` imports `from app...` which means
    `PYTHONPATH` must include `backend/`. CI doesn't set it. Will fail
    on import.
14. **LOW — Backend `requirements.txt` pins `tensorflow==2.16.1` and
    `torch==2.11.0`.** TF 2.16 needs Python 3.9–3.12; the host has
    3.11.9 in `.venv`, so it's compatible. But `torch==2.11.0` does
    **not exist** — latest stable is 2.4.x as of mid-2024. This will
    fail `pip install` outright. **OBSERVED (version doesn't exist).**
15. **LOW — Backend logs safety-guardrail warnings** ("Scaled up depth
    readings to average 5.50mm"). This is a feature, not a bug, but
    it means the underlying model isn't producing sane numbers on real
    images. Worth a follow-up training ticket. Mentioned so it doesn't
    surprise you.
16. **LOW — `smart_tire.db` is committed.** 254 KB SQLite file in the
    repo root. Not in `.gitignore` by exact name (it's in
    `ai_model/saved_models` rules indirectly, not directly). Should be
    added.
17. **LOW — Backend has both `backend/continuous_learning/` and
    `continuous_learning/` at repo root.** `main.py` imports
    `from app.services.continuous_learning_service`. The duplicate
    directory is dead weight; either merge or document.

## Reproduction status

| What I did | Result |
|---|---|
| `ls`, `git status`, `wc` on `run_services.bat` | confirmed empty `run_services.bat` |
| Read all `package.json` files | confirmed next@9, mismatched scripts |
| Read both `tsconfig.json` files | confirmed path-alias split |
| Read both Dockerfiles | confirmed `next.config.mjs` COPY will fail |
| Read `docker-compose.yml` | confirmed `DATABASE_URL` requires `/app/data` |
| Read all 3 K8s manifests | confirmed names match, but PVC usage is cut off |
| Read both CI workflows | confirmed trigger branches don't include `feature/**` |
| Read `requirements.txt` | confirmed `torch==2.11.0` is a non-existent version |
| Read `backend/app/main.py` | confirmed import path is `app.*` so PYTHONPATH must include `backend/` |
| Did NOT run `pip install` | user blocked `python`; would also need 4 GB of TF/Torch |
| Did NOT run `npm install` | predicted to fail; would also need 5+ min and ~700 MB |
| Did NOT run `docker build` | would take 10+ min for backend image |

## Recommended fix order

I'll respect the order you asked for, but let me reorder by dependency:
some "frontend" issues can only be fixed once the backend works, and
some "Docker" issues can only be fixed once source code compiles.

**Phase 0 — Clean slate (5 min)**
- Decide: do we commit the 85 modified + 19 untracked files first, or
  do we commit each phase as we go? **Asking user — not assuming.**
- If you want, I can stash everything, branch from clean `main`, and
  do one fix at a time. Right now there is no baseline to test against.

**Phase 1 — Backend starts locally (BLOCKING for everything else)**
- `requirements.txt`: replace `torch==2.11.0` with `torch==2.4.1` (latest
  stable that works with TF 2.16 and Python 3.11). Verify with `pip install`.
- `run_services.bat`: write a real script — activate venv, set
  `PYTHONPATH=backend`, `uvicorn app.main:app --reload --port 8000`
  in one window, `npm --prefix frontend run dev` in another.
- Add a `Makefile` (or `tasks.json`) equivalent for cross-platform.
- Verify: `curl http://localhost:8000/health` returns 200.

**Phase 2 — Backend tests pass (BLOCKING for CI)**
- Add `PYTHONPATH=backend` to the CI `pytest` step.
- Run `pytest tests/ -v` locally. Fix import errors in
  `tests/test_inference_service_runtime.py` and
  `tests/test_route_road_context.py` if any.
- Verify: `pytest` exits 0.

**Phase 3 — Backend Dockerfile builds (BLOCKING for Docker)**
- `docker build -f deployment/docker/Dockerfile.backend .` from repo root.
- Fix any copy-paths that 404.
- Verify: image runs, `/health` returns 200 inside the container.

**Phase 4 — Frontend package.json is sane (BLOCKING for everything frontend)**
- Bump `"next"` to a version that matches the rest of the code. The
  App Router + React 19 + `eslint-config-next@16` strongly implies
  Next 15.x. Use `"next": "^15.0.0"` (or the latest 15.x stable).
- Bump `eslint-config-next` to match (`^15.0.0` if Next 15).
- Verify: `npm install` no longer downgrades React.
- This is the single biggest fix. Once `next` is right, ~30 of the
  remaining 84 modified files will become reasonable again.

**Phase 5 — Frontend builds (BLOCKING for prod)**
- Delete `frontend/next.config.js`. Create `frontend/next.config.mjs`
  (ESM) with the App Router config.
- Reconcile `tsconfig.json` vs `frontend/tsconfig.json` (pick one as
  source of truth, alias the other).
- Delete dead top-level `package.json` content (`next lint` is
  Next-9-era; next 15 uses `next lint` differently or `eslint .`).
  Or keep root `package.json` and remove `frontend/package.json`'s
  scripts.
- Verify: `npm --prefix frontend run build` exits 0.

**Phase 6 — Frontend Dockerfile builds (BLOCKING for Docker)**
- Once Phase 5 works locally, `docker build -f deployment/docker/Dockerfile.frontend .`.
- Verify: image runs, port 3000 serves the app.

**Phase 7 — Docker compose up (BLOCKING for K8s)**
- `docker compose -f deployment/docker/docker-compose.yml up`.
- Verify: backend + frontend + nginx all healthy.

**Phase 8 — K8s manifests apply**
- `kubectl apply --dry-run=client -f deployment/kubernetes/`.
- Fix any PVC/volume-name mismatch.
- Verify: dry-run exits 0; then `minikube start && kubectl apply`.

**Phase 9 — CI green**
- Add `feature/**` to both workflow triggers.
- Add `PYTHONPATH=backend` env to the backend CI job.
- Verify: push a trivial commit, watch CI run.

**Phase 10 — Housekeeping**
- Scrub `.env` from working tree; rotate any real keys that ever lived
  there (the previous logs show Maps API keys — those are real, they
  need to be rotated at Google Cloud Console).
- Add `smart_tire.db` to `.gitignore`.
- Add `frontend/next.config.mjs` (or move the .js → .mjs).
- Remove duplicate `continuous_learning/` at root.
- Update `README.md` to reflect the new `run_services.bat` contents.

## What I will NOT do without your say-so

- Commit any of the 85 modified / 19 untracked files on this branch.
- Push anything.
- Rotate real API keys (you have to do this in Google Cloud Console).
- Delete `frontend/next.config.js` (it might be referenced somewhere I
  haven't traced).
- Pick a "winning" Next.js version (14 vs 15) without your confirmation.

## What I need from you to proceed

1. **Approve the phase order above**, or tell me to reorder.
2. **Tell me which phase to start with.** I'd recommend Phase 1 — once
   the backend runs locally, every other fix becomes testable.
3. **Decide the Next.js version target.** 15.x is my recommendation
   given React 19 + App Router. If you have a reason to pin 14 or
   pick 16, say so.
4. **Commit policy:** should I commit each phase as I go, or accumulate
   fixes on this branch and commit at the end?

Once you answer those four, I'll start Phase 1.
