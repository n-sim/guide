import logging
import os
import dash
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
cyto.load_extra_layouts()

app = Dash(title="GUIDE - Tutor Dashboard",
           external_stylesheets=[dbc.themes.UNITED],
           use_pages=True,
           suppress_callback_exceptions=True)

app.layout = html.Div(children=[
    dcc.Location(id='url'),
    dash.page_container
])

if __name__ == "__main__":
    app.run(host=os.getenv('HOST', '127.0.0.1'), port=int(os.getenv('PORT', '8050')), debug=False)
