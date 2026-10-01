from io import StringIO

import pandas as pd
import plotly.express as px

from analysis.chart_data import (
    commit_activity_matrix,
    hourly_commit_counts,
    valid_commit_timestamps,
    weekday_commit_counts,
)
from dash import dcc, html, callback, Output, Input


def create_switchable_commit_time_plot(df_commits):
    activity_data = df_commits.reindex(columns=['authored_timestamp']).copy()
    activity_data['authored_timestamp'] = pd.to_datetime(activity_data['authored_timestamp'], errors='coerce')
    return html.Div(
        children=[
            dcc.Store(
                id='commit-activity-data',
                storage_type='memory',
                data=activity_data.to_json(orient='split', date_format='iso'),
            ),
            dcc.RadioItems(
                id='plot-type-selector',
                options=[
                    {'label': 'Commits activity as two bar charts', 'value': 'two_bar'},
                    {'label': 'Commit activity as a heatmap (day vs. hour)', 'value': 'one_heatmap'},
                ],
                value='two_bar',
                labelStyle={'cursor': 'pointer'},
                inputStyle={'margin-right': '4px'},
            ),
            html.Div(id='graph-container')
        ]
    )


def _create_commit_activity_heatmap(df_commits):
    if df_commits.empty or 'authored_timestamp' not in df_commits.columns:
        return html.Div("No commit data available to display commit activity heatmap.")

    df = valid_commit_timestamps(df_commits)

    if df.empty:
        return html.Div("No valid timestamps found to display commit activity heatmap.")

    pivot_df = commit_activity_matrix(df)

    if pivot_df.sum().sum() == 0:
        return html.Div("No commits found to display in the activity heatmap.")

    fig = px.imshow(
        pivot_df,
        labels=dict(x="Hour of Day", y="Day of Week", color="Number of Commits"),
        x=[f"{h}:00" for h in pivot_df.columns],
        y=pivot_df.index,
        text_auto=True,  # Display the commit count number on each cell
    )

    fig.update_layout(
        title_text='Commit activity: day of the week vs. hour of the day',
        xaxis_title="Hour of Day",
        yaxis_title="Day of Week",
        xaxis_tickangle=0,  # Keep hour labels horizontal
    )

    fig.update_traces(
        hovertemplate="<b>Day:</b> %{y}<br>" +
                      "<b>Hour:</b> %{x}<br>" +
                      "<b>Commits:</b> %{z}<extra></extra>"  # Custom hover text
    )

    return dcc.Graph(figure=fig, id="commit-activity-heatmap", config={'displaylogo': False})


def _create_commit_time_distribution_plot(df_commits):
    if df_commits.empty or 'authored_timestamp' not in df_commits.columns:
        return html.Div("No commit data available to display commit time distribution.")

    df = valid_commit_timestamps(df_commits)

    if df.empty:
        return html.Div("No valid timestamps found to display commit time distribution.")

    merged_df = hourly_commit_counts(df)

    fig = px.bar(
        merged_df,
        x='hour',
        y='commit_count',
        labels={'hour': 'Hour of Day (0-23)', 'commit_count': 'Number of Commits'},
        title='Commit distribution by hour of the day'
    )

    fig.update_xaxes(tickvals=list(range(24)), ticktext=[f"[{h} - {h + 1})" for h in range(24)])
    fig.update_layout(
        xaxis_title="Hour of Day",
        yaxis_title="Number of Commits",
        bargap=0.2,
    )

    return dcc.Graph(figure=fig, id="commit-time-distribution-graph", config={'displaylogo': False})


def _create_commit_day_of_week_plot(df_commits):
    if df_commits.empty or 'authored_timestamp' not in df_commits.columns:
        return html.Div("No commit data available to display day of week commit distribution.")

    df = valid_commit_timestamps(df_commits)

    if df.empty:
        return html.Div("No valid timestamps found to display day of week commit distribution.")

    day_counts_ordered = weekday_commit_counts(df)

    if day_counts_ordered.empty or day_counts_ordered['Number of Commits'].sum() == 0:
        return html.Div("No commits found to display in day of week distribution.")

    fig = px.bar(
        day_counts_ordered,
        x='Day of Week',
        y='Number of Commits',
        title='Commit distribution by day of week',
        labels={'Day of Week': 'Day of the the Week', 'Number of Commits': 'Number of Commits'},
        text_auto=True  # Display the value on top of the bars
    )

    fig.update_layout(
        xaxis_title="Day of the Week",
        yaxis_title="Number of Commits",
    )

    fig.update_traces(
        textposition='outside'
    )

    return dcc.Graph(figure=fig, id="commit-day-of-week-barchart", config={'displaylogo': False})


@callback(
    Output('graph-container', 'children'),
    Input('plot-type-selector', 'value'),
    Input('commit-activity-data', 'data'),
)
def update_graph_display(selected_plot_value, store_data):
    df = pd.read_json(StringIO(store_data), orient='split', convert_dates=False) if store_data else pd.DataFrame()
    if df.empty:
        return html.Div("No commit data available to display commit activity.")
    df['authored_timestamp'] = pd.to_datetime(df['authored_timestamp'], errors='coerce')

    if selected_plot_value == 'two_bar':
        return html.Div([
            _create_commit_time_distribution_plot(df),
            _create_commit_day_of_week_plot(df)
        ])
    elif selected_plot_value == 'one_heatmap':
        return _create_commit_activity_heatmap(df)
    else:
        return html.Div("Please select a plot type.")
