import dash
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output

import data_access

dash.register_page(__name__, path='/')


def layout():
    return dbc.Container(children=[
        html.Center(children=[
            dcc.Markdown("# GUIDE - Tutor Dashboard"),
            dcc.Markdown("## Select Project"),
        ]),
        dbc.Row(children=[
            dbc.Col(dcc.Dropdown(
                options=[],
                id='project-dropdown',
                placeholder="Select a project..."
            )),
            dbc.Col(dbc.Button("Refresh projects", id='refresh-projects', n_clicks=0), width='auto'),
        ], className='g-2 align-items-center flex-nowrap'),
    ])


@callback(
    Output('project-dropdown', 'options'),
    Output('project-dropdown', 'value'),
    Input('refresh-projects', 'n_clicks'),
)
def refresh_projects(_n_clicks):
    try:
        df_projects = data_access.load_projects()
    except Exception as e:
        print(f"Error loading projects from database: {e}")
        df_projects = None

    if df_projects is None or df_projects.empty:
        options = [{'label': 'No projects found', 'value': '', 'disabled': True}]
    else:
        options = [{'label': project['name'], 'value': project['id']}
                   for project in df_projects.to_dict('records')]

    return options, None


@callback(
    Output('url', 'href'),
    Input('project-dropdown', 'value'),
    prevent_initial_call=True,
)
def navigate_to_project(project_id):
    if project_id is None or project_id == '':
        raise PreventUpdate

    return f"/project?project_id={project_id}"
