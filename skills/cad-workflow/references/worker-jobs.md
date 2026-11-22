# Worker job contract

Use [worker_job.py](../scripts/worker_job.py) to prepare a brief and verify the returned evidence bindings. It does not launch an agent, enforce OS permissions, fetch a model catalog or certify the truth of a check. Model and context preferences come from the [team profile](../../../profiles/agents/cad-team.yaml); the maintained decision rules are in [bounded delegation](../../../knowledge/workflow/delegation.md).

```sh
uv run python skills/cad-workflow/scripts/worker_job.py prepare \
  skills/cad-workflow/references/research-job.example.json --out /tmp/toolroom-source-job
```

The output directory must be new. It receives `job.json` and `brief.md`; stdout contains only a short status, paths and launch preferences. Input paths are relative to the request JSON. Source contents are not copied into the brief. The job hash includes the source hashes, criteria, role, profile, tool revision and output scope.

For the runtime's collaboration interface, launch the prepared brief with the recorded model, `fork_turns: "none"` and the recorded reasoning effort. Read only that brief and required source sections. For the critical role resolve `highest_available` using the current runtime's supported effort levels, not a guessed universal value. This routing is task-scoped; Toolroom does not modify global account/model settings.

## Request

See the runnable [research request](research-job.example.json). Required fields are `schema_version: 1`, `id`, `role`, `objective`, nonempty `constraints`, `inputs`, expected relative `artifacts`, and `checks`. Each input has `path` and `purpose`. Each check has a unique `id`, a `criterion`, and `owner: "worker"` or `"astra"`. Use isolated input sets and output directories. Authorized CAD writes still need the backend-specific workflow; this contract never grants new permissions.

Optional `entrypoints` is a nonempty list of paths relative to the request JSON, for example `"entrypoints": ["inputs/manifest.json"]`. Each must resolve to a distinct declared input. Use a manifest or concise source note that gives the worker an effective starting route; the full `inputs` list still declares every file that must remain unchanged.

The brief shows those entrypoints, or all inputs when none are specified, relative to one common base directory. Input hashes and the complete inventory live in `job.json`. Constraints, output names, check criteria and owners stay visible. `render_brief(job)` exposes this formatting independently of preparation. A shorter brief is not a total-token benchmark: count subsequent source reads too.

## Return and verification

The worker writes `result.json` in the job directory:

```json
{
  "job_sha256": "hash from job.json",
  "status": "review",
  "summary": "Requested source passages extracted; applicability needs lead review.",
  "artifacts": [{"path": "evidence.json", "sha256": "actual file hash"}],
  "checks": [
    {"id": "source-evidence", "status": "no_findings", "evidence": "evidence.json"},
    {"id": "engineering-applicability", "status": "not_run"}
  ]
}
```

```sh
uv run python skills/cad-workflow/scripts/worker_job.py verify \
  /tmp/toolroom-source-job /tmp/toolroom-source-job/result.json \
  --out /tmp/toolroom-source-job/verification.json
```

The checker rejects changed inputs/profiles, foreign result bindings, altered or escaping artifacts and worker claims to clear Astra-owned checks. Missing expected artifacts or unfinished worker checks produce `incomplete`; pending Astra checks produce `review`. A worker's claimed success cannot override those states. `no_findings` means only that this contract's structural checks found no issue. Returned evidence must still be interpreted within its own inspection scope.

Entrypoints affect presentation only: verification covers every declared input. The helper's own hash is also bound to the job. Verify an existing frozen job with its recorded helper revision; a helper update does not retroactively update old evidence.

The lead resolves pending critical checks and carries the authorized task through delivery. Internal `review` is not a new user approval gate. Keep physical fit or lifetime tests explicitly unresolved when delivering a coupon intended to measure them.

Exit codes follow the [shared verification states](../../../knowledge/foundations/verification.md#result-states): 0 `no_findings`, 1 `review`, 2 `incomplete`. Neither 0 nor a model name is a manufacturing release. Context allowances count characters explicitly and reject overlong briefs/results instead of silently discarding requirements or evidence.
