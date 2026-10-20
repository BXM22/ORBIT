# Step 9 — Diagnose and fix the cron "Operation not permitted" bug

**Why:** `pipeline.log`/`check.log` currently show repeated
`bash: .../run.sh: Operation not permitted` errors when cron fires. This is
a live, real bug independent of everything above — CI doesn't exercise cron
at all (it calls `run.sh check` / `python -m orbit.pipeline` directly), so it's safe to
tackle this step in parallel or after the testing work, not blocking it.

**Likely cause:** "Operation not permitted" (as opposed to "Permission
denied") is the signature of macOS's TCC (Transparency, Consent, and
Control) privacy system blocking `cron` from reaching resources outside its
sandbox — in this case, almost certainly the Docker socket that
`docker compose` needs.

**How to confirm:** after a scheduled cron firing, run:

```bash
sudo log show --predicate 'eventMessage contains "cron"' --last 1h
```

and look for TCC-related denials around the time of the failure.

**Fix options:**
1. **Full Disk Access for cron** — System Settings → Privacy & Security →
   Full Disk Access → add `/usr/sbin/cron`. Simplest, try this first.
2. **Migrate to `launchd`** — macOS's native scheduler, which doesn't hit
   the same TCC wall for user agents. Create
   `~/Library/LaunchAgents/com.orbit.pipeline.plist` pointing at `run.sh`,
   load it with `launchctl load`. More idiomatic on macOS but more setup.

**Check your work:** run `./run.sh install`, wait for the next scheduled
firing (every 10 min for the pipeline, every 30 min for the freshness
check), and confirm `pipeline.log`/`check.log` show clean `loaded ...` /
`OK:` lines with no `Operation not permitted` errors.

---

[← Step 8](08-github-actions-ci.md) · [Index](README.md) · [Wrap-up →](README.md#when-youre-done)
