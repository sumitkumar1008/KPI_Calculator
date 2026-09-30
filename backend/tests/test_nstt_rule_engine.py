"""
Unit Tests for Phase 2 — NSTT Rule Engine
==========================================
Tests all 10 rule modules independently with known-answer test records,
then tests the full orchestrator end-to-end.

Critical tests:
  - Resolved NSTT is checked BEFORE Same NSTT (order test)
  - CONTAINS rules use substring, not equality
  - Wrong NSTT uses exact spec labels
  - Different NSTT produces exactly 4 sub-categories with exact labels
  - Failure Analysis correctly checks DESCRIPTION and AUTOMATION_RCA_CONCLUSION_TEXT
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ── Helper to build a minimal record ─────────────────────────────────────────

def make_record(**kwargs):
    """Creates a minimal record dict with sensible defaults."""
    defaults = {
        "INCIDENTID": "INC001",
        "ATTRIBUTEDTO": "TXN",
        "SRCREATIONTIME": "2026-09-01 10:00:00",
        "FACTORY": "IM",
        "AUTO_ALLOCATION": "yes",
        "AUTOMATION_UPDATE_NSTT_NUMBER": "INC001",
        "AUTOMATION_RCA_CONCLUSION_TEXT": "",
        "ASSIGNED_SUPPORT_COMPANY": "Company A",
        "UP_TIME": "2026-09-01 15:00:00",
        "Submit Date": "2026-09-01 09:00:00",
        "INCIDENT_IMPACT": "SA",
        "DESCRIPTION": "Normal incident",
        "is_matched": True,
        "is_potential_duplicate": False,
    }
    defaults.update(kwargs)
    return defaults


# ═══════════════════════════════════════════════════════════════════════════════
# Rule 1: Total SR Filter
# ═══════════════════════════════════════════════════════════════════════════════

class TestTotalSR:
    def test_tnl_is_total_sr(self):
        from app.services.nstt.rules.total_sr import apply_total_sr
        rec = make_record(ATTRIBUTEDTO="TNL")
        apply_total_sr([rec])
        assert rec["is_total_sr"] is True

    def test_txn_is_total_sr(self):
        from app.services.nstt.rules.total_sr import apply_total_sr
        rec = make_record(ATTRIBUTEDTO="TXN")
        apply_total_sr([rec])
        assert rec["is_total_sr"] is True

    def test_txn_infra_is_total_sr(self):
        from app.services.nstt.rules.total_sr import apply_total_sr
        rec = make_record(ATTRIBUTEDTO="TXN_Infra")
        apply_total_sr([rec])
        assert rec["is_total_sr"] is True

    def test_txn_hardware_is_total_sr(self):
        from app.services.nstt.rules.total_sr import apply_total_sr
        rec = make_record(ATTRIBUTEDTO="TXN_Hardware")
        apply_total_sr([rec])
        assert rec["is_total_sr"] is True

    def test_other_not_total_sr(self):
        from app.services.nstt.rules.total_sr import apply_total_sr
        for val in ["OTHER", "VENDOR", "MGMT", "", None]:
            rec = make_record(ATTRIBUTEDTO=val)
            apply_total_sr([rec])
            assert rec["is_total_sr"] is False, f"Expected False for ATTRIBUTEDTO={val!r}"

    def test_case_insensitive(self):
        from app.services.nstt.rules.total_sr import apply_total_sr
        rec = make_record(ATTRIBUTEDTO="txn")
        apply_total_sr([rec])
        assert rec["is_total_sr"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# Rule 2: NSTT Count
# ═══════════════════════════════════════════════════════════════════════════════

class TestNsttCount:
    def test_non_blank_incidentid_is_nstt(self):
        from app.services.nstt.rules.nstt_count import apply_nstt_count
        rec = make_record(is_total_sr=True, INCIDENTID="INC001")
        apply_nstt_count([rec])
        assert rec["is_nstt"] is True

    def test_blank_incidentid_not_nstt(self):
        from app.services.nstt.rules.nstt_count import apply_nstt_count
        rec = make_record(is_total_sr=True, INCIDENTID="")
        apply_nstt_count([rec])
        assert rec["is_nstt"] is False

    def test_non_total_sr_not_nstt(self):
        from app.services.nstt.rules.nstt_count import apply_nstt_count
        rec = make_record(is_total_sr=False, INCIDENTID="INC001")
        apply_nstt_count([rec])
        assert rec["is_nstt"] is False

    def test_none_incidentid_not_nstt(self):
        from app.services.nstt.rules.nstt_count import apply_nstt_count
        rec = make_record(is_total_sr=True, INCIDENTID=None)
        apply_nstt_count([rec])
        assert rec["is_nstt"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# Rule 3: Capture Type
# ═══════════════════════════════════════════════════════════════════════════════

class TestCaptureType:
    def test_non_blank_auto_nstt_is_automation(self):
        from app.services.nstt.rules.capture_type import apply_capture_type
        rec = make_record(is_nstt=True, AUTOMATION_UPDATE_NSTT_NUMBER="INC001")
        apply_capture_type([rec])
        assert rec["capture_type"] == "Automation"

    def test_blank_auto_nstt_is_manual(self):
        from app.services.nstt.rules.capture_type import apply_capture_type
        rec = make_record(is_nstt=True, AUTOMATION_UPDATE_NSTT_NUMBER="")
        apply_capture_type([rec])
        assert rec["capture_type"] == "Manual"

    def test_none_auto_nstt_is_manual(self):
        from app.services.nstt.rules.capture_type import apply_capture_type
        rec = make_record(is_nstt=True, AUTOMATION_UPDATE_NSTT_NUMBER=None)
        apply_capture_type([rec])
        assert rec["capture_type"] == "Manual"

    def test_non_nstt_gets_null_capture_type(self):
        from app.services.nstt.rules.capture_type import apply_capture_type
        rec = make_record(is_nstt=False)
        apply_capture_type([rec])
        assert rec["capture_type"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# Rule 4: Automation Classifier — ORDER MATTERS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAutomationClassifier:
    def test_resolved_nstt_when_src_after_uptime(self):
        """SRCREATIONTIME > UP_TIME → Resolved NSTT (highest priority)."""
        from app.services.nstt.rules.automation_classifier import apply_automation_classifier
        rec = make_record(
            capture_type="Automation",
            INCIDENTID="INC001",
            AUTOMATION_UPDATE_NSTT_NUMBER="INC001",  # would be "Same" if not resolved first
            SRCREATIONTIME="2026-09-02 10:00:00",
            UP_TIME="2026-09-01 15:00:00",
        )
        apply_automation_classifier([rec])
        assert rec["nstt_type"] == "Resolved NSTT", "Resolved must take priority over Same"

    def test_same_nstt_when_ids_match(self):
        """INCIDENTID == AUTOMATION_UPDATE_NSTT_NUMBER → Same NSTT."""
        from app.services.nstt.rules.automation_classifier import apply_automation_classifier
        rec = make_record(
            capture_type="Automation",
            INCIDENTID="INC001",
            AUTOMATION_UPDATE_NSTT_NUMBER="INC001",
            SRCREATIONTIME="2026-09-01 10:00:00",
            UP_TIME="2026-09-01 15:00:00",  # UP_TIME > SRCREATIONTIME → not Resolved
        )
        apply_automation_classifier([rec])
        assert rec["nstt_type"] == "Same NSTT"

    def test_different_nstt_when_ids_differ(self):
        """INCIDENTID != AUTOMATION_UPDATE_NSTT_NUMBER → Different NSTT."""
        from app.services.nstt.rules.automation_classifier import apply_automation_classifier
        rec = make_record(
            capture_type="Automation",
            INCIDENTID="INC001",
            AUTOMATION_UPDATE_NSTT_NUMBER="INC999",  # different
            SRCREATIONTIME="2026-09-01 10:00:00",
            UP_TIME="2026-09-01 15:00:00",
        )
        apply_automation_classifier([rec])
        assert rec["nstt_type"] == "Different NSTT"

    def test_manual_records_not_classified(self):
        """Manual capture_type records should not have nstt_type set by this rule."""
        from app.services.nstt.rules.automation_classifier import apply_automation_classifier
        rec = make_record(capture_type="Manual")
        rec["nstt_type"] = None  # ensure it starts null
        apply_automation_classifier([rec])
        assert rec["nstt_type"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# Rule 5: Same NSTT
# ═══════════════════════════════════════════════════════════════════════════════

class TestSameNstt:
    def test_im_auto_sa(self):
        from app.services.nstt.rules.same_nstt import apply_same_nstt
        rec = make_record(nstt_type="Same NSTT", FACTORY="IM", AUTO_ALLOCATION="yes", INCIDENT_IMPACT="SA")
        apply_same_nstt([rec])
        assert rec["factory_type"] == "IM"
        assert rec["allocation_type"] == "Auto"
        assert rec["impact_type"] == "SA"

    def test_non_im_manual_nsa(self):
        from app.services.nstt.rules.same_nstt import apply_same_nstt
        rec = make_record(nstt_type="Same NSTT", FACTORY="Non IM", AUTO_ALLOCATION="no", INCIDENT_IMPACT="NSA")
        apply_same_nstt([rec])
        assert rec["factory_type"] == "Non IM"
        assert rec["allocation_type"] == "Manual"
        assert rec["impact_type"] == "NSA"

    def test_factory_case_insensitive(self):
        from app.services.nstt.rules.same_nstt import apply_same_nstt
        rec = make_record(nstt_type="Same NSTT", FACTORY="im")
        apply_same_nstt([rec])
        assert rec["factory_type"] == "IM"

    def test_non_same_nstt_gets_nulls(self):
        from app.services.nstt.rules.same_nstt import apply_same_nstt
        rec = make_record(nstt_type="Different NSTT")
        apply_same_nstt([rec])
        assert rec["factory_type"] is None
        assert rec["allocation_type"] is None
        assert rec["impact_type"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# Rule 6: Different NSTT — exactly 4 categories
# ═══════════════════════════════════════════════════════════════════════════════

class TestDifferentNstt:
    def test_four_category_labels_exactly(self):
        """Verifies the 4 exact spec label strings are used."""
        from app.services.nstt.rules.different_nstt import (
            DIFF_CAT_INCIDENT_SA_AUTO_NSA,
            DIFF_CAT_INCIDENT_NSA_AUTO_SA,
            DIFF_CAT_BOTH_NSA,
            DIFF_CAT_BOTH_SA,
        )
        assert DIFF_CAT_INCIDENT_SA_AUTO_NSA == "Incident SA auto NSA"
        assert DIFF_CAT_INCIDENT_NSA_AUTO_SA == "Incident NSA auto SA"
        assert DIFF_CAT_BOTH_NSA == "Both NSA"
        assert DIFF_CAT_BOTH_SA == "Both SA"

    def test_incident_sa_auto_nsa(self):
        from app.services.nstt.rules.different_nstt import apply_different_nstt
        rec = make_record(nstt_type="Different NSTT", INCIDENTID="INC001", INCIDENT_IMPACT="SA",
                          AUTOMATION_UPDATE_NSTT_NUMBER="INC999")
        remedy_map = {"INC999": "NSA"}
        apply_different_nstt([rec], remedy_impact_map=remedy_map)
        assert rec["diff_nstt_category"] == "Incident SA auto NSA"

    def test_incident_nsa_auto_sa(self):
        from app.services.nstt.rules.different_nstt import apply_different_nstt
        rec = make_record(nstt_type="Different NSTT", INCIDENTID="INC001", INCIDENT_IMPACT="NSA",
                          AUTOMATION_UPDATE_NSTT_NUMBER="INC999")
        remedy_map = {"INC999": "SA"}
        apply_different_nstt([rec], remedy_impact_map=remedy_map)
        assert rec["diff_nstt_category"] == "Incident NSA auto SA"

    def test_both_nsa(self):
        from app.services.nstt.rules.different_nstt import apply_different_nstt
        rec = make_record(nstt_type="Different NSTT", INCIDENTID="INC001", INCIDENT_IMPACT="NSA",
                          AUTOMATION_UPDATE_NSTT_NUMBER="INC999")
        remedy_map = {"INC999": "NSA"}
        apply_different_nstt([rec], remedy_impact_map=remedy_map)
        assert rec["diff_nstt_category"] == "Both NSA"

    def test_both_sa(self):
        from app.services.nstt.rules.different_nstt import apply_different_nstt
        rec = make_record(nstt_type="Different NSTT", INCIDENTID="INC001", INCIDENT_IMPACT="SA",
                          AUTOMATION_UPDATE_NSTT_NUMBER="INC999")
        remedy_map = {"INC999": "SA"}
        apply_different_nstt([rec], remedy_impact_map=remedy_map)
        assert rec["diff_nstt_category"] == "Both SA"

    def test_non_different_nstt_gets_null(self):
        from app.services.nstt.rules.different_nstt import apply_different_nstt
        rec = make_record(nstt_type="Same NSTT")
        apply_different_nstt([rec])
        assert rec["diff_nstt_category"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# Rule 7: Resolved NSTT
# ═══════════════════════════════════════════════════════════════════════════════

class TestResolvedNstt:
    def test_im_auto(self):
        from app.services.nstt.rules.resolved_nstt import apply_resolved_nstt
        rec = make_record(nstt_type="Resolved NSTT", FACTORY="IM", AUTO_ALLOCATION="yes")
        apply_resolved_nstt([rec])
        assert rec["factory_type"] == "IM"
        assert rec["allocation_type"] == "Auto"

    def test_non_im_manual(self):
        from app.services.nstt.rules.resolved_nstt import apply_resolved_nstt
        rec = make_record(nstt_type="Resolved NSTT", FACTORY="Non IM", AUTO_ALLOCATION="no")
        apply_resolved_nstt([rec])
        assert rec["factory_type"] == "Non IM"
        assert rec["allocation_type"] == "Manual"

    def test_non_resolved_not_touched(self):
        from app.services.nstt.rules.resolved_nstt import apply_resolved_nstt
        rec = make_record(nstt_type="Same NSTT")
        # Should not set factory_type or allocation_type
        apply_resolved_nstt([rec])
        assert "factory_type" not in rec or rec.get("factory_type") is None


# ═══════════════════════════════════════════════════════════════════════════════
# Rule 8: Manual Classifier
# ═══════════════════════════════════════════════════════════════════════════════

class TestManualClassifier:
    def test_resolved_when_src_after_uptime(self):
        """SRCREATIONTIME > UP_TIME → timing_type = 'Resolved'."""
        from app.services.nstt.rules.manual_classifier import apply_manual_classifier
        rec = make_record(
            capture_type="Manual",
            SRCREATIONTIME="2026-09-02 10:00:00",
            UP_TIME="2026-09-01 15:00:00",
            **{"Submit Date": "2026-09-01 09:00:00"},
            INCIDENT_IMPACT="SA",
        )
        apply_manual_classifier([rec])
        assert rec["timing_type"] == "Resolved"
        assert rec["impact_type"] == "SA"

    def test_before_sr_creation(self):
        """SRCREATIONTIME > Submit Date (but <= UP_TIME) → 'Before SR Creation'."""
        from app.services.nstt.rules.manual_classifier import apply_manual_classifier
        rec = make_record(
            capture_type="Manual",
            SRCREATIONTIME="2026-09-01 10:00:00",
            UP_TIME="2026-09-01 15:00:00",  # UP_TIME > SRCREATIONTIME → not Resolved
            **{"Submit Date": "2026-09-01 08:00:00"},  # SRCREATIONTIME > Submit Date
            INCIDENT_IMPACT="NSA",
        )
        apply_manual_classifier([rec])
        assert rec["timing_type"] == "Before SR Creation"
        assert rec["impact_type"] == "NSA"

    def test_after_sr_creation(self):
        """SRCREATIONTIME < Submit Date → 'After SR Creation'."""
        from app.services.nstt.rules.manual_classifier import apply_manual_classifier
        rec = make_record(
            capture_type="Manual",
            SRCREATIONTIME="2026-09-01 07:00:00",
            UP_TIME="2026-09-01 15:00:00",
            **{"Submit Date": "2026-09-01 09:00:00"},  # SRCREATIONTIME < Submit Date
            INCIDENT_IMPACT="SA",
        )
        apply_manual_classifier([rec])
        assert rec["timing_type"] == "After SR Creation"

    def test_automation_not_classified(self):
        from app.services.nstt.rules.manual_classifier import apply_manual_classifier
        rec = make_record(capture_type="Automation")
        apply_manual_classifier([rec])
        assert rec["timing_type"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# Rule 9: Wrong NSTT — CONTAINS check (NOT equality)
# ═══════════════════════════════════════════════════════════════════════════════

class TestWrongNstt:
    def test_exact_label_automation(self):
        """Automation + ANG + TXN → exact spec label."""
        from app.services.nstt.rules.wrong_nstt import apply_wrong_nstt, WRONG_NSTT_AUTOMATION
        rec = make_record(
            is_nstt=True,
            capture_type="Automation",
            ASSIGNED_SUPPORT_COMPANY="ANG Vendor Co",
            ATTRIBUTEDTO="TXN_Infra",
        )
        apply_wrong_nstt([rec])
        assert rec["exception_type"] == "wrong NSTT Attached by automation Ang in TXN Attribution"
        assert rec["exception_type"] == WRONG_NSTT_AUTOMATION

    def test_exact_label_manual(self):
        """Manual + ANG + TXN → exact spec label."""
        from app.services.nstt.rules.wrong_nstt import apply_wrong_nstt, WRONG_NSTT_ENGINEER
        rec = make_record(
            is_nstt=True,
            capture_type="Manual",
            ASSIGNED_SUPPORT_COMPANY="ANOTHER_ANG_COMPANY",
            ATTRIBUTEDTO="TXN",
        )
        apply_wrong_nstt([rec])
        assert rec["exception_type"] == "wrong NSTT Attached by Engineer Ang in TXN Attribution"
        assert rec["exception_type"] == WRONG_NSTT_ENGINEER

    def test_contains_not_equality(self):
        """CONTAINS: 'ANG_VENDOR' contains 'ANG', should match."""
        from app.services.nstt.rules.wrong_nstt import apply_wrong_nstt
        rec = make_record(
            is_nstt=True,
            capture_type="Automation",
            ASSIGNED_SUPPORT_COMPANY="ANG_VENDOR",  # substring match
            ATTRIBUTEDTO="TXN_Hardware",             # substring match
        )
        apply_wrong_nstt([rec])
        assert rec["exception_type"] is not None

    def test_no_match_without_ang(self):
        """Missing ANG → no exception."""
        from app.services.nstt.rules.wrong_nstt import apply_wrong_nstt
        rec = make_record(
            is_nstt=True,
            capture_type="Automation",
            ASSIGNED_SUPPORT_COMPANY="OTHER_COMPANY",  # no ANG
            ATTRIBUTEDTO="TXN",
        )
        apply_wrong_nstt([rec])
        assert rec["exception_type"] is None

    def test_no_match_without_txn(self):
        """Missing TXN → no exception."""
        from app.services.nstt.rules.wrong_nstt import apply_wrong_nstt
        rec = make_record(
            is_nstt=True,
            capture_type="Automation",
            ASSIGNED_SUPPORT_COMPANY="ANG_VENDOR",
            ATTRIBUTEDTO="TNL",  # not TXN
        )
        apply_wrong_nstt([rec])
        assert rec["exception_type"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# Rule 10: Failure Analysis — CONTAINS checks
# ═══════════════════════════════════════════════════════════════════════════════

class TestFailureAnalysis:
    def test_not_found_in_remedy(self):
        from app.services.nstt.rules.failure_analysis import apply_failure_analysis, FAIL_NOT_FOUND
        rec = make_record(is_nstt=True, capture_type="Manual", is_matched=False)
        apply_failure_analysis([rec])
        assert rec["failure_category"] == FAIL_NOT_FOUND

    def test_ring_failure_contains(self):
        """'Ring failure' substring in DESCRIPTION → Ring Failure."""
        from app.services.nstt.rules.failure_analysis import apply_failure_analysis, FAIL_RING
        rec = make_record(
            is_nstt=True, capture_type="Manual", is_matched=True,
            DESCRIPTION="Major Ring Failure detected on node"
        )
        apply_failure_analysis([rec])
        assert rec["failure_category"] == FAIL_RING

    def test_ring_failure_case_insensitive(self):
        """'RING' in uppercase, space-stripped match."""
        from app.services.nstt.rules.failure_analysis import apply_failure_analysis, FAIL_RING
        rec = make_record(
            is_nstt=True, capture_type="Manual", is_matched=True,
            DESCRIPTION="ring issue observed"
        )
        apply_failure_analysis([rec])
        assert rec["failure_category"] == FAIL_RING

    def test_section_failure_contains(self):
        """'Section' substring in DESCRIPTION → Section Failure."""
        from app.services.nstt.rules.failure_analysis import apply_failure_analysis, FAIL_SECTION
        rec = make_record(
            is_nstt=True, capture_type="Manual", is_matched=True,
            DESCRIPTION="Section 12 has degraded performance"
        )
        apply_failure_analysis([rec])
        assert rec["failure_category"] == FAIL_SECTION

    def test_unstitched_exact_phrase(self):
        """AUTOMATION_RCA_CONCLUSION_TEXT contains exact phrase → Unstitched."""
        from app.services.nstt.rules.failure_analysis import apply_failure_analysis, FAIL_UNSTITCHED
        rec = make_record(
            is_nstt=True, capture_type="Manual", is_matched=True,
            AUTOMATION_RCA_CONCLUSION_TEXT="FLT Observations for Unstitched LSI - detected",
        )
        apply_failure_analysis([rec])
        assert rec["failure_category"] == FAIL_UNSTITCHED

    def test_not_found_takes_priority_over_ring(self):
        """is_matched=False has higher priority than ring keywords in DESCRIPTION."""
        from app.services.nstt.rules.failure_analysis import apply_failure_analysis, FAIL_NOT_FOUND
        rec = make_record(
            is_nstt=True, capture_type="Manual", is_matched=False,
            DESCRIPTION="Ring failure and Section problem"
        )
        apply_failure_analysis([rec])
        assert rec["failure_category"] == FAIL_NOT_FOUND

    def test_no_failure_category_for_automation(self):
        """Automation records are not in failure analysis scope."""
        from app.services.nstt.rules.failure_analysis import apply_failure_analysis
        rec = make_record(is_nstt=True, capture_type="Automation", DESCRIPTION="Ring failure")
        apply_failure_analysis([rec])
        assert rec["failure_category"] is None

    def test_no_failure_category_when_no_conditions_match(self):
        from app.services.nstt.rules.failure_analysis import apply_failure_analysis
        rec = make_record(
            is_nstt=True, capture_type="Manual", is_matched=True,
            DESCRIPTION="Normal planned maintenance",
            AUTOMATION_RCA_CONCLUSION_TEXT="",
        )
        apply_failure_analysis([rec])
        assert rec["failure_category"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# Full Rule Engine Orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuleEngineOrchestrator:
    def _build_master_response(self, records):
        return {
            "records": records,
            "total_records": len(records),
            "columns": list(records[0].keys()) if records else [],
        }

    def test_empty_records_returns_zero_stats(self):
        from app.services.nstt.rule_engine import run_rule_engine
        result = run_rule_engine({"records": [], "total_records": 0, "columns": []})
        stats = result["classification_stats"]
        assert stats["total_sr"] == 0
        assert stats["nstt_count"] == 0

    def test_full_automation_same_nstt_flow(self):
        """Full pipeline: TXN → Automation → Same NSTT → IM Auto SA"""
        from app.services.nstt.rule_engine import run_rule_engine
        records = [make_record(
            ATTRIBUTEDTO="TXN",
            INCIDENTID="INC001",
            AUTOMATION_UPDATE_NSTT_NUMBER="INC001",
            FACTORY="IM",
            AUTO_ALLOCATION="yes",
            INCIDENT_IMPACT="SA",
            SRCREATIONTIME="2026-09-01 10:00:00",
            UP_TIME="2026-09-01 15:00:00",
        )]
        result = run_rule_engine(self._build_master_response(records))
        rec = result["records"][0]
        assert rec["is_total_sr"] is True
        assert rec["is_nstt"] is True
        assert rec["capture_type"] == "Automation"
        assert rec["nstt_type"] == "Same NSTT"
        assert rec["factory_type"] == "IM"
        assert rec["allocation_type"] == "Auto"
        assert rec["impact_type"] == "SA"
        stats = result["classification_stats"]
        assert stats["total_sr"] == 1
        assert stats["nstt_count"] == 1
        assert stats["automation_count"] == 1
        assert stats["same_nstt"] == 1

    def test_resolved_beats_same_in_orchestrator(self):
        """Order test: Resolved NSTT must be classified before Same NSTT."""
        from app.services.nstt.rule_engine import run_rule_engine
        records = [make_record(
            ATTRIBUTEDTO="TXN",
            INCIDENTID="INC001",
            AUTOMATION_UPDATE_NSTT_NUMBER="INC001",  # would be Same if not resolved
            SRCREATIONTIME="2026-09-02 10:00:00",  # AFTER UP_TIME → Resolved
            UP_TIME="2026-09-01 15:00:00",
        )]
        result = run_rule_engine(self._build_master_response(records))
        rec = result["records"][0]
        assert rec["nstt_type"] == "Resolved NSTT", "Resolved must win over Same NSTT"

    def test_manual_flow(self):
        """Full pipeline: TXN → Manual → Before SR Creation → SA"""
        from app.services.nstt.rule_engine import run_rule_engine
        records = [make_record(
            ATTRIBUTEDTO="TXN",
            INCIDENTID="INC002",
            AUTOMATION_UPDATE_NSTT_NUMBER="",  # Manual
            FACTORY="Non IM",
            AUTO_ALLOCATION="no",
            INCIDENT_IMPACT="SA",
            SRCREATIONTIME="2026-09-01 10:00:00",
            UP_TIME="2026-09-01 15:00:00",
            **{"Submit Date": "2026-09-01 08:00:00"},  # SRCREATIONTIME > Submit Date
        )]
        result = run_rule_engine(self._build_master_response(records))
        rec = result["records"][0]
        assert rec["capture_type"] == "Manual"
        assert rec["timing_type"] == "Before SR Creation"
        assert rec["impact_type"] == "SA"

    def test_wrong_nstt_exception_in_orchestrator(self):
        """Wrong NSTT should be flagged in full pipeline."""
        from app.services.nstt.rule_engine import run_rule_engine
        records = [make_record(
            ATTRIBUTEDTO="TXN",
            INCIDENTID="INC003",
            AUTOMATION_UPDATE_NSTT_NUMBER="INC003",
            ASSIGNED_SUPPORT_COMPANY="ANG-XYZ",
        )]
        result = run_rule_engine(self._build_master_response(records))
        rec = result["records"][0]
        assert rec["exception_type"] == "wrong NSTT Attached by automation Ang in TXN Attribution"
        assert result["classification_stats"]["wrong_nstt_count"] == 1

    def test_failure_analysis_in_orchestrator(self):
        """Ring failure should be detected in full pipeline for Manual records."""
        from app.services.nstt.rule_engine import run_rule_engine
        records = [make_record(
            ATTRIBUTEDTO="TXN",
            INCIDENTID="INC004",
            AUTOMATION_UPDATE_NSTT_NUMBER="",  # Manual
            DESCRIPTION="Ring Failure detected on the node",
            is_matched=True,
        )]
        result = run_rule_engine(self._build_master_response(records))
        rec = result["records"][0]
        assert rec["failure_category"] == "Ring Failure"
        assert result["classification_stats"]["failure_count"] == 1

    def test_non_total_sr_excluded(self):
        """Records with non-NSTT ATTRIBUTEDTO must not be counted in NSTT metrics."""
        from app.services.nstt.rule_engine import run_rule_engine
        records = [make_record(ATTRIBUTEDTO="VENDOR")]
        result = run_rule_engine(self._build_master_response(records))
        rec = result["records"][0]
        assert rec["is_total_sr"] is False
        assert rec["is_nstt"] is False
        assert result["classification_stats"]["total_sr"] == 0

    def test_classification_stats_consistency(self):
        """automation_count + manual_count should equal nstt_count."""
        from app.services.nstt.rule_engine import run_rule_engine
        records = [
            make_record(ATTRIBUTEDTO="TXN", INCIDENTID=f"INC{i:03d}",
                        AUTOMATION_UPDATE_NSTT_NUMBER=f"INC{i:03d}" if i % 2 == 0 else "")
            for i in range(10)
        ]
        result = run_rule_engine(self._build_master_response(records))
        stats = result["classification_stats"]
        assert stats["automation_count"] + stats["manual_count"] == stats["nstt_count"]
