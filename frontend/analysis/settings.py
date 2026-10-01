"""Immutable rule values passed explicitly to analysis."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ParticipationSettings:
    high_multiplier: float
    low_multiplier: float


@dataclass(frozen=True)
class ProcessSettings:
    large_commit_lines: int
    short_message_chars: int
    generic_subject_keywords: tuple[str, ...]


@dataclass(frozen=True)
class ActivitySettings:
    minimum_commits: int
    low_daily_commits: int
    low_run_alert_days: int
    window_days: int
    minimum_periods: int
    variability_info_cv: float
    variability_warning_cv: float


@dataclass(frozen=True)
class ComparisonSettings:
    tolerance: float


@dataclass(frozen=True)
class DashboardSettings:
    participation: ParticipationSettings
    process: ProcessSettings
    activity: ActivitySettings
    comparison: ComparisonSettings
