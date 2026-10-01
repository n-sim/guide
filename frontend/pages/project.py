import dash
import dash_bootstrap_components as dbc
import plotly.express as px
from dash import html

import data_access
from analysis.commit_metrics import member_commit_groups
from configuration import ConfigurationError, load_configuration
from components.git_information import create_git_information
from components.member_information import create_member_information_card
from components.project_information import create_project_information_card
from components.sidebar import sidebar
from plots.commit_graph import create_commit_graph_total, create_commit_graph_student
from plots.commit_overview import create_commit_overview_plot
from plots.commit_piechart import create_commit_piechart
from plots.commit_time_distribution import create_switchable_commit_time_plot
from plots.filechange_heatmap import create_filechange_heatmap
from plots.git_graph import create_git_graph_plot
from plots.team_indicators import create_indicator_cards
dash.register_page(__name__)

def layout(project_id=None):
    try:
        settings = load_configuration()
    except ConfigurationError as error:
        return dbc.Alert([
            html.H4("Invalid indicator configuration"),
            html.Pre(str(error), style={'white-space': 'pre-wrap'}),
        ], color='danger')

    project = data_access.load_project(project_id)
    df_commits = project.commits
    df_branches = project.branches
    df_commit_parents = project.commit_parents
    df_project_details = project.details
    df_changes_grouped = project.file_changes

    if df_commits.empty:
        return html.H1(f"Project with id={project_id} not found in database.")

    author_color_map = get_author_color_map(df_commits)

    return html.Div(children=[
        sidebar,
        html.Main(children=[
            html.H2("Project Overview", id="section-details"),
            dbc.Row(
                [
                    dbc.Col(create_project_information_card(df_project_details) ,width=6),
                    dbc.Col(create_member_information_card(df_commits, author_color_map), width=6)
                ]
            ),
            html.H2("Indicators", id="section-indicators"),
            create_indicator_cards(df_commits, settings=settings),
            html.H2("Team Collaboration", id="section-collaboration"),
            dbc.Tabs(children=[dbc.Tab(children=[create_commit_overview_plot(df_commits, settings=settings)], label="Total")] + [
                dbc.Tab(children=[
                    create_commit_overview_plot(member_commits, df_total=df_commits, is_individual_tab=True, settings=settings),
                ], label=author_email) for author_email, member_commits in member_commit_groups(df_commits)]),
            create_commit_graph_total(df_commits),
            html.Hr(),
            create_commit_graph_student(df_commits, author_color_map),
            html.Hr(),
            create_switchable_commit_time_plot(df_commits),
            html.Hr(),
            create_commit_piechart(df_commits, author_color_map),
            html.Hr(),
            create_filechange_heatmap(df_changes_grouped),
            html.Hr(),
            html.H2("Git Usage", id="section-git"),
            create_git_information(df_commits, df_branches),
            create_git_graph_plot(df_commits, df_commit_parents, author_color_map)
        ],
            style={"flex-grow": "1", "padding": "4rem"})
    ],
        style={"display": "flex", "align-items": "flex-start"})


def get_author_color_map(df_commits):
    unique_emails = sorted(df_commits['author_email'].unique())
    color_palette = px.colors.qualitative.Plotly
    return {
        email: color_palette[i % len(color_palette)]
        for i, email in enumerate(unique_emails)
    }
