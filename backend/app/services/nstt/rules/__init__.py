"""
NSTT Rule Engine — Rules Package
==================================
Contains all individual classification rule modules.
Each module exports a single apply_* function that mutates records in-place.

Rule execution order (enforced by rule_engine.py):
  1. total_sr        — ATTRIBUTEDTO filter
  2. nstt_count      — blank INCIDENTID filter
  3. capture_type    — Automation vs Manual
  4. automation_classifier — Resolved → Same → Different (ORDER MATTERS)
  5. same_nstt       — IM/Non-IM, Auto/Manual, SA/NSA
  6. different_nstt  — 4 exact sub-categories
  7. resolved_nstt   — IM/Non-IM, Auto/Manual
  8. manual_classifier — Resolved/Before SR/After SR → SA/NSA
  9. wrong_nstt      — CONTAINS-based exception rules
  10. failure_analysis — Manual population failures
"""
