"""Prepare chart data independent of presentation."""

import pandas as pd


def valid_commit_timestamps(commits):
    commits = commits.copy()
    commits['authored_timestamp'] = pd.to_datetime(commits['authored_timestamp'], errors='coerce')
    return commits.dropna(subset=['authored_timestamp'])


def transform_data_commit_graph_total(df):
    df = df.copy()
    df['commit_date'] = df['authored_timestamp'].dt.normalize()

    daily_commits = df['commit_date'].value_counts().sort_index()

    min_date = df['commit_date'].min()
    max_date = df['commit_date'].max()

    all_dates_idx = pd.date_range(start=min_date, end=max_date, freq='D', name='date')

    daily_commits_full_range = daily_commits.reindex(all_dates_idx, fill_value=0)
    plot_df = daily_commits_full_range.reset_index()
    plot_df.columns = ['date', 'commit_count']
    return plot_df


def transform_data_commit_graph_student(df):
    df = df.copy()
    df['commit_date'] = df['authored_timestamp'].dt.normalize()

    daily_commits_per_author = df.groupby(['commit_date', 'author_email']).size()
    daily_commits_unstacked = daily_commits_per_author.unstack(level='author_email', fill_value=0)

    min_date = df['commit_date'].min()
    max_date = df['commit_date'].max()

    all_dates_idx = pd.date_range(start=min_date, end=max_date, freq='D')

    daily_commits_full_range = daily_commits_unstacked.reindex(all_dates_idx, fill_value=0)
    plot_df_series = daily_commits_full_range.stack(level='author_email')
    plot_df = plot_df_series.reset_index()
    plot_df.columns = ['date', 'author_email', 'commit_count']
    return plot_df


def commit_activity_matrix(df):
    df = df.copy()
    df['day_of_week_name'] = df['authored_timestamp'].dt.day_name()
    df['hour_of_day'] = df['authored_timestamp'].dt.hour

    commit_activity = df.groupby(['day_of_week_name', 'hour_of_day']).size().reset_index(name='num_commits')

    ordered_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    ordered_hours = list(range(24))

    pivot_df = commit_activity.pivot_table(
        index='day_of_week_name',
        columns='hour_of_day',
        values='num_commits',
        fill_value=0
    )

    pivot_df = pivot_df.reindex(ordered_days, fill_value=0)
    pivot_df = pivot_df.reindex(columns=ordered_hours, fill_value=0)

    return pivot_df


def hourly_commit_counts(df):
    df = df.copy()
    df['commit_hour'] = df['authored_timestamp'].dt.hour

    hourly_commits = df['commit_hour'].value_counts().sort_index()

    all_hours = pd.DataFrame({'hour': range(24)})

    hourly_commits_df = hourly_commits.reset_index()
    hourly_commits_df.columns = ['hour', 'commit_count']

    merged_df = pd.merge(all_hours, hourly_commits_df, on='hour', how='left').fillna(0)

    return merged_df


def weekday_commit_counts(df):
    df = df.copy()
    df['day_name'] = df['authored_timestamp'].dt.day_name()

    day_counts = df['day_name'].value_counts().reset_index()
    day_counts.columns = ['Day of Week', 'Number of Commits']

    ordered_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    all_days_df = pd.DataFrame({'Day of Week': ordered_days})
    day_counts_ordered = pd.merge(all_days_df, day_counts, on='Day of Week', how='left').fillna(0)
    day_counts_ordered['Number of Commits'] = day_counts_ordered['Number of Commits'].astype(int)

    return day_counts_ordered


def get_path_up_to_n_segments(path_str, n_segments):
    if not isinstance(path_str, str) or n_segments <= 0:
        return path_str

    parts = path_str.split('/')
    if n_segments >= len(parts) or (len(parts) == 1 and n_segments >= 1):
        return path_str
    return '/'.join(parts[:n_segments])


def file_change_matrix(df, selected_segments):
    df = df.copy()
    df['grouped_path'] = df['file_path'].apply(lambda p: get_path_up_to_n_segments(p, selected_segments))
    heatmap_data = df.pivot_table(
        index='grouped_path',
        columns='author_email',
        values='num_changes',
        fill_value=0,
        aggfunc='sum'
    )
    all_students_in_project = sorted(heatmap_data.columns.tolist())
    all_grouped_paths = sorted(heatmap_data.index.tolist())
    heatmap_data = heatmap_data.reindex(index=all_grouped_paths, columns=all_students_in_project, fill_value=0)

    return heatmap_data


def git_graph_elements(df_commits, df_commit_parents):
    cytoscape_elements = []

    commit_info = df_commits.set_index('hash').to_dict('index')

    all_node_hashes = pd.concat(
        [df_commit_parents['commit_hash'],
         df_commit_parents['parent_hash']]
    ).unique()
    all_node_hashes = pd.Series(list(set(all_node_hashes) | set(df_commits['hash']))).unique()

    for commit_hash in all_node_hashes:
        commit_details = commit_info.get(commit_hash)
        if commit_details:
            author_email = commit_details['author_email']
            message_subject = commit_details['message_subject']
            message_body = commit_details['message_body']
        else:
            author_email = 'unknown@example.com'
            message_subject = "Commit details not found"
            message_body = ""


        cytoscape_elements.append({
            'data': {
                'id': commit_hash,
                'label': commit_hash[:7],
                'author_email': author_email,
                'message_subject': message_subject,
                'message_body': message_body
            }
        })

    for edge in df_commit_parents.itertuples():
        cytoscape_elements.append({
            'data': {
                'source': edge.commit_hash,
                'target': edge.parent_hash
            }
        })

    return cytoscape_elements
