from dash import dcc
import plotly.express as px


def create_commit_piechart(df, author_color_map):
    return dcc.Graph(id="pie-chart",
                     figure=px.pie(
                         df,
                         names='author_email',
                         color='author_email',
                         color_discrete_map=author_color_map,
                         title="Percentage of commits per student",
                     ).update_layout(legend_title_text='Author Email'),
                     config={'displaylogo': False})
