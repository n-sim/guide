from io import StringIO

import pandas as pd
from dash import dcc, callback, Output, Input, html
import plotly.express as px
import plotly.graph_objects as go

from analysis.chart_data import file_change_matrix, get_path_up_to_n_segments


def create_filechange_heatmap(df):
    return html.Div([
        dcc.Store(
            id='file-change-data',
            storage_type='memory',
            data=df.reindex(columns=['file_path', 'author_email', 'num_changes']).to_json(orient='split'),
        ),
        dcc.Graph(
            id='file-change-heatmap',
            config={'displaylogo': False}
        ),
        dcc.Slider(
            id='segment-slider',
            min=1,
            max=4,
            step=1,
            value=1,
            marks={i: f'{i} Segments' for i in range(1, 5)},
        ),
    ])


@callback(
    Output('file-change-heatmap', 'figure'),
    Input('segment-slider', 'value'),
    Input('file-change-data', 'data'),
)
def update_heatmap(selected_segments, store_data):
    df = pd.read_json(StringIO(store_data), orient='split') if store_data else pd.DataFrame()
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No file change data available.", showarrow=False)
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        return fig

    heatmap_data = file_change_matrix(df, selected_segments)

    return px.imshow(
                heatmap_data,
                x=heatmap_data.columns,
                y=heatmap_data.index,
                text_auto=True, aspect="auto",
                title="Number of changes per student and segment",
                labels={'x': 'Author Email', 'y': 'File Path', 'color': 'Number of Changes'}
            )


