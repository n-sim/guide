import dash_bootstrap_components as dbc
from dash import html

from analysis.commit_metrics import average_message_length


def create_git_information(df_commits, df_branches):
    message_length = average_message_length(df_commits)
    return dbc.CardGroup([
        dbc.Card([
            dbc.CardHeader("Branches"),
            dbc.CardBody(
                [
                    html.Ul(children=[html.Li(html.H5(name_value)) for name_value in df_branches['name']])
                ]
            )
        ]),
        dbc.Card([
            dbc.CardHeader("Average Commit message length"),
            dbc.CardBody(
                [
                    html.H2(
                        f"{message_length:.2f} characters",
                        id="average-commit-length"
                    ),
                ]
            )
        ])
    ],
    style={"margin-bottom": "1rem"})
