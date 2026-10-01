from dash import html
import dash_bootstrap_components as dbc

_SIDEBAR_STYLE = {
    "position": "sticky",
    "top": "0",
    "height": "100vh",
    "width": "16rem",
    "overflow-y": "auto",
    "flex-shrink": "0",
    "padding": "2rem 1rem",
    "background-color": "#f9f9f9",
}

sidebar = html.Aside(
    [
        html.H2("GUIDE"),
        html.Hr(),
        dbc.Nav(
            [
                dbc.NavLink("Project Overview", href="#section-details", external_link=True),
                dbc.NavLink("Indicators", href="#section-indicators", external_link=True),
                dbc.NavLink("Team Collaboration", href="#section-collaboration", external_link=True),
                dbc.NavLink("Git Usage", href="#section-git", external_link=True)
            ],
            vertical=True,
        ),
        html.Hr(),
        dbc.Nav(
            [
                dbc.NavLink("Back to Home", href="/"),
            ],
            vertical=True
        )
    ],
    style=_SIDEBAR_STYLE,
    id="sidebar",
)
