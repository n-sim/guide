import dash_bootstrap_components as dbc
import pandas as pd
from dash import html

from analysis.commit_metrics import (
    calculate_commit_overview,
    compare_to_team,
)
from configuration import load_configuration


def create_commit_overview_plot(df, df_total=None, is_individual_tab=False, settings=None):
    settings = settings or load_configuration()
    overview = calculate_commit_overview(df, df_total, is_individual_tab)
    def create_comparison_indicator(individual_value, team_value, metric_name):
        comparison = compare_to_team(individual_value, team_value, settings.comparison.tolerance)
        if comparison == 'unavailable':
            return html.Span(" (N/A)", title=f"{metric_name}: Data not available for individual or team",
                             style={"color": "grey", "font-size": "0.8em", "margin-left": "5px"})
        if comparison == 'individual_unavailable':
            team_val_str = f"{team_value:.2f}" if pd.notna(team_value) else "N/A"
            return html.Span(f" (N/A for individual, Team: {team_val_str})",
                             title=f"{metric_name}: Data not available for individual (Team: {team_val_str})",
                             style={"color": "grey", "font-size": "0.8em", "margin-left": "5px"})
        if comparison == 'team_unavailable':
            ind_val_str = f"{individual_value:.2f}" if pd.notna(individual_value) else "N/A"
            return html.Span(f" (N/A for team avg, Indiv: {ind_val_str})",
                             title=f"{metric_name}: Data not available for team average (Individual: {ind_val_str})",
                             style={"color": "grey", "font-size": "0.8em", "margin-left": "5px"})

        if comparison.endswith('_zero'):
            if comparison == 'higher_zero':
                return html.Span(f" (↑ vs team: 0)", title=f"{metric_name}: Higher than team (team is 0)",
                                 style={"color": "green", "font-size": "0.8em", "margin-left": "5px"})
            elif comparison == 'equal_zero':
                return html.Span(f" (= vs team: 0)", title=f"{metric_name}: Same as team (both 0)",
                                 style={"color": "grey", "font-size": "0.8em", "margin-left": "5px"})
            else:
                return html.Span(f" (↓ vs team: 0)", title=f"{metric_name}: Lower than team (team is 0)",
                                 style={"color": "red", "font-size": "0.8em", "margin-left": "5px"})

        if comparison == 'higher':
            return html.Span(f" (↑ vs team avg: {team_value:.2f})",
                             title=f"{metric_name}: Higher than team average ({team_value:.2f})",
                             style={"color": "green", "font-size": "0.8em", "margin-left": "5px"})
        elif comparison == 'lower':
            return html.Span(f" (↓ vs team avg: {team_value:.2f})",
                             title=f"{metric_name}: Lower than team average ({team_value:.2f})",
                             style={"color": "red", "font-size": "0.8em", "margin-left": "5px"})
        else:
            return html.Span(f" (≈ vs team avg: {team_value:.2f})",
                             title=f"{metric_name}: Similar to team average ({team_value:.2f})",
                             style={"color": "orange", "font-size": "0.8em", "margin-left": "5px"})

    total_commits_indicator = ""
    avg_daily_commits_indicator = ""
    active_days_indicator = ""
    median_lines_added_indicator = ""
    median_lines_removed_indicator = ""

    metrics = overview.individual
    individual_total_commits_val = metrics.total_commits
    individual_avg_daily_commits_val = metrics.average_daily_commits
    individual_active_days_val = metrics.active_days
    individual_median_lines_added_val = metrics.median_lines_added
    individual_median_lines_removed_val = metrics.median_lines_removed

    earliest_commit_str = latest_commit_str = duration_commit_str = "N/A"
    if overview.date_state == 'available':
        earliest_commit_str = overview.first_commit.strftime('%Y-%m-%d %H:%M:%S %Z')
        latest_commit_str = overview.last_commit.strftime('%Y-%m-%d %H:%M:%S %Z')
        duration_commit_str = f"{(overview.last_commit - overview.first_commit).days} days"
    elif overview.date_state == 'invalid':
        earliest_commit_str = latest_commit_str = duration_commit_str = "Invalid Date Data"

    if overview.benchmark is not None:
        benchmark = overview.benchmark
        total_commits_indicator = create_comparison_indicator(metrics.total_commits, benchmark.total_commits, "Total Commits")
        avg_daily_commits_indicator = create_comparison_indicator(metrics.average_daily_commits, benchmark.average_daily_commits, "Avg Daily Commits")
        active_days_indicator = create_comparison_indicator(metrics.active_days, benchmark.active_days, "Active Days")
        median_lines_added_indicator = create_comparison_indicator(metrics.median_lines_added, benchmark.median_lines_added, "Median Lines Added")
        median_lines_removed_indicator = create_comparison_indicator(metrics.median_lines_removed, benchmark.median_lines_removed, "Median Lines Removed")

    return html.Div(children=[
        dbc.CardGroup([
            dbc.Card([
                dbc.CardHeader("Total number of commits"),
                dbc.CardBody(
                    [
                        html.H2(
                            [f"{individual_total_commits_val}", total_commits_indicator],
                        ),
                    ]
                )
            ]),
            dbc.Card([
                dbc.CardHeader("Average number of commits per day"),
                dbc.CardBody(
                    [
                        html.H2(
                            [f"{round(individual_avg_daily_commits_val, 2) if pd.notna(individual_avg_daily_commits_val) else 'N/A'}",
                             avg_daily_commits_indicator],
                        ),
                    ]
                )
            ]),
        ],
            style={"margin-bottom": "1rem", "margin-top": "1rem"}),
        dbc.CardGroup([
            dbc.Card([
                dbc.CardHeader("Median number of lines added per commit"),
                dbc.CardBody(
                    [
                        html.H2(
                            [f"{round(individual_median_lines_added_val, 2) if pd.notna(individual_median_lines_added_val) else 'N/A'}",
                             median_lines_added_indicator],
                        ),
                    ]
                )
            ]),
            dbc.Card([
                dbc.CardHeader("Median number of lines deleted per commit"),
                dbc.CardBody(
                    [
                        html.H2(
                            [f"{round(individual_median_lines_removed_val, 2) if pd.notna(individual_median_lines_removed_val) else 'N/A'}",
                             median_lines_removed_indicator],
                        ),
                    ]
                )
            ])

        ], style={"margin-bottom": "1rem"}),
        dbc.CardGroup([
            dbc.Card([
                dbc.CardHeader("Number of days total"),
                dbc.CardBody(
                    [
                        html.H2(duration_commit_str),
                    ]
                )
            ]),
            dbc.Card([
                dbc.CardHeader("Number of active days"),
                dbc.CardBody(
                    [
                        html.H2(
                            [f"{individual_active_days_val} days", active_days_indicator],
                        ),
                    ]
                )
            ])
        ], style={"margin-bottom": "1rem"}),
        dbc.CardGroup([
            dbc.Card([
                dbc.CardHeader("Earliest Commit"),
                dbc.CardBody(
                    [
                        html.H2(earliest_commit_str),
                    ]
                )
            ]),
            dbc.Card([
                dbc.CardHeader("Latest commit"),
                dbc.CardBody(
                    [
                        html.H2(latest_commit_str),
                    ]
                )
            ]),
        ],
            style={"margin-bottom": "1rem"})
    ],
    )
