"""Automation-run decision helpers."""

from datetime import datetime
from typing import Any

from app.services.kpi_aggregator import get_period_bucket
from app.utils.time_utils import parse_datetime

YES_VALUES = {"1", "true", "t", "y", "yes", "on", "automated", "run"}


def parse_sr_creation_time(value: Any) -> datetime | None:
	"""Parse SR creation dates with the Excel month/day/year convention."""
	if isinstance(value, str):
		for date_format in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y"):
			try:
				return datetime.strptime(value.strip(), date_format)
			except ValueError:
				continue
	return parse_datetime(value)


def automation_run_answer(value: Any) -> str:
	"""Return the master-data automation value using the Excel Y/N format."""
	if value is None:
		return "N"

	normalized = str(value).strip().lower()
	return "Y" if normalized in YES_VALUES else "N"


def count_automation_runs(rows: list[dict[str, Any]]) -> dict[str, int]:
	"""Count normalized automation decisions from uploaded API response rows."""
	y_count = sum(
		automation_run_answer(row.get("AUTOMATION_RUN", row.get("automation_run"))) == "Y"
		for row in rows
	)
	n_count = len(rows) - y_count
	return {
		"Y_count": y_count,
		"N_count": n_count,
		"total_count": len(rows),
	}


def aggregate_automation_runs(rows: list[dict[str, Any]], group_by: str) -> dict[str, Any]:
	"""Group upload-response automation values by creation date period."""
	buckets: dict[str, dict[str, Any]] = {}
	omitted_count = 0

	for row in rows:
		datetime_value = parse_sr_creation_time(row.get("SRCREATIONTIME"))
		if datetime_value is None:
			omitted_count += 1
			continue

		period, period_label, sort_datetime = get_period_bucket(datetime_value, group_by)
		if period not in buckets:
			buckets[period] = {
				"period": period,
				"period_label": period_label,
				"sort_datetime": sort_datetime,
				"rows": [],
			}
		buckets[period]["rows"].append(row)

	summary = []
	for bucket in sorted(buckets.values(), key=lambda item: item["sort_datetime"]):
		counts = count_automation_runs(bucket["rows"])
		summary.append({
			"period": bucket["period"],
			"period_label": bucket["period_label"],
			**counts,
		})

	return {
		"group_by": group_by,
		"total_records": len(rows),
		"periods_count": len(summary),
		"summary": summary,
		"omitted_records": omitted_count,
	}
