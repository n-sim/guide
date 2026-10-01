"""Evaluate commit-based indicators; return facts without presentation markup."""

import re
from dataclasses import dataclass
from typing import Literal

import pandas as pd

from analysis.settings import ActivitySettings, ParticipationSettings, ProcessSettings


@dataclass(frozen=True)
class ParticipationAssessment:
    has_data: bool
    high_threshold: float = 0
    low_threshold: float = 0
    high_contributors: tuple[tuple[str, float], ...] = ()
    low_contributors: tuple[tuple[str, float], ...] = ()
    severity: Literal['good', 'alert'] = 'good'


@dataclass(frozen=True)
class ProcessAssessment:
    has_data: bool
    large_commits: int = 0
    short_messages: int = 0
    generic_subjects: int = 0
    severity: Literal['good', 'warning', 'alert'] = 'good'


@dataclass(frozen=True)
class ActivityAssessment:
    state: Literal['insufficient_data', 'date_error', 'consistent',
                   'low_activity', 'high_variability', 'moderate_variability']
    longest_low_days: int = 0
    coefficient_of_variation: float | None = None


def evaluate_participation(commits, settings: ParticipationSettings) -> ParticipationAssessment:
    if commits.empty:
        return ParticipationAssessment(False)
    percentages = commits['author_email'].value_counts() / len(commits) * 100
    high = 100 / len(percentages) * settings.high_multiplier
    low = 100 / len(percentages) * settings.low_multiplier
    high_contributors = tuple((author, pct) for author, pct in percentages.items() if pct > high)
    low_contributors = tuple((author, pct) for author, pct in percentages.items() if pct < low)
    return ParticipationAssessment(True, high, low, high_contributors, low_contributors,
                                   'alert' if high_contributors or low_contributors else 'good')


def is_generic_subject(subject: str, keywords: tuple[str, ...]) -> bool:
    words = re.findall(r'[^\W_]+', subject.casefold())
    return bool(words) and all(word in keywords for word in words)


def evaluate_process(commits, settings: ProcessSettings) -> ProcessAssessment:
    if commits.empty:
        return ProcessAssessment(False)
    subjects = commits['message_subject'].fillna('').astype(str)
    bodies = commits['message_body'].fillna('').astype(str)
    messages = pd.Series(
        [f'{subject}\n{body}' if body else subject for subject, body in zip(subjects, bodies)],
        index=commits.index,
    )
    large = int(((commits['number_of_lines_added'] + commits['number_of_lines_removed'])
                 > settings.large_commit_lines).sum())
    short = int((messages.str.len() < settings.short_message_chars).sum())
    generic = int(subjects.apply(lambda subject: is_generic_subject(subject, settings.generic_subject_keywords)).sum())
    severity = 'alert' if large else 'warning' if short or generic else 'good'
    return ProcessAssessment(True, large, short, generic, severity)


def evaluate_activity(commits, settings: ActivitySettings) -> ActivityAssessment:
    if commits.empty or len(commits) < settings.minimum_commits:
        return ActivityAssessment('insufficient_data')
    commits = commits.copy()
    commits['authored_timestamp'] = pd.to_datetime(commits['authored_timestamp'])
    first = commits['authored_timestamp'].min()
    last = commits['authored_timestamp'].max()
    if pd.isna(first) or pd.isna(last) or first > last:
        return ActivityAssessment('date_error')

    dates = pd.date_range(start=first.normalize(), end=last.normalize(), freq='D')
    indexed = commits.set_index('authored_timestamp')['hash']
    daily = indexed.resample('D').count().reindex(dates, fill_value=0)
    longest = current = 0
    for count in daily:
        if count <= settings.low_daily_commits:
            current += 1
        else:
            longest = max(longest, current)
            current = 0
    longest = max(longest, current)
    if longest > settings.low_run_alert_days:
        return ActivityAssessment('low_activity', longest)

    periods = indexed.resample(f'{settings.window_days}D').count()
    cv = None
    state = 'consistent'
    if len(periods) >= settings.minimum_periods:
        mean = periods.mean()
        cv = periods.std(ddof=0) / mean if mean > 0 else 0
        if cv > settings.variability_warning_cv:
            state = 'high_variability'
        elif cv > settings.variability_info_cv:
            state = 'moderate_variability'
    return ActivityAssessment(state, longest, cv)
