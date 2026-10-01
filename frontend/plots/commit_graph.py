from dash import html, dcc
import plotly.express as px
from analysis.chart_data import (
    transform_data_commit_graph_student,
    transform_data_commit_graph_total,
)


def create_commit_graph_total(df):
    return dcc.Graph(
        id="commit-graph_total",
        figure=px.line(
            transform_data_commit_graph_total(df),
            x='date',
            y='commit_count',
            title="Number of commits per day (total)",
            labels={'date': 'Date', 'commit_count': 'Number of Commits'},
            markers=True
        ),
        config={'displaylogo': False}
    )


def create_commit_graph_student(df, author_color_map):
    return dcc.Graph(
        id="commit-graph_student",
        figure=px.line(
            transform_data_commit_graph_student(df),
            x='date',
            y='commit_count',
            color='author_email',
            color_discrete_map=author_color_map,
            title="Number of commits per day (per student)",
            labels={'date': 'Date', 'commit_count': 'Number of Commits', 'author_email': 'Author Email'},
            markers=True
        ),
        config={'displaylogo': False}
    )
