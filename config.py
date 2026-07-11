"""
config.py — tunable settings for the audit pipeline.

Change these two numbers to adjust how the system behaves without
touching any pipeline logic. Both are also overridable via environment
variables (useful for adk web / Agent Engine deployments where editing
files isn't convenient).

  PURSUE_THRESHOLD  — a practice only gets a full report + demo website
                      + draft email if it fails AT LEAST this many of
                      the 12 checks. Lower = more leads pursued (more
                      generous), higher = only the worst sites (more
                      conservative). Range: 1-12.

  MAX_LEADS         — upper limit on how many practices the Scout will
                      return per run. Protects against accidentally
                      auditing hundreds of sites (and burning API/time)
                      on a broad query like "all dermatologists in
                      Switzerland".

                      INVARIANT: keep this <= the number of parallel
                      audit workers (3, in agents/agent.py). It is one
                      worker per lead, so a lead beyond the worker count
                      would be found but never audited (silently dropped).
"""

import os

PURSUE_THRESHOLD = int(os.environ.get("PURSUE_THRESHOLD", 4))
MAX_LEADS = int(os.environ.get("MAX_LEADS", 3))
