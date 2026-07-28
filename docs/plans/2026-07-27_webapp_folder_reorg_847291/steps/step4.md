# Step 4: Verify local static serve

## Goal

Copy the stimulus catalog into the new public image path, serve that public tree with a static HTTP server, and confirm the experiment loads config with unchanged API URLs, fetches the catalog locally, and progresses past political affiliation without assignment errors. Do not use npm start/dev for this gate; save-to-S3 completion is optional.

## Caller / unit of work

**Main caller:** Browser hitting `http://localhost:3000/index.html?PROLIFIC_PID=TEST123` served from `webapp/public/`.

**In scope:** Stimuli copy, static HTTP server, browser/network checks for core flow past affiliation.

**Out of scope:** `npm run dev` / `npm start`; completing the full study; proving SAVE_DATA_URL write; docs updates; S3 staging (Step 5); Terraform (Step 6).

## Prep references

- Commands: [ROLLOUT_PLAN.md](../ROLLOUT_PLAN.md) § Phase 2
- Stimuli SoT (unchanged): `jobs/mirrorview_scaled_2026_06_18/flips.csv`
- Browser-relative catalog path (unchanged S3/site key): `img/flips_scaled_2026_06_18.csv`

## Files to inspect

| Path | Why |
|------|-----|
| `jobs/mirrorview_scaled_2026_06_18/flips.csv` | Source-of-record copy source |
| `webapp/public/config.js` | API URLs must be production |
| `webapp/public/index.html` | Entry |
| `webapp/public/main.js` | Catalog fetch path `img/flips_scaled_...` |
| `webapp/public/img/flips_scaled_2026_06_18.csv` | After copy; gitignored deploy asset |

## Files allowed to change

- Create/overwrite only: `webapp/public/img/flips_scaled_2026_06_18.csv` (local data copy; gitignored)
- Create dir `webapp/public/img/` if missing

## Files forbidden to change

- Any tracked source under `webapp/public/` (including `config.js` URLs, `main.js` `postCatalogPath` value)
- Lambdas, infra, upload scripts, docs
- Do not restore or invent `server-local.js`

## Exact commands

```bash
cd /Users/mark/src/work/mirrorView-task

# Stimuli catalog into new local path
mkdir -p webapp/public/img
cp jobs/mirrorview_scaled_2026_06_18/flips.csv \
  webapp/public/img/flips_scaled_2026_06_18.csv
test -s webapp/public/img/flips_scaled_2026_06_18.csv && echo "OK: local catalog present"

# Static server — MUST use webapp/public (not root public/)
python3 -m http.server 3000 --directory webapp/public
# Leave running; open in browser:
#   http://localhost:3000/index.html?PROLIFIC_PID=TEST123
```

In a second shell (server running):

```bash
curl -sI "http://localhost:3000/index.html" | head -1
# Expect: HTTP/1.0 200 OK  (or HTTP/1.1 200 OK)

curl -sI "http://localhost:3000/img/flips_scaled_2026_06_18.csv" | head -1
# Expect: HTTP/1.0 200 OK

curl -s "http://localhost:3000/config.js" | rg "POST_ASSIGNMENTS_URL|SAVE_DATA_URL"
# Expect both production URLs:
#   https://bgdxga8s91.execute-api.us-east-2.amazonaws.com/prod/get-post-assignments
#   https://bgdxga8s91.execute-api.us-east-2.amazonaws.com/prod/save-jspsych-data
```

### Browser / Network checklist (required)

1. Page loads from localhost:3000.
2. `config.js` loads; URLs unchanged (match curl above).
3. Assignment POST to live API Gateway returns 2xx.
4. Fetch of `/img/flips_scaled_2026_06_18.csv` returns 200 from **local** server (not a missing file).
5. After political-affiliation step: **no** “Assignment Error” / “unknown post IDs”.
6. At least one moderation trial UI renders.

Save-to-S3 on completion: **optional**, not required to pass.

### Explicitly do not run

```bash
# Forbidden for this gate
npm start
npm run dev
cd webapp && npm start
```

## Pass / fail

### Pass

- Curl checks return 200 for index + catalog; config.js shows production URLs.
- Browser flow progresses past affiliation without assignment errors.
- Moderation trials render.
- Server was started with `--directory webapp/public`.

### Fail

| Symptom | Likely cause |
|---------|--------------|
| Serving empty / wrong site | Used `--directory public` or leftover root `public/` |
| Assignment Error: unknown post IDs | Forgot CSV copy to `webapp/public/img/...` |
| 404 on `/img/...` | File not under `webapp/public/img/` |
| config.js URLs differ from production | Accidental edit in Step 3 — restore URLs before continuing |
| npm start used as verification | Invalid gate; switch to static serve |

## Rollback

Stop the HTTP server. Local CSV under `webapp/public/img/` is disposable. If the serve path is wrong, fix tree/docs paths in prior steps — do not change API URLs to “make it work.”

## Done when

Core flow past affiliation is confirmed on `webapp/public` static serve; proceed to Step 5 staging dry-run.
