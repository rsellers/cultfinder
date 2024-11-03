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
    html.H1('C U L T F I N D E R'),
    html.Label('Select a memecoin:'),
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
        
        # Add the descriptive text and external links
        html.Div([
            html.H4("Additional Information"),
            html.P("This dashboard provides an overview of chat log emotional metrics and price data for various memecoin projects."),
            html.A("Github", href="https://github.com/rsellers/cultfinder", target="_blank"),
            html.Br(),
            
            html.H4("gpt4o-mini promp guidelines for memecoin telegram channels"),
            html.P([html.Strong("concept_or_meme_strength: "), "Evaluate how powerful and engaging the core idea or meme of the project is. 0 indicates the members are not focused on the idea, 100 indicates the topic is universally captivating."]),
            html.P([html.Strong("fairness: "), "Is the token or project perceived to be fair to the participants? 0 indicates widespread suspicion or discontent, 100 indicates the project or idea is widely accepted as being economically fair and evenly distributed."]),
            html.P([html.Strong("VC_cabal: "), "Is there a widespread sentiment that large insiders, venture capitalists with large allocations, or 'cabals' are in control of the trajectory of the token price? 0 indicates widespread belief that venture capitalists, insiders, whales, or cabals are in control, 100 indicates a widespread belief that the community-at-large is in control and not select insiders."]),
            html.P([html.Strong("sell_intent: "), "Are people openly planning or in the process of selling tokens? 0 indicates an open and widespread expression of intent to sell by the community, 100 indicates widespread sentiments to 'hold forever' or have 'diamond hands' or 'price doesn't matter'."]),
            html.P([html.Strong("vibes: "), "How good are the vibes within the chat log? 0 indicates widespread negativity, unsupportiveness and harshness, 100 an atmosphere of general support, encouragement and generosity."]),
            html.P([html.Strong("comunity_strength: "), "Is this a tight-knit community? 0 indicates community members regard each other as strangers, 100 indicates an intimate and personal connection between all participants."]),
            html.P([html.Strong("emotional_intensity: "), "Is the discussion highly emotionally charged? 0 indicates a flat or dry discussion, 100 indicates a highly emotionally charged environment across all participants."]),
            html.P([html.Strong("stickiness: "), "Ignoring repeated messages in a short period of time, do users return and contribute messages and discussion across many hours or days? 0 indicates most users do not return to make multiple messages throughout the session duration, 100 indicates all users are contributing throughout the duration of the chat log."]),
            html.P([html.Strong("socioeconomic: "), "Reading from clues within the chat group such as mentions of low disposable income, poor upbringing, living in 3rd-world or marginalized communities, are members of this group of high or low socioeconomic status? 0 indicates all users are of low socioeconomic status, 100 indicates all users wealthy and well-connected elites."]),
            html.P([html.Strong("price_action_focus: "), "Is there a strong focus on the token price in the conversations? 0 indicates no discussion of price action, 100 indicates widespread reaction to price movements and overall fixation on price."]),
            html.P([html.Strong("perceived_maximum_upside: "), "Do the participants express a strong belief in the potential of the project making them rich? 0 indicates widespread disbelief or suspicion that participation will make users rich, 100 indicates widespread belief users will become rich after holding this token."]),
            html.P([html.Strong("free_cult_labor: "), "Are people volunteering significant time and effort for the project without compensation, for example: participating in social media 'raids', creating original memes, evangelizing the project? 0 indicates people are not participating in value accretive activities whatsoever, 100 indicates widespread value accretive participation across the whole set of participants."]),
            html.P([html.Strong("community_health: "), "Does this appear to be a vibrant and growing community or is the community 'dead'? 0 indicates an anemic 'dead' community, 100 indicates a vibrant healthy community."]),
            html.P([html.Strong("buy_inquiry: "), "Are newcomers asking where or how they can buy the token? 0 indicates nobody is asking where to buy the token, 100 indicates widespread inquiries about where or how to purchase."]),
            html.P([html.Strong("inspiration: "), "Do community members derive a sense of inspiration and hope from the community? 0 indicates that nobody is expressing inspiration and hope, 100 indicates widespread expressions of inspiration and hope gained from participating in the group."])
        ], style={'marginTop': '20px', 'padding': '10px', 'borderTop': '1px solid #ddd'})
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
