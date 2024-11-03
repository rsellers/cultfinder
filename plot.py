import os
import json
from datetime import datetime
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from plotly.subplots import make_subplots

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server  # Expose the Flask server

# Path to the 'tg' directory containing project folders
TG_DIR = 'tg'

# Build the dropdown options
options = []
for root, dirs, files in os.walk(TG_DIR):
    # Only consider subdirectories directly under TG_DIR
    if os.path.dirname(root) != TG_DIR and root != TG_DIR:
        continue
    # Check if the folder contains at least one rollup file
    rollup_files_in_folder = [file for file in files if 'rollup' in file and file.endswith('.json')]
    if rollup_files_in_folder:
        project_name = os.path.basename(root)
        for file in rollup_files_in_folder:
            full_path = os.path.join(root, file)
            # Get the filename without extension
            filename_without_ext = os.path.splitext(file)[0]
            label = f"{project_name} / {filename_without_ext}"
            options.append({'label': label, 'value': full_path})
# Sort the options to group similar project names together
options.sort(key=lambda x: x['label'])

# Layout of the app
app.layout = html.Div([
    html.H1('Telegram Project Dashboard'),
    html.Label('Select a Project Rollup:'),
    dcc.Dropdown(
        id='project-dropdown',
        options=options,
        value=options[0]['value'] if options else None
    ),
    html.Div(id='output-container'),
])

# Callback to update the dashboard based on selected project
@app.callback(
    Output('output-container', 'children'),
    [Input('project-dropdown', 'value')]
)
def update_dashboard(selected_rollup_file):
    if selected_rollup_file is None:
        return html.Div("No rollup files available.")

    rollup_file = selected_rollup_file

    if not os.path.exists(rollup_file):
        return html.Div(f"Rollup file '{rollup_file}' not found.")

    # Load the rollup data to get metrics options
    with open(rollup_file, 'r', encoding='utf-8') as f:
        rollup_data = json.load(f)

    date_data = rollup_data.get('date_data', {})
    if not date_data:
        return html.Div("No date data available in the rollup file.")

    # Prepare metrics from 'emotional_metrics' and 'user_stats'
    sample_day_data = next(iter(date_data.values()))
    metrics = []

    # Extract emotional_metrics
    if 'metrics' in sample_day_data and 'emotional_metrics' in sample_day_data['metrics']:
        emotional_metrics_keys = sample_day_data['metrics']['emotional_metrics'].keys()
        metrics.extend(emotional_metrics_keys)

    # Extract user_stats metrics
    if 'metrics' in sample_day_data and 'user_stats' in sample_day_data['metrics']:
        user_stats_keys = sample_day_data['metrics']['user_stats'].keys()
        metrics.extend(user_stats_keys)

    if not metrics:
        return html.Div("No metrics available in the rollup file.")

    # Create metrics options for checkboxes
    metrics_options = [{'label': metric, 'value': metric} for metric in metrics]

    # Build the layout
    layout_children = [
        dcc.Checklist(
            id='metrics-checklist',
            options=metrics_options,
            value=metrics[:5],  # Default to the first 5 metrics
            labelStyle={'display': 'inline-block', 'margin-right': '10px'}
        ),
        dcc.Graph(id='metrics-graph'),
    ]

    return html.Div(layout_children)

# Callback to update the graph based on selected metrics
@app.callback(
    Output('metrics-graph', 'figure'),
    [Input('project-dropdown', 'value'),
     Input('metrics-checklist', 'value')]
)
def update_graph(selected_rollup_file, selected_metrics):
    if selected_rollup_file is None or not selected_metrics:
        return {}

    rollup_file = selected_rollup_file

    # Extract the project folder and project name from the rollup_file path
    project_folder = os.path.dirname(rollup_file)
    project_name = os.path.basename(project_folder)
    rollup_filename = os.path.splitext(os.path.basename(rollup_file))[0]

    # Paths to data files
    price_file = os.path.join(project_folder, f"{project_name}_price.json")

    # Load rollup data
    with open(rollup_file, 'r', encoding='utf-8') as f:
        rollup_data = json.load(f)
    date_data = rollup_data.get('date_data', {})
    dates = sorted(date_data.keys())

    # Load price data if available
    price_data = {}
    if os.path.exists(price_file):
        with open(price_file, 'r', encoding='utf-8') as f:
            price_data = json.load(f)
    else:
        print(f"Price data file '{price_file}' not found. Proceeding without price data.")

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
            metric_value = None
            context = None

            # Check for emotional_metrics
            if 'metrics' in day_data and 'emotional_metrics' in day_data['metrics']:
                emotional_metrics = day_data['metrics']['emotional_metrics']
                if metric in emotional_metrics:
                    metric_value = emotional_metrics[metric]['intensity']
                    context = emotional_metrics[metric]['context']

            # Check for user_stats
            if metric_value is None and 'metrics' in day_data and 'user_stats' in day_data['metrics']:
                user_stats = day_data['metrics']['user_stats']
                if metric in user_stats:
                    metric_value = user_stats[metric]
                    context = None  # No context for user_stats

            y_values.append(metric_value)
            customdata.append(context)

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
        print(f"No price data available for project '{project_name}'.")

    # Update layout
    fig.update_layout(
        title=f"Metrics and Price for '{rollup_filename}'",
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
