import os
import json
from datetime import datetime
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from plotly.subplots import make_subplots


app = dash.Dash(__name__)
server = app.server  # Expose the Flask server

# Path to the 'tg' directory containing project folders
TG_DIR = 'tg'

# Get the list of projects (subdirectories in TG_DIR)
projects = [d for d in os.listdir(TG_DIR) if os.path.isdir(os.path.join(TG_DIR, d))]

# Layout of the app
app.layout = html.Div([
    html.H1('Telegram Project Dashboard'),
    html.Label('Select a Project:'),
    dcc.Dropdown(
        id='project-dropdown',
        options=[{'label': project, 'value': project} for project in projects],
        value=projects[0] if projects else None
    ),
    html.Div(id='output-container'),
])

# Callback to update the dashboard based on selected project
@app.callback(
    Output('output-container', 'children'),
    [Input('project-dropdown', 'value')]
)
def update_dashboard(selected_project):
    if selected_project is None:
        return html.Div("No projects available.")

    # Path to the rollup JSON file
    rollup_file = os.path.join(TG_DIR, selected_project, f"{selected_project}_rollup.json")

    if not os.path.exists(rollup_file):
        return html.Div(f"Rollup file for project '{selected_project}' not found.")

    # Load the rollup data to get metrics options
    with open(rollup_file, 'r', encoding='utf-8') as f:
        rollup_data = json.load(f)

    date_data = rollup_data.get('date_data', {})
    if not date_data:
        return html.Div("No date data available in the rollup file.")

    # Prepare metrics
    metrics = ['message_count_ex_bot', 'user_count_ex_bot'] + list(next(iter(date_data.values()))['emotional_metrics'].keys())
    metrics_options = [{'label': metric, 'value': metric} for metric in metrics]

    # Build the layout
    layout_children = [
        dcc.Checklist(
            id='metrics-checklist',
            options=metrics_options,
            value=['message_count_ex_bot', 'user_count_ex_bot'],
            labelStyle={'display': 'inline-block', 'margin-right': '10px'}
        ),
        dcc.Graph(id='metrics-graph'),
    ]

    return html.Div(layout_children)

# Updated update_graph function
@app.callback(
    Output('metrics-graph', 'figure'),
    [Input('project-dropdown', 'value'),
     Input('metrics-checklist', 'value')]
)

def update_graph(selected_project, selected_metrics):
    if selected_project is None or not selected_metrics:
        return {}

    # Paths to data files
    rollup_file = os.path.join(TG_DIR, selected_project, f"{selected_project}_rollup.json")
    price_file = os.path.join(TG_DIR, selected_project, f"{selected_project}_price.json")

    # Check if data files exist
    if not os.path.exists(rollup_file):
        return {}
    if not os.path.exists(price_file):
        print(f"Price data file '{price_file}' not found.")
        # Depending on your preference, you can decide to proceed without the price data.

    # Load data
    with open(rollup_file, 'r', encoding='utf-8') as f:
        rollup_data = json.load(f)
    date_data = rollup_data.get('date_data', {})
    dates = sorted(date_data.keys())

    # Load price data if available
    price_data = {}
    if os.path.exists(price_file):
        with open(price_file, 'r', encoding='utf-8') as f:
            price_data = json.load(f)

    # Create subplots with metrics on top and candlestick chart below
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=('Metrics', 'Daily Candlestick Chart')
    )

    # --- Metrics Data (Row 1) ---
    for metric in selected_metrics:
        y_values = []
        customdata = []  # To store context or None
        for date in dates:
            day_data = date_data[date]
            if metric in day_data:
                # For 'message_count_ex_bot' and 'user_count_ex_bot'
                y_values.append(day_data[metric])
                customdata.append(None)  # No additional context
            elif 'emotional_metrics' in day_data and metric in day_data['emotional_metrics']:
                # For emotional metrics
                intensity = day_data['emotional_metrics'][metric]['intensity']
                context = day_data['emotional_metrics'][metric]['context']
                y_values.append(intensity)
                customdata.append(context)
            else:
                y_values.append(None)  # Handle missing data
                customdata.append(None)
        # Set hovertemplate
        if any(customdata):
            hovertemplate = '<b>%{y}</b><br>Date: %{x}<br>Context: %{customdata}<extra></extra>'
        else:
            hovertemplate = '<b>%{y}</b><br>Date: %{x}<extra></extra>'
        trace = go.Scatter(
            x=dates,
            y=y_values,
            mode='lines+markers',
            name=metric,
            customdata=customdata,
            hovertemplate=hovertemplate
        )
        fig.add_trace(trace, row=1, col=1)

    # --- Price Data (Row 2) ---
    if price_data:
        price_dates = []
        opens = []
        highs = []
        lows = []
        closes = []
        for date in sorted(price_data.keys()):
            price_dates.append(date)
            day_data = price_data[date]
            opens.append(day_data['open'])
            highs.append(day_data['high'])
            lows.append(day_data['low'])
            closes.append(day_data['close'])

        # Create the candlestick trace
        candlestick = go.Candlestick(
            x=price_dates,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
            name='Price'
        )

        # Add candlestick to the second row
        fig.add_trace(candlestick, row=2, col=1)

    else:
        print(f"No price data available for project '{selected_project}'.")

    # Update layout
    fig.update_layout(
        title=f"Metrics and Price for Project '{selected_project}'",
        hovermode='x unified',
        height=800
    )

    # Update x-axis titles
    fig.update_xaxes(title_text='Date', row=2, col=1)

    # Update y-axis titles
    fig.update_yaxes(title_text='Metrics Value', row=1, col=1)
    fig.update_yaxes(title_text='Price (USD)', row=2, col=1)

    return fig


if __name__ == '__main__':
    app.run_server(debug=True)