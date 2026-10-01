from dash import html
import dash_bootstrap_components as dbc

from analysis.commit_metrics import observed_members


def create_member_information_card(df_commits, author_color_map):
    df_members = observed_members(df_commits)
    df_members.columns = ['Student Name', 'Student Email']

    return html.Div(children=[
        html.H4("Member Information", id="member-info"),
        dbc.Table(
            children=[
                html.Thead(html.Tr([html.Th("Student Name"), html.Th("Student Email")])),
                html.Tbody([
                    html.Tr([
                        html.Td(row_data['Student Name']),
                        html.Td(row_data['Student Email'], style={'backgroundColor': author_color_map.get(row_data['Student Email'])})
                    ],
                    ) for index, row_data in df_members.iterrows()
                ])
            ],
            bordered=True,
            hover=True,
        )
    ])
