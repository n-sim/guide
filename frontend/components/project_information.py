from dash import html
import dash_bootstrap_components as dbc

def create_project_information_card(df):
    return html.Div(children=[
        html.H4("Project Information", id="project-info"),
        dbc.Card(
            dbc.CardBody(
                [
                    dbc.Row([
                        dbc.Col([
                            html.H5("Project name", className="card-title"),
                            html.P(df["name"].iloc[0], className="card-text")
                        ]),
                        dbc.Col([
                            html.H5("Project ID", className="card-title"),
                            html.P(df["id"].iloc[0], className="card-text"),
                        ]),
                        dbc.Col([
                            html.H5("Semester code", className="card-title"),
                            html.P(df["semester_code"].iloc[0],
                                   className="card-text"),
                        ]),
                    ]),
                    dbc.Button("Navigate to project", href=df["web_url"].iloc[0],
                               target="_blank",
                               style={"margin-top": "1rem"}),
                ]
            ),
        )
    ])