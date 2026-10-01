from analysis.chart_data import git_graph_elements
import dash_cytoscape as cyto
from dash import html, callback, Output, Input


def create_git_graph_plot(df_commits, df_commit_parents, author_color_map):
    return html.Div(
        style={
            'position': 'relative',
            'height': '900px',
            'border': '1px solid lightgrey'
        },
        children=[
            html.Div(
                id='commit-message-box',
                style={
                    'position': 'absolute',
                    'top': '10px',
                    'left': '10px',
                    'width': '30%',
                    'padding': '10px',
                    'border': '1px solid #ddd',
                    'background-color': 'rgba(250, 250, 250, 0.95)',
                    'z-index': '10',
                    'overflow-y': 'auto',
                    'box-shadow': '2px 2px 5px rgba(0,0,0,0.1)'
                }
            ),
            _create_git_graph(df_commits, df_commit_parents, author_color_map)
        ]
    )

def _create_git_graph(df_commits, df_commit_parents, author_color_map):
    cytoscape_elements = git_graph_elements(df_commits, df_commit_parents)
    for element in cytoscape_elements:
        data = element['data']
        if 'id' in data:
            data['node_color'] = author_color_map.get(
                data['author_email'], author_color_map.get('unknown@example.com', '#D3D3D3'))

    return cyto.Cytoscape(
                id='git-cytoscape-graph',
                elements=cytoscape_elements,
                style={'width': '100%', 'height': '100%', 'background-color': '#f9f9f9'},
                zoom=2,
                layout={
                    'name': 'dagre',
                    'rankDir': 'TB',
                    'spacingFactor': 1.2,
                    'fit': False
                },
                stylesheet=[
                    {
                        'selector': 'node',
                        'style': {
                            'content': 'data(label)',
                            'text-valign': 'center',
                            'shape': 'round-rectangle',
                            'width': '70px',
                            'height': '30px',
                            'font-size': '10px',
                            'background-color': 'data(node_color)',
                            'border-width': 1,
                            'border-color': '#555'
                        }
                    },
                    {
                        'selector': 'edge',
                        'style': {
                            'curve-style': 'bezier',
                            'target-arrow-shape': 'triangle',
                            'width': 2,
                        }
                    },
                    {
                        'selector': ':selected',
                        'style': {
                            'border-width': 3,
                            'border-color': 'black'
                        }
                    }
                ]
            )

@callback(
    Output('commit-message-box', 'children'),
    Input('git-cytoscape-graph', 'tapNodeData')
)
def display_tap_node_data(node_data):
    if node_data:
        commit_hash_short = node_data['id'][:7]
        subject = node_data.get('message_subject', "N/A")
        body = node_data.get('message_body', "")
        author_email = node_data.get('author_email', "")

        return [
            html.H5(f"Commit: {commit_hash_short}", style={'margin-top': '0', 'margin-bottom': '5px'}),
            html.Strong("Author: "), html.Span(author_email),
            html.Br(),
            html.Strong("Subject: "), html.Span(subject),
            html.Hr(style={'margin': '5px 0'}),
            html.Strong("Body:"),
            html.Pre(body, style={'white-space': 'pre-wrap', 'word-break': 'break-word', 'margin-top': '5px'})
        ]
    return "Click on a commit node to see its message."