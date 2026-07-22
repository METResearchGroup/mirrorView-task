# Migrate local experiment artifacts to S3

Upload allowlisted `*.csv` / `*.json` under `experiments/{folder}/` to
`s3://mirrorview-experimental-artifacts/` with **path-preserving keys**, tracked in
local SQLite. **Local files are never deleted by this tooling.**

See `spec.md` for frozen contracts.

## Quick start

```bash
# From repo root
chmod +x experiments/migrate_local_artifacts_to_s3_2026_07_20/upload_to_s3.sh
chmod +x experiments/migrate_local_artifacts_to_s3_2026_07_20/verify_s3_object.sh

# Dry-run discovery
PYTHONPATH=. uv run python experiments/migrate_local_artifacts_to_s3_2026_07_20/runner.py init --dry-run

# Register into SQLite
PYTHONPATH=. uv run python experiments/migrate_local_artifacts_to_s3_2026_07_20/runner.py init

# Dry-run upload
PYTHONPATH=. uv run python experiments/migrate_local_artifacts_to_s3_2026_07_20/runner.py upload --dry-run

# Pilot prefix with verify
PYTHONPATH=. uv run python experiments/migrate_local_artifacts_to_s3_2026_07_20/runner.py upload \
  --prefix experiments/followup_model_error_analysis_2026_07_15 \
  --verify

# Full upload + verify
PYTHONPATH=. uv run python experiments/migrate_local_artifacts_to_s3_2026_07_20/runner.py upload --verify

# Status / export
PYTHONPATH=. uv run python experiments/migrate_local_artifacts_to_s3_2026_07_20/runner.py status
PYTHONPATH=. uv run python experiments/migrate_local_artifacts_to_s3_2026_07_20/runner.py export \
  --out experiments/migrate_local_artifacts_to_s3_2026_07_20/manifests/full_upload_manifest.json
```

## Tests

```bash
PYTHONPATH=. uv run pytest experiments/migrate_local_artifacts_to_s3_2026_07_20/tests/ -q
```

## Layout

| File | Role |
| --- | --- |
| `constants.py` | Bucket, allowlist, excludes, paths |
| `file_discovery.py` | Phase 1 discover + register |
| `migration_tracker.py` | SQLite status API |
| `runner.py` | CLI: init / upload / status / retry-failed / verify / export |
| `upload_to_s3.sh` | Single-object `aws s3 cp` |
| `verify_s3_object.sh` | Fail-closed size + sha256 verify |
| `migration_tracker.db` | Local DB (**gitignored**) |

## Notes

- Bucket setup: `notes/aws_setup.md`
- Default region: `us-east-2`
- Failed uploads are **not** retried until `runner.py retry-failed`
