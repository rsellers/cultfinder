#plot.py
import os
import json
from datetime import datetime
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go

# Initialize the Dash app
app = dash.Dash(__name__)

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
    
    # Load the rollup data
    with open(rollup_file, 'r', encoding='utf-8') as f:
        rollup_data = json.load(f)
    
    # Extract date-wise data
    date_data = rollup_data.get('date_data', {})
    dates = sorted(date_data.keys())
    
    # Prepare metrics
    metrics = ['message_count_ex_bot', 'user_count_ex_bot'] + list(next(iter(date_data.values()))['emotional_metrics'].keys())
    metrics_options = [{'label': metric, 'value': metric} for metric in metrics]
    
    return html.Div([
        dcc.Checklist(
            id='metrics-checklist',
            options=metrics_options,
            value=['message_count_ex_bot', 'user_count_ex_bot'],
            labelStyle={'display': 'inline-block', 'margin-right': '10px'}
        ),
        dcc.Graph(id='metrics-graph'),
    ])

# Callback to update the graph based on selected metrics
@app.callback(
    Output('metrics-graph', 'figure'),
    [Input('project-dropdown', 'value'),
     Input('metrics-checklist', 'value')]
)
def update_graph(selected_project, selected_metrics):
    if selected_project is None or not selected_metrics:
        return {}
    
    # Path to the rollup JSON file
    rollup_file = os.path.join(TG_DIR, selected_project, f"{selected_project}_rollup.json")
    
    if not os.path.exists(rollup_file):
        return {}
    
    # Load the rollup data
    with open(rollup_file, 'r', encoding='utf-8') as f:
        rollup_data = json.load(f)
    
    # Extract date-wise data
    date_data = rollup_data.get('date_data', {})
    dates = sorted(date_data.keys())
    
    # Prepare data for plotting
    data = []
    for metric in selected_metrics:
        y_values = []
        for date in dates:
            day_data = date_data[date]
            if metric in day_data:
                y_values.append(day_data[metric])
            elif 'emotional_metrics' in day_data and metric in day_data['emotional_metrics']:
                y_values.append(day_data['emotional_metrics'][metric]['intensity'])
            else:
                y_values.append(None)  # Handle missing data
        data.append(go.Scatter(
            x=dates,
            y=y_values,
            mode='lines+markers',
            name=metric
        ))
    
    # Create the figure
    figure = {
        'data': data,
        'layout': go.Layout(
            title=f"Metrics for Project '{selected_project}'",
            xaxis={'title': 'Date'},
            yaxis={'title': 'Value'},
            hovermode='closest'
        )
    }
    
    return figure

if __name__ == '__main__':
    app.run_server(debug=True)