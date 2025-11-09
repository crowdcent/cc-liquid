---
title: Autopilot & Scheduling
---

Autopilot runs a live dashboard and executes rebalances on your schedule.

## Run autopilot

```bash
cc-liquid run --skip-confirm
```

Live dashboard (monitor):

![dashboard](images/dashboard.svg)

Flags:

- `--skip-confirm`: execute without confirmation when due
- `--tmux`: run monitor within a tmux session/window
- `--set`: override config at runtime
- `--refresh`: UI refresh cadence in seconds (default 1.0)

!!! tip "Run inside tmux (advanced)"
    For long-running sessions, you can run the dashboard in a fixed tmux session. This will attach to the session if it already exists, or create it and start the loop if not.

    Start (or attach) with uv:

    ```bash
    uv run cc-liquid run --tmux --skip-confirm
    ```

    - Detach with Ctrl-B and continue using your machine. 
    - Re-attach later: `tmux attach -t cc-liquid` or `cc-liquid run --tmux`
    - Stop the loop with Ctrl-C. The session stays open until you exit/kill it.

## Schedule

Configure in [`cc-liquid-config.yaml`](configuration.md#yaml-cc-liquid-configyaml):

```yaml
portfolio:
  rebalancing:
    every_n_days: 10
    at_time: "18:15"   # UTC
```

The next time is computed from the last successful rebalance timestamp, stored in `.cc_liquid_state.json`.

State details:

- The file stores `last_rebalance_date` as ISO-8601 UTC.
- If no state is present, the next run is scheduled for today at `portfolio.rebalancing.at_time` (or immediately if already past).
- Each successful cycle updates the timestamp.


