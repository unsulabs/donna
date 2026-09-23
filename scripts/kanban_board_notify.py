#!/usr/bin/env python3
"""Compatibility notice for the old best-effort notifier.

The v1 script advanced a cursor before delivery and read private native SQL.
It is intentionally not retained as a silent substitute for executive review.
Existing cron owners must migrate it explicitly, not silently change job semantics.
"""
import sys

if __name__ == "__main__":
    print("Donna 2: this legacy no-agent notification job needs migration. Use native notify+wake subscriptions and a skill-backed review cron with donna_review_gate.py. See docs/AUTOMATION.md. No cursor was advanced and no task was modified.", file=sys.stderr)
    raise SystemExit(2)
