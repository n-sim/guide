"""Commit measurements, team benchmarks, and comparison classification."""

from dataclasses import dataclass
from typing import Literal

import pandas as pd


@dataclass(frozen=True)
class CommitMetrics:
    total_commits: float
    average_daily_commits: float
    active_days: float
    median_lines_added: float
    median_lines_removed: float


@dataclass(frozen=True)
class CommitOverview:
    individual: CommitMetrics
    benchmark: CommitMetrics | None
    first_commit: pd.Timestamp | None
    last_commit: pd.Timestamp | None
    date_state: Literal['unavailable', 'invalid', 'available']


def get_average_daily_number_of_commits(df):
    min_date = df['authored_timestamp'].min()
    max_date = df['authored_timestamp'].max()
    total_days_in_range = (max_date - min_date).days + 1
    total_commits = len(df)
    if total_days_in_range > 0:
        return total_commits / total_days_in_range
    return 0 if total_commits == 0 else total_commits


def get_active_days(commits):
    if commits.empty or 'authored_timestamp' not in commits:
        return 0
    dates = pd.to_datetime(commits['authored_timestamp'], errors='coerce').dt.date.dropna()
    return dates.nunique()


def calculate_commit_overview(commits, team=None, individual_tab=False) -> CommitOverview:
    individual = CommitMetrics(
        total_commits=len(commits),
        average_daily_commits=get_average_daily_number_of_commits(commits) if not commits.empty else 0.0,
        active_days=get_active_days(commits),
        median_lines_added=commits['number_of_lines_added'].median()
        if not commits.empty and 'number_of_lines_added' in commits else float('nan'),
        median_lines_removed=commits['number_of_lines_removed'].median()
        if not commits.empty and 'number_of_lines_removed' in commits else float('nan'),
    )
    first = last = None
    date_state = 'unavailable'
    if not commits.empty and 'authored_timestamp' in commits:
        timestamps = pd.to_datetime(commits['authored_timestamp'], errors='coerce').dropna()
        date_state = 'invalid' if timestamps.empty else 'available'
        if not timestamps.empty:
            first, last = timestamps.min(), timestamps.max()

    benchmark = None
    if individual_tab and team is not None and not team.empty:
        member_count = team['author_email'].nunique() if 'author_email' in team else 0
        groups = team.groupby('author_email') if member_count > 0 else None
        rates = [get_average_daily_number_of_commits(member) for _, member in groups] if groups is not None else []
        active_days = [get_active_days(team[team['author_email'] == author])
                       for author in team['author_email'].unique()] if member_count > 0 else []
        benchmark = CommitMetrics(
            total_commits=len(team) / member_count if member_count > 0 else float('nan'),
            average_daily_commits=pd.Series(rates, dtype=float).mean(),
            active_days=sum(active_days) / len(active_days) if active_days else float('nan'),
            median_lines_added=groups['number_of_lines_added'].median().mean()
            if groups is not None and 'number_of_lines_added' in team else float('nan'),
            median_lines_removed=groups['number_of_lines_removed'].median().mean()
            if groups is not None and 'number_of_lines_removed' in team else float('nan'),
        )
    return CommitOverview(individual, benchmark, first, last, date_state)


def compare_to_team(individual_value, team_value, tolerance: float) -> str:
    if pd.isna(individual_value) and pd.isna(team_value):
        return 'unavailable'
    if pd.isna(individual_value):
        return 'individual_unavailable'
    if pd.isna(team_value):
        return 'team_unavailable'
    if team_value == 0:
        return 'higher_zero' if individual_value > 0 else 'equal_zero' if individual_value == 0 else 'lower_zero'
    if individual_value > team_value * (1 + tolerance):
        return 'higher'
    if individual_value < team_value * (1 - tolerance):
        return 'lower'
    return 'similar'


def average_message_length(commits):
    messages = commits['message_subject'].fillna('') + commits['message_body'].fillna('')
    return messages.str.len().mean()


def observed_members(commits):
    return commits[['author_name', 'author_email']].drop_duplicates()


def member_commit_groups(commits):
    return [(author, commits[commits['author_email'] == author])
            for author in commits['author_email'].unique()]
