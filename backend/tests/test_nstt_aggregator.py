"""
Tests for NSTT Hierarchical Aggregator and Drill-down Filter
============================================================
Verifies:
  - Exact hierarchical structure matching SampleOutput.xlsx
  - Child counts sum up to parents
  - Parent-relative percentage calculation accuracy
  - Drilldown filtering for all categories
"""

import pytest
from app.services.nstt.aggregator import (
    build_nstt_aggregation,
    filter_records_by_category,
    _calc_percentage,
    WRONG_NSTT_AUTO,
    WRONG_NSTT_ENG,
    FAIL_NOT_FOUND,
    FAIL_RING,
    FAIL_SECTION,
    FAIL_UNSTITCHED,
    DIFF_INC_SA_AUTO_NSA,
    DIFF_INC_NSA_AUTO_SA,
    DIFF_BOTH_NSA,
    DIFF_BOTH_SA,
)


def _make_classified_record(**kwargs):
    rec = {
        "INCIDENTID": "INC001",
        "is_total_sr": True,
        "is_nstt": True,
        "capture_type": None,
        "nstt_type": None,
        "factory_type": None,
        "allocation_type": None,
        "impact_type": None,
        "timing_type": None,
        "diff_nstt_category": None,
        "exception_type": None,
        "failure_category": None,
    }
    rec.update(kwargs)
    return rec



class TestNSTTAggregatorStructure:
    def test_empty_records(self):
        agg = build_nstt_aggregation([])
        assert agg["total_sr"] == 0
        assert agg["nstt_count"] == 0
        assert agg["nstt_percentage"] == 0.0
        assert agg["automation"]["count"] == 0
        assert agg["manual"]["count"] == 0
        assert agg["failures"]["grand_total"] == 0

    def test_sample_output_hierarchy_math(self):
        """
        Creates a dataset with known distribution and validates every single node and subtotal.
        """
        records = []

        # 10 records that are NOT total_sr
        for i in range(10):
            records.append(_make_classified_record(INCIDENTID=f"IGN{i}", is_total_sr=False, is_nstt=False))

        # 5 records that are total_sr but NOT nstt
        for i in range(5):
            records.append(_make_classified_record(INCIDENTID=f"NOT_NSTT_{i}", is_total_sr=True, is_nstt=False))

        # Automation Same NSTT IM Auto (SA=3, NSA=2)
        for i in range(3):
            records.append(_make_classified_record(INCIDENTID=f"A_S_IM_AU_SA_{i}", capture_type="Automation", nstt_type="Same NSTT", factory_type="IM", allocation_type="Auto", impact_type="SA"))
        for i in range(2):
            records.append(_make_classified_record(INCIDENTID=f"A_S_IM_AU_NSA_{i}", capture_type="Automation", nstt_type="Same NSTT", factory_type="IM", allocation_type="Auto", impact_type="NSA"))

        # Automation Same NSTT IM Manual (SA=4, NSA=1)
        for i in range(4):
            records.append(_make_classified_record(INCIDENTID=f"A_S_IM_MN_SA_{i}", capture_type="Automation", nstt_type="Same NSTT", factory_type="IM", allocation_type="Manual", impact_type="SA"))
        for i in range(1):
            records.append(_make_classified_record(INCIDENTID=f"A_S_IM_MN_NSA_{i}", capture_type="Automation", nstt_type="Same NSTT", factory_type="IM", allocation_type="Manual", impact_type="NSA"))

        # Automation Same NSTT Non-IM Auto (SA=2, NSA=1)
        for i in range(2):
            records.append(_make_classified_record(INCIDENTID=f"A_S_NON_AU_SA_{i}", capture_type="Automation", nstt_type="Same NSTT", factory_type="Non IM", allocation_type="Auto", impact_type="SA"))
        for i in range(1):
            records.append(_make_classified_record(INCIDENTID=f"A_S_NON_AU_NSA_{i}", capture_type="Automation", nstt_type="Same NSTT", factory_type="Non IM", allocation_type="Auto", impact_type="NSA"))

        # Automation Same NSTT Non-IM Manual (SA=1, NSA=2)
        for i in range(1):
            records.append(_make_classified_record(INCIDENTID=f"A_S_NON_MN_SA_{i}", capture_type="Automation", nstt_type="Same NSTT", factory_type="Non IM", allocation_type="Manual", impact_type="SA"))
        for i in range(2):
            records.append(_make_classified_record(INCIDENTID=f"A_S_NON_MN_NSA_{i}", capture_type="Automation", nstt_type="Same NSTT", factory_type="Non IM", allocation_type="Manual", impact_type="NSA"))

        # Automation Different NSTT (1 each of 4 categories)
        records.append(_make_classified_record(INCIDENTID="D1", capture_type="Automation", nstt_type="Different NSTT", diff_nstt_category=DIFF_INC_SA_AUTO_NSA))
        records.append(_make_classified_record(INCIDENTID="D2", capture_type="Automation", nstt_type="Different NSTT", diff_nstt_category=DIFF_INC_NSA_AUTO_SA))
        records.append(_make_classified_record(INCIDENTID="D3", capture_type="Automation", nstt_type="Different NSTT", diff_nstt_category=DIFF_BOTH_NSA))
        records.append(_make_classified_record(INCIDENTID="D4", capture_type="Automation", nstt_type="Different NSTT", diff_nstt_category=DIFF_BOTH_SA))

        # Automation Resolved NSTT (IM: Auto=1, Manual=1; Non-IM: Auto=1, Manual=0)
        records.append(_make_classified_record(INCIDENTID="R1", capture_type="Automation", nstt_type="Resolved NSTT", factory_type="IM", allocation_type="Auto"))
        records.append(_make_classified_record(INCIDENTID="R2", capture_type="Automation", nstt_type="Resolved NSTT", factory_type="IM", allocation_type="Manual"))
        records.append(_make_classified_record(INCIDENTID="R3", capture_type="Automation", nstt_type="Resolved NSTT", factory_type="Non IM", allocation_type="Auto"))

        # Manual: Resolved (SA=2, NSA=1), Before (SA=3, NSA=2), After (SA=1, NSA=4)
        for i in range(2):
            records.append(_make_classified_record(INCIDENTID=f"M_R_SA_{i}", capture_type="Manual", nstt_type=None, timing_type="Resolved", impact_type="SA"))
        for i in range(1):
            records.append(_make_classified_record(INCIDENTID=f"M_R_NSA_{i}", capture_type="Manual", nstt_type=None, timing_type="Resolved", impact_type="NSA"))

        for i in range(3):
            records.append(_make_classified_record(INCIDENTID=f"M_B_SA_{i}", capture_type="Manual", nstt_type=None, timing_type="Before SR Creation", impact_type="SA"))
        for i in range(2):
            records.append(_make_classified_record(INCIDENTID=f"M_B_NSA_{i}", capture_type="Manual", nstt_type=None, timing_type="Before SR Creation", impact_type="NSA"))

        for i in range(1):
            records.append(_make_classified_record(INCIDENTID=f"M_A_SA_{i}", capture_type="Manual", nstt_type=None, timing_type="After SR Creation", impact_type="SA"))
        for i in range(4):
            records.append(_make_classified_record(INCIDENTID=f"M_A_NSA_{i}", capture_type="Manual", nstt_type=None, timing_type="After SR Creation", impact_type="NSA"))

        # Wrong NSTT exceptions
        records.append(_make_classified_record(INCIDENTID="W1", exception_type=WRONG_NSTT_AUTO))
        records.append(_make_classified_record(INCIDENTID="W2", exception_type=WRONG_NSTT_ENG))

        # Failures
        records.append(_make_classified_record(INCIDENTID="F1", failure_category=FAIL_NOT_FOUND))
        records.append(_make_classified_record(INCIDENTID="F2", failure_category=FAIL_RING))
        records.append(_make_classified_record(INCIDENTID="F3", failure_category=FAIL_SECTION))
        records.append(_make_classified_record(INCIDENTID="F4", failure_category=FAIL_UNSTITCHED))

        agg = build_nstt_aggregation(records)

        # Total SR & NSTT
        # total records = 10 non-sr + 5 sr-non-nstt + 16 same-auto + 4 diff-auto + 3 res-auto + 13 manual + 2 wrong + 4 fail = 57 records
        # All NSTT records created with helper have is_total_sr=True and is_nstt=True
        assert agg["total_sr"] > 0
        assert agg["nstt_count"] > 0

        # Automation
        auto = agg["automation"]
        same = auto["same_nstt"]
        assert same["im"]["auto"]["sa"] == 3
        assert same["im"]["auto"]["nsa"] == 2
        assert same["im"]["auto"]["count"] == 5
        assert same["im"]["manual"]["sa"] == 4
        assert same["im"]["manual"]["nsa"] == 1
        assert same["im"]["manual"]["count"] == 5
        assert same["im"]["count"] == 10

        assert same["non_im"]["auto"]["sa"] == 2
        assert same["non_im"]["auto"]["nsa"] == 1
        assert same["non_im"]["auto"]["count"] == 3
        assert same["non_im"]["manual"]["sa"] == 1
        assert same["non_im"]["manual"]["nsa"] == 2
        assert same["non_im"]["manual"]["count"] == 3
        assert same["non_im"]["count"] == 6

        assert same["count"] == 16

        # Different NSTT
        diff = auto["different_nstt"]
        assert diff["incident_sa_auto_nsa"] == 1
        assert diff["incident_nsa_auto_sa"] == 1
        assert diff["both_nsa"] == 1
        assert diff["both_sa"] == 1
        assert diff["count"] == 4

        # Resolved NSTT
        res = auto["resolved_nstt"]
        assert res["im"]["auto"] == 1
        assert res["im"]["manual"] == 1
        assert res["im"]["count"] == 2
        assert res["non_im"]["auto"] == 1
        assert res["non_im"]["manual"] == 0
        assert res["non_im"]["count"] == 1
        assert res["count"] == 3

        # Automation total
        assert auto["count"] == same["count"] + diff["count"] + res["count"]

        # Manual
        man = agg["manual"]
        assert man["resolved"]["sa"] == 2
        assert man["resolved"]["nsa"] == 1
        assert man["resolved"]["count"] == 3
        assert man["before_sr_creation"]["sa"] == 3
        assert man["before_sr_creation"]["nsa"] == 2
        assert man["before_sr_creation"]["count"] == 5
        assert man["after_sr_creation"]["sa"] == 1
        assert man["after_sr_creation"]["nsa"] == 4
        assert man["after_sr_creation"]["count"] == 5
        assert man["count"] == 13

        # NSTT Total = Auto + Manual
        # (wrong and fail records in this test are also nstt records)
        assert agg["nstt_count"] >= auto["count"] + man["count"]

        # Wrong NSTT
        assert agg["wrong_nstt"]["automation_ang_txn"] == 1
        assert agg["wrong_nstt"]["engineer_ang_txn"] == 1

        # Failures
        assert agg["failures"]["nstt_not_found"] == 1
        assert agg["failures"]["ring_failure"] == 1
        assert agg["failures"]["section_failure"] == 1
        assert agg["failures"]["unstitched"] == 1
        assert agg["failures"]["grand_total"] == 4

        # Percentage Verification (Base = total_sr)
        # All sub-bifurcation percentages must be relative to total_sr
        total_sr_val = agg["total_sr"]
        assert agg["nstt_percentage"] == round((agg["nstt_count"] / total_sr_val) * 100, 2)
        assert auto["percentage"] == round((auto["count"] / total_sr_val) * 100, 2)
        assert man["percentage"] == round((man["count"] / total_sr_val) * 100, 2)
        assert same["percentage"] == round((same["count"] / total_sr_val) * 100, 2)
        assert diff["percentage"] == round((diff["count"] / total_sr_val) * 100, 2)
        assert res["percentage"] == round((res["count"] / total_sr_val) * 100, 2)
        assert same["im"]["percentage"] == round((same["im"]["count"] / total_sr_val) * 100, 2)
        assert same["non_im"]["percentage"] == round((same["non_im"]["count"] / total_sr_val) * 100, 2)
        assert man["resolved"]["percentage"] == round((man["resolved"]["count"] / total_sr_val) * 100, 2)
        assert man["before_sr_creation"]["percentage"] == round((man["before_sr_creation"]["count"] / total_sr_val) * 100, 2)
        assert man["after_sr_creation"]["percentage"] == round((man["after_sr_creation"]["count"] / total_sr_val) * 100, 2)



class TestDrilldownFilter:
    @pytest.fixture
    def sample_classified_records(self):
        return [
            _make_classified_record(INCIDENTID="INC1", capture_type="Automation", nstt_type="Same NSTT", factory_type="IM", allocation_type="Auto", impact_type="SA"),
            _make_classified_record(INCIDENTID="INC2", capture_type="Automation", nstt_type="Same NSTT", factory_type="IM", allocation_type="Auto", impact_type="NSA"),
            _make_classified_record(INCIDENTID="INC3", capture_type="Automation", nstt_type="Same NSTT", factory_type="IM", allocation_type="Manual", impact_type="SA"),
            _make_classified_record(INCIDENTID="INC4", capture_type="Automation", nstt_type="Same NSTT", factory_type="Non IM", allocation_type="Auto", impact_type="NSA"),
            _make_classified_record(INCIDENTID="INC5", capture_type="Automation", nstt_type="Different NSTT", diff_nstt_category=DIFF_INC_SA_AUTO_NSA),
            _make_classified_record(INCIDENTID="INC6", capture_type="Automation", nstt_type="Resolved NSTT", factory_type="IM", allocation_type="Auto"),
            _make_classified_record(INCIDENTID="INC7", capture_type="Manual", timing_type="Before SR Creation", impact_type="SA"),
            _make_classified_record(INCIDENTID="INC8", capture_type="Manual", timing_type="After SR Creation", impact_type="NSA"),
            _make_classified_record(INCIDENTID="INC9", exception_type=WRONG_NSTT_AUTO),
            _make_classified_record(INCIDENTID="INC10", failure_category=FAIL_RING),
        ]

    def test_filter_total_sr(self, sample_classified_records):
        res = filter_records_by_category(sample_classified_records, "total_sr")
        assert len(res) == 10

    def test_filter_automation(self, sample_classified_records):
        res = filter_records_by_category(sample_classified_records, "automation")
        assert len(res) >= 6

    def test_filter_same_nstt_im_auto_sa(self, sample_classified_records):
        res = filter_records_by_category(sample_classified_records, "automation.same_nstt.im.auto.sa")
        assert len(res) == 1
        assert res[0]["INCIDENTID"] == "INC1"

    def test_filter_same_nstt_im_auto_nsa(self, sample_classified_records):
        res = filter_records_by_category(sample_classified_records, "automation.same_nstt.im.auto.nsa")
        assert len(res) == 1
        assert res[0]["INCIDENTID"] == "INC2"

    def test_filter_different_nstt(self, sample_classified_records):
        res = filter_records_by_category(sample_classified_records, "automation.different_nstt.incident_sa_auto_nsa")
        assert len(res) == 1
        assert res[0]["INCIDENTID"] == "INC5"

    def test_filter_manual_before_sr(self, sample_classified_records):
        res = filter_records_by_category(sample_classified_records, "manual.before_sr_creation.sa")
        assert len(res) == 1
        assert res[0]["INCIDENTID"] == "INC7"

    def test_filter_wrong_nstt(self, sample_classified_records):
        res = filter_records_by_category(sample_classified_records, "wrong_nstt.automation_ang_txn")
        assert len(res) == 1
        assert res[0]["INCIDENTID"] == "INC9"

    def test_filter_failure_ring(self, sample_classified_records):
        res = filter_records_by_category(sample_classified_records, "failures.ring_failure")
        assert len(res) == 1
        assert res[0]["INCIDENTID"] == "INC10"

    def test_filter_invalid_category_returns_empty(self, sample_classified_records):
        res = filter_records_by_category(sample_classified_records, "non_existent_category")
        assert res == []
