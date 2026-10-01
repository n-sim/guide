import dash_bootstrap_components as dbc
from dash import html

from analysis.indicators import evaluate_activity, evaluate_participation, evaluate_process
from configuration import load_configuration

STATUS_GOOD_EMOJI = "✅"
STATUS_WARN_EMOJI = "⚠️"
STATUS_ALERT_EMOJI = "🚨"
STATUS_INFO_EMOJI = "ℹ️"


def card_unbalanced_participation(df_commits, settings=None):
    settings = settings or load_configuration()
    result = evaluate_participation(df_commits, settings.participation)
    card_id = "participation-card"
    title = "Participation Balance"
    header_id = f"{card_id}-header"
    body_id = f"{card_id}-body"

    if not result.has_data:
        return dbc.Card([
            dbc.CardHeader(title, id=header_id),
            dbc.CardBody([
                html.H5(f"{STATUS_INFO_EMOJI} No Data", className="card-title"),
                html.P("No commit data to assess participation.", className="card-text"),
            ], id=body_id)
        ], id=card_id, className="mb-3")

    participation_high_threshold_pct = result.high_threshold
    participation_low_threshold_pct = result.low_threshold
    high_contributors = result.high_contributors
    low_contributors = result.low_contributors

    details_items = []

    if result.severity == 'alert':
        status_emoji = STATUS_ALERT_EMOJI
        card_color = "danger"
        status_text = ""
    else:
        status_emoji = STATUS_GOOD_EMOJI
        card_color = "white"
        status_text = "Participation appears balanced."

    if high_contributors:
        status_text = status_text + f"{len(high_contributors)} author(s) dominating contributions"
        for author, pct in high_contributors:
            details_items.append(
                html.Li(f"{author.split('@')[0]}: {pct:.0f}% (Threshold: >{participation_high_threshold_pct}%)"))
    if low_contributors:
        if status_text:
            status_text = status_text + " and "
        status_text = status_text + f"{len(low_contributors)} author(s) with low participation"
        for author, pct in low_contributors:
            details_items.append(
                html.Li(f"{author.split('@')[0]}: {pct:.0f}% (Threshold: <{participation_low_threshold_pct}%)"))

    card_body_children = [
        html.H5(f"{status_emoji} {status_text}", className="card-title"),
    ]
    if details_items:
        card_body_children.extend([
            html.P("Details:", className="card-text mt-2 mb-1 small"),
            html.Ul(details_items, className="small")
        ])

    return dbc.Card([
        dbc.CardHeader(title, id=header_id),
        dbc.CardBody(card_body_children, id=body_id)
    ], color=card_color, inverse=(card_color != "white"), className="mb-3")


def card_process_warnings(df_commits, card_id="process-warnings-card", settings=None):
    settings = settings or load_configuration()
    result = evaluate_process(df_commits, settings.process)
    title = "Git Process Health"
    header_id = f"{card_id}-header"
    body_id = f"{card_id}-body"

    if not result.has_data:
        return dbc.Card([
            dbc.CardHeader(title, id=header_id),
            dbc.CardBody([
                html.H5(f"{STATUS_INFO_EMOJI} No Data", className="card-title"),
                html.P("No commit data to assess process warnings.", className="card-text"),
            ], id=body_id)
        ], id=card_id, className="mb-3")

    num_large_commits = result.large_commits
    num_short_messages = result.short_messages
    num_generic_subjects = result.generic_subjects

    warnings_found_text = []

    if num_large_commits > 0:
        warnings_found_text.append(f"{num_large_commits} large commit(s) (> {settings.process.large_commit_lines} lines).")
    if num_short_messages > 0:
        warnings_found_text.append(f"{num_short_messages} short message(s) (< {settings.process.short_message_chars} chars).")
    if num_generic_subjects > 0:
        warnings_found_text.append(f"{num_generic_subjects} commit(s) with generic subjects.")

    if result.severity == 'alert':
        status_emoji = STATUS_ALERT_EMOJI
        status_text = "Significant process warnings."
        card_color = "danger"
    elif result.severity == 'warning':
        status_emoji = STATUS_WARN_EMOJI
        status_text = "Some process warnings noted."
        card_color = "warning"
    else:
        status_emoji = STATUS_GOOD_EMOJI
        status_text = "Git process seems healthy."
        card_color = "light"

    card_body_children = [html.H5(f"{status_emoji} {status_text}", className="card-title")]
    if warnings_found_text:
        card_body_children.append(
            html.Ul([html.Li(item, className="small") for item in warnings_found_text], className="mt-2 mb-0"))

    return dbc.Card([
        dbc.CardHeader(title, id=header_id),
        dbc.CardBody(card_body_children, id=body_id)
    ], id=card_id, color=card_color, inverse=(card_color not in ["light", "white"]), className="mb-3")


def card_deadline_crunch_pattern(df_commits, card_id="deadline-crunch-card", settings=None):
    settings = settings or load_configuration()
    result = evaluate_activity(df_commits, settings.activity)
    title = "Activity Pattern & Consistency"
    header_id = f"{card_id}-header"
    body_id = f"{card_id}-body"

    if result.state == 'insufficient_data':
        return dbc.Card([
            dbc.CardHeader(title, id=header_id),
            dbc.CardBody([
                html.H5(f"{STATUS_INFO_EMOJI} Insufficient Data", className="card-title"),
                html.P("Too few commits for robust activity pattern analysis.", className="card-text"),
            ], id=body_id)
        ], id=card_id, className="mb-3")

    if result.state == 'date_error':
        return dbc.Card([
            dbc.CardHeader(title, id=header_id),
            dbc.CardBody([
                html.H5(f"{STATUS_INFO_EMOJI} Date Error", className="card-title"),
                html.P("Could not determine a valid date range from commits.", className="card-text"),
            ], id=body_id)
        ], id=card_id, className="mb-3")

    styles = {
        'consistent': (STATUS_GOOD_EMOJI, 'light', 'Activity pattern appears consistent.'),
        'low_activity': (STATUS_ALERT_EMOJI, 'danger', 'Significant period of low/no activity detected.'),
        'high_variability': (STATUS_WARN_EMOJI, 'warning', 'High variability in weekly activity rhythm.'),
        'moderate_variability': (STATUS_INFO_EMOJI, 'light', 'Moderate variability in weekly activity rhythm.'),
    }
    status_emoji, card_color, status_text = styles[result.state]
    main_alert_triggered = result.state == 'low_activity'
    details_daily_low_activity = ''
    if main_alert_triggered:
        details_daily_low_activity = (
            f"{result.longest_low_days} consecutive day(s) with "
            f"<= {settings.activity.low_daily_commits} commit(s)."
        )
    details_weekly_cv = ''
    if result.coefficient_of_variation is not None:
        details_weekly_cv = (
            f"Weekly activity variability (CV over {settings.activity.window_days}-day periods): "
            f"{result.coefficient_of_variation:.2f}."
        )

    card_body_children = [html.H5(f"{status_emoji} {status_text}", className="card-title")]

    all_details_items = []
    if details_daily_low_activity:
        all_details_items.append(
            html.Li(details_daily_low_activity, className="small"))

    if details_weekly_cv:
        all_details_items.append(html.Li(details_weekly_cv, className="small"))

    if all_details_items:
        card_body_children.append(html.Ul(all_details_items, className="mt-2 mb-0"))

    return dbc.Card([
        dbc.CardHeader(title, id=header_id),
        dbc.CardBody(card_body_children, id=body_id)
    ], id=card_id, color=card_color, inverse=(card_color not in ["light", "white"]), className="mb-3")


def create_indicator_cards(df_commits, settings=None):
    settings = settings or load_configuration()
    return dbc.CardGroup(children=[
        card_unbalanced_participation(df_commits, settings=settings),
        card_process_warnings(df_commits, settings=settings),
        card_deadline_crunch_pattern(df_commits, settings=settings),
    ])
