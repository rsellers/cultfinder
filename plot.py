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
    html.H1('C U L T F I N D E R'),
    html.Label('Select a memecoin:'),
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