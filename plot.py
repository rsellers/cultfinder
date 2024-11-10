import os
import json
import numpy as np  # For numerical computations
from datetime import datetime, timedelta
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import dash_table  # For data tables
import configparser  # For reading coins.ini

# Initialize the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server  # Expose the Flask server


# Path to the 'tg' directory containing project folders
TG_DIR = 'tg'

# Build the dropdown options and collect all rollup files
options = []
rollup_files = []
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
            rollup_files.append(full_path)
# Sort the options to group similar project names together
options.sort(key=lambda x: x['label'])

# Layout of the app with tabs
app.layout = html.Div([
    html.H1('Telegram Project Dashboard'),
    dcc.Tabs(id='tabs', value='emotion', children=[
        dcc.Tab(label='Emotion', value='emotion'),
        dcc.Tab(label='Leaderboard', value='leaderboard'),
        dcc.Tab(label='About', value='about'),
    ]),
    html.Div(id='tabs-content')
])
@app.callback(
    Output('tabs-content', 'children'),
    [Input('tabs', 'value')]
)
def render_content(tab):
    if tab == 'emotion':
        return render_emotion_tab()
    elif tab == 'leaderboard':
        return render_leaderboard_tab()
    elif tab == 'about':
        return render_about_tab()
    else:
        return []

def get_leaderboard_metrics_options():
    collected_metrics = set()
    for rollup_file in rollup_files:
        try:
            with open(rollup_file, 'r', encoding='utf-8') as f:
                rollup_data = json.load(f)
            date_data = rollup_data.get('date_data', {})
            if not date_data:
                continue
            sample_day_data = next(iter(date_data.values()))
            # Extract emotional_metrics
            if 'metrics' in sample_day_data and 'emotional_metrics' in sample_day_data['metrics']:
                emotional_metrics_keys = sample_day_data['metrics']['emotional_metrics'].keys()
                collected_metrics.update(emotional_metrics_keys)
            # Extract user_stats metrics
            if 'metrics' in sample_day_data and 'user_stats' in sample_day_data['metrics']:
                user_stats_keys = sample_day_data['metrics']['user_stats'].keys()
                collected_metrics.update(user_stats_keys)
        except Exception as e:
            print(f"Error processing rollup file '{rollup_file}': {e}")
            continue
    # Create metrics options
    metrics_options = [{'label': metric, 'value': metric} for metric in sorted(collected_metrics)]
    return metrics_options

def render_leaderboard_tab():
    metrics_options = get_leaderboard_metrics_options()
    content = [
        html.Div([
            html.Label('Window (days):'),
            dcc.Input(
                id='leaderboard-window',
                type='number',
                min=1,
                value=30,
                style={'width': '80px', 'margin-right': '20px'}
            ),
            html.Label('Show #:'),
            dcc.Input(
                id='leaderboard-show-n',
                type='number',
                min=1,
                value=5,
                style={'width': '80px', 'margin-right': '20px'}
            ),
        ], style={'display': 'flex', 'align-items': 'center', 'margin-bottom': '10px'}),
        html.Div([
            html.Label('Select Metrics:'),
            dcc.Checklist(
                id='leaderboard-metrics-checklist',
                options=metrics_options,
                value=[],    # Default to empty, user selects
                labelStyle={'display': 'inline-block', 'margin-right': '10px'}
            ),
        ], style={'margin-bottom': '20px'}),
        html.Div(id='leaderboard-tables')
    ]
    return content

def render_emotion_tab():
    return html.Div([
        html.Div([
            html.Label('Select a Project Rollup:'),
            dcc.Dropdown(
                id='project-dropdown',
                options=options,
                value=options[0]['value'] if options else None
            ),
            html.Div([
                dcc.Checklist(
                    id='metrics-checklist',
                    options=[],  # Options will be populated via callback
                    value=['fairness'],    # Default to ['fairness']
                    labelStyle={'display': 'inline-block', 'margin-right': '10px'}
                ),
                html.Label('SMOOTH'),
                dcc.Checklist(
                    id='smooth-checklist',
                    options=[{'label': '', 'value': 'smooth'}],
                    value=['smooth'],  # Default to 'smooth' on
                    labelStyle={'display': 'inline-block', 'margin-left': '10px'}
                ),
                html.Label('Number of days to smooth:'),
                dcc.Input(
                    id='smoothing-days',
                    type='number',
                    min=1,
                    value=3,  # Default value of 3
                    style={'width': '60px', 'margin-left': '10px'}
                ),
            ], style={'display': 'flex', 'align-items': 'center', 'margin-bottom': '10px'}),
        ]),
        dcc.Graph(id='metrics-graph'),
        html.Div(id='emotion-content'),
    ])

def render_about_tab():
    content = [
        html.H2('About'),
        html.P('This viewer is designed to provide insights into the emotional metrics of various Telegram project communities. It allows users to explore and compare different projects based on sentiment analysis and community engagement metrics derived from chat logs.'),
        html.H2('Emotional Metrics'),
    ]

    # Descriptions for each metric
    metrics_descriptions = {
        "meme_strength": {
            "description": "How powerful and engaging is the core idea or meme of the project?",
            "low_score": "Low score (bearish): The members do not have a central meme.",
            "high_score": "High score (bullish): Discussion revolves around a central meme."
        },
        "fairness": {
            "description": "Is the token or project fair to the participants?",
            "low_score": "Low score (bearish): Widespread belief the project is unfair.",
            "high_score": "High score (bullish): The project is widely accepted as being economically fair and evenly distributed."
        },
        "VC_cabal": {
            "description": "Is there sentiment that insiders, venture capitalists, or cabals are in control of the trajectory of the token price?",
            "low_score": "Low score (bearish): Widespread suspicion or complaints that venture capitalists, insiders, whales, or cabals are in control.",
            "high_score": "High score (bullish): Widespread belief that the community, not insiders, is in control."
        },
        "hold_intent": {
            "description": "Are people holding or selling tokens?",
            "low_score": "Low score (bearish): Everybody wants to sell the token.",
            "high_score": "High score (bullish): Everybody wants to 'hold forever' or have 'diamond hands'."
        },
        "vibes": {
            "description": "How good are the vibes within the chat log?",
            "low_score": "Low score (bearish): Widespread negativity, unsupportiveness, and harshness.",
            "high_score": "High score (bullish): An atmosphere of general support, encouragement, and generosity."
        },
        "emotional_intensity": {
            "description": "Is the discussion highly emotionally charged?",
            "low_score": "Low score (bearish): Flat, dry, technical, or matter-of-fact discussion.",
            "high_score": "High score (bullish): A highly emotionally charged environment across all participants."
        },
        "socioeconomic": {
            "description": "Are members of this group of high or low socioeconomic status?",
            "low_score": "Low score (bearish): All users are wealthy and well-connected elites.",
            "high_score": "High score (bullish): All users are of low socioeconomic status."
        },
        "price_action_focus": {
            "description": "Is there a strong focus on the token price in the conversations?",
            "low_score": "Low score (bearish): Absence of price discussion.",
            "high_score": "High score (bullish): Conversation revolves around price discussion."
        },
        "perceived_maximum_upside": {
            "description": "Do the participants express a strong belief in the potential of the project making them rich?",
            "low_score": "Low score (bearish): Nobody believes they will get rich.",
            "high_score": "High score (bullish): Widespread belief users will become rich after holding this token."
        },
        "free_cult_labor": {
            "description": "Are people volunteering significant time and effort for the project without compensation?",
            "low_score": "Low score (bearish): People are not participating in value-accretive activities whatsoever.",
            "high_score": "High score (bullish): Widespread value-accretive participation across all participants."
        },
        "community_health": {
            "description": "Does this appear to be a vibrant and lively discussion or is the community dead?",
            "low_score": "Low score (bearish): An anemic 'dead' community with little interesting discussion.",
            "high_score": "High score (bullish): A vibrant, diverse, healthy community with rich discussion."
        },
        "buy_inquiry": {
            "description": "Are newcomers asking where or how they can buy the token?",
            "low_score": "Low score (bearish): Nobody is asking where to buy the token.",
            "high_score": "High score (bullish): Widespread inquiries about where or how to purchase."
        },
        "inspiration": {
            "description": "Do community members get a sense of inspiration and hope from the community?",
            "low_score": "Low score (bearish): Nobody is expressing inspiration and hope.",
            "high_score": "High score (bullish): Widespread expressions of inspiration and hope gained from participating in the group."
        }
    }

    # For each metric, add the description and low/high score points
    for metric, info in metrics_descriptions.items():
        content.append(html.H3(metric))
        content.append(html.P(info['description']))
        content.append(html.Ul([
            html.Li([
                html.Strong('Low score (bearish):'),
                f' {info["low_score"].split(": ")[1]}'
            ]),
            html.Li([
                html.Strong('High score (bullish):'),
                f' {info["high_score"].split(": ")[1]}'
            ])
        ]))
    return content


# Callback to update the metrics options based on selected project
@app.callback(
    [Output('metrics-checklist', 'options'),
     Output('metrics-checklist', 'value')],
    [Input('project-dropdown', 'value')],
    [State('metrics-checklist', 'value')]
)
def update_metrics_options(selected_rollup_file, current_value):
    if selected_rollup_file is None:
        return [], []

    rollup_file = selected_rollup_file

    if not os.path.exists(rollup_file):
        return [], []

    # Load the rollup data to get metrics options
    try:
        with open(rollup_file, 'r', encoding='utf-8') as f:
            rollup_data = json.load(f)
    except Exception as e:
        print(f"Error loading rollup file: {e}")
        return [], []

    date_data = rollup_data.get('date_data', {})
    if not date_data:
        return [], []

    # Prepare metrics from 'emotional_metrics'
    sample_day_data = next(iter(date_data.values()))
    metrics = []
    emotional_metrics_list = []

    # Extract emotional_metrics
    if 'metrics' in sample_day_data and 'emotional_metrics' in sample_day_data['metrics']:
        emotional_metrics_keys = sample_day_data['metrics']['emotional_metrics'].keys()
        metrics.extend(emotional_metrics_keys)
        emotional_metrics_list.extend(emotional_metrics_keys)

    # Remove 'unique_user_count' and 'total_message_count' from the metrics options
    metrics_to_exclude = ['unique_user_count', 'total_message_count']
    metrics = [metric for metric in metrics if metric not in metrics_to_exclude]

    # Create metrics options
    metrics_options = [{'label': metric, 'value': metric} for metric in metrics]

    # Set default value to 'fairness' if it's available
    if 'fairness' in [option['value'] for option in metrics_options]:
        default_value = ['fairness']
    else:
        default_value = [metrics_options[0]['value']] if metrics_options else []

    # Preserve current selections if possible
    preserved_value = [val for val in current_value if val in [opt['value'] for opt in metrics_options]]
    if not preserved_value:
        preserved_value = default_value

    return metrics_options, preserved_value

# Callback to update the graph based on selected metrics and smoothing
@app.callback(
    Output('metrics-graph', 'figure'),
    [Input('project-dropdown', 'value'),
     Input('metrics-checklist', 'value'),
     Input('smooth-checklist', 'value'),
     Input('smoothing-days', 'value')]
)
def update_graph(selected_rollup_file, selected_metrics, smooth_options, smoothing_days):
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
    try:
        with open(rollup_file, 'r', encoding='utf-8') as f:
            rollup_data = json.load(f)
    except Exception as e:
        print(f"Error loading rollup file: {e}")
        return {}
    date_data = rollup_data.get('date_data', {})
    dates = sorted(date_data.keys())

    # Load price data if available
    price_data = {}
    if os.path.exists(price_file):
        try:
            with open(price_file, 'r', encoding='utf-8') as f:
                price_data = json.load(f)
        except Exception as e:
            print(f"Error loading price data: {e}")
    else:
        print(f"Price data file '{price_file}' not found. Proceeding without price data.")

    # Create subplots with metrics on top, user stats in the middle, and candlestick chart below
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=('Emotional Metrics', 'User Statistics', 'Daily Candlestick Chart'),
        specs=[[{}],
               [{"secondary_y": True}],
               [{}]]
    )

    # Determine if smoothing is enabled
    smoothing_enabled = 'smooth' in smooth_options
    smoothing_days = max(1, int(smoothing_days) if smoothing_days else 3)  # Ensure at least 1 day

    # --- Emotional Metrics Data (Row 1) ---
    for metric in selected_metrics:
        y_values = []
        customdata = []  # To store context or None
        for date in dates:
            day_data = date_data[date]
            metric_value = None
            context = None

            # Check for emotional_metrics
            try:
                emotional_metrics = day_data['metrics'].get('emotional_metrics', {})
                if metric in emotional_metrics:
                    metric_value = emotional_metrics[metric]['intensity']
                    context = emotional_metrics[metric]['context']
            except KeyError as e:
                print(f"KeyError in emotional_metrics for date {date}: {e}")

            y_values.append(metric_value)
            customdata.append(context)

        # Skip metrics with no data
        if all(v is None for v in y_values):
            continue

        # Apply smoothing if enabled
        if smoothing_enabled:
            # Convert y_values to numpy array, replace None with np.nan
            y_array = np.array([float(v) if v is not None else np.nan for v in y_values])
            window = int(smoothing_days)
            # Handle NaNs during convolution
            weights = np.ones(window)
            sums = np.convolve(np.nan_to_num(y_array), weights, 'same')
            counts = np.convolve(~np.isnan(y_array), weights, 'same')
            with np.errstate(invalid='ignore'):
                y_smoothed = sums / counts
            y_smoothed[counts == 0] = np.nan  # Avoid division by zero
            y_values = y_smoothed.tolist()
        else:
            # Ensure y_values is a list of floats for consistency
            y_values = [float(y) if y is not None else None for y in y_values]

        # Set hovertemplate
        if any(customdata):
            hovertemplate = '<b>%{y}</b><br>Date: %{x}<br>Context: %{customdata}<extra></extra>'
        else:
            hovertemplate = '<b>%{y}</b><br>Date: %{x}<extra></extra>'
        trace = go.Scatter(
            x=dates,
            y=y_values,
            mode='lines+markers',
            name=metric + (' (Smoothed)' if smoothing_enabled else ''),
            customdata=customdata,
            hovertemplate=hovertemplate
        )
        fig.add_trace(trace, row=1, col=1)

    # Set y-axis range for emotional metrics to 0-100
    fig.update_yaxes(range=[0, 100], row=1, col=1)

    # --- User Statistics (Row 2) ---
    # Prepare data for unique_user_count and total_message_count
    user_stats_metrics = ['unique_user_count', 'total_message_count']
    user_stats_data = {metric: [] for metric in user_stats_metrics}
    for date in dates:
        day_data = date_data[date]
        for metric in user_stats_metrics:
            value = None
            try:
                user_stats = day_data['metrics'].get('user_stats', {})
                if metric in user_stats:
                    value = user_stats[metric]
            except KeyError as e:
                print(f"KeyError in user_stats for date {date}: {e}")
            user_stats_data[metric].append(value)

    # Plot unique_user_count on the left y-axis
    trace_users = go.Scatter(
        x=dates,
        y=user_stats_data['unique_user_count'],
        mode='lines+markers',
        name='Unique User Count',
        marker_color='blue',
        yaxis='y1'
    )
    fig.add_trace(trace_users, row=2, col=1)

    # Plot total_message_count on the right y-axis
    trace_messages = go.Scatter(
        x=dates,
        y=user_stats_data['total_message_count'],
        mode='lines+markers',
        name='Total Message Count',
        marker_color='red',
        yaxis='y2'
    )
    fig.add_trace(trace_messages, row=2, col=1, secondary_y=True)

    # Update y-axes labels and titles for user stats
    fig.update_yaxes(title_text='Unique User Count', row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text='Total Message Count', row=2, col=1, secondary_y=True)

    # --- Price Data (Row 3) ---
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

        # Add candlestick to the third row
        fig.add_trace(candlestick, row=3, col=1)

    else:
        print(f"No price data available for project '{project_name}'.")

    # Update layout
    fig.update_layout(
        title=f"Metrics and Price for '{rollup_filename}'",
        hovermode='x unified',
        height=1000
    )

    # Update x-axis titles
    fig.update_xaxes(title_text='Date', row=3, col=1)

    # Update y-axis titles
    fig.update_yaxes(title_text='Emotional Metric Value', row=1, col=1)
    fig.update_yaxes(title_text='Price (USD)', row=3, col=1)

    return fig

# Callback to update the emotion content (Catchphrase & Socials)
@app.callback(
    Output('emotion-content', 'children'),
    [Input('project-dropdown', 'value')]
)
def update_emotion_content(selected_rollup_file):
    if selected_rollup_file is None:
        return []

    rollup_file = selected_rollup_file

    if not os.path.exists(rollup_file):
        return []

    # Extract the project folder and project name from the rollup_file path
    project_folder = os.path.dirname(rollup_file)
    project_name = os.path.basename(project_folder)

    # Load the rollup data
    try:
        with open(rollup_file, 'r', encoding='utf-8') as f:
            rollup_data = json.load(f)
    except Exception as e:
        print(f"Error loading rollup file: {e}")
        return []

    date_data = rollup_data.get('date_data', {})
    if not date_data:
        return []

    # --- Existing code for Catchphrase & Socials ---
    # Process data to tally socials
    social_account_counts = {}
    for date in date_data:
        day_data = date_data[date]
        try:
            socials = day_data['metrics'].get('socials', {})
            top_accounts = socials.get('top_mentioned_accounts', [])
            for account in top_accounts:
                url = account['url']
                mentions = account['mentions']
                if url in social_account_counts:
                    social_account_counts[url] += mentions
                else:
                    social_account_counts[url] = mentions
        except KeyError as e:
            print(f"KeyError in socials processing for date {date}: {e}")
            continue

    # Get top 10 social accounts
    sorted_social_accounts = sorted(social_account_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Build the socials table data
    socials_table_data = []
    for url, count in sorted_social_accounts:
        # Build markdown link
        account_link = f'[{url}]({url})'
        socials_table_data.append({'Total references': count, 'Social media account': account_link})

    # Process data to tally catchphrases
    catchphrase_counts = {}
    for date in date_data:
        day_data = date_data[date]
        try:
            catchphrase = day_data['metrics'].get('catch_phrase', None)
            if catchphrase:
                if catchphrase in catchphrase_counts:
                    catchphrase_counts[catchphrase] += 1
                else:
                    catchphrase_counts[catchphrase] = 1
        except KeyError as e:
            print(f"KeyError in catchphrase processing for date {date}: {e}")
            continue

    # Get top 10 catchphrases
    sorted_catchphrases = sorted(catchphrase_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Build the catchphrases table data
    catchphrase_table_data = [{'Total occurrences': count, 'Catchphrase': phrase} for phrase, count in sorted_catchphrases]

    # --- New code for Coin Info ---
    # Read coins.ini
    config = configparser.ConfigParser()
    coins_ini_path = os.path.join(os.getcwd(), 'coins.ini')
    if not os.path.exists(coins_ini_path):
        print(f"coins.ini file not found at {coins_ini_path}")
        coin_info_table_data = [{'Attribute': 'Error', 'Value': 'coins.ini not found'}]
    else:
        config.read(coins_ini_path)
        if project_name in config.sections():
            coin_info = config[project_name]
            # Extract required fields
            coin_attributes = ['api_id', 'chain', 'ca', 'twitter', 'tg']
            coin_info_table_data = []
            for attr in coin_attributes:
                value = coin_info.get(attr, 'N/A')
                coin_info_table_data.append({'Attribute': attr, 'Value': value})
        else:
            print(f"Project '{project_name}' not found in coins.ini")
            coin_info_table_data = [{'Attribute': 'Error', 'Value': f"Project '{project_name}' not found in coins.ini"}]

    # Build the content
    content = [
        html.H2('Catchphrase & Socials'),
        html.H3('Top 10 Social Media Accounts'),
        dash_table.DataTable(
            id='socials-table',
            columns=[
                {'name': 'Total references', 'id': 'Total references'},
                {'name': 'Social media account', 'id': 'Social media account', 'presentation': 'markdown'}
            ],
            data=socials_table_data,
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_as_list_view=True,
            style_header={'backgroundColor': 'white', 'fontWeight': 'bold'},
            style_table={'margin': '0', 'padding': '0', 'border': 'none'}
        ),
        html.H3('Top 10 Catchphrases'),
        dash_table.DataTable(
            id='catchphrases-table',
            columns=[
                {'name': 'Total occurrences', 'id': 'Total occurrences'},
                {'name': 'Catchphrase', 'id': 'Catchphrase'}
            ],
            data=catchphrase_table_data,
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_as_list_view=True,
            style_header={'backgroundColor': 'white', 'fontWeight': 'bold'},
            style_table={'margin': '0', 'padding': '0', 'border': 'none'}
        ),
        html.H3('Coin Info'),
        dash_table.DataTable(
            id='coin-info-table',
            columns=[
                {'name': 'Attribute', 'id': 'Attribute'},
                {'name': 'Value', 'id': 'Value'}
            ],
            data=coin_info_table_data,
            style_cell={'textAlign': 'left'},
            style_as_list_view=True,
        ),
    ]

    return content


@app.callback(
    Output('leaderboard-tables', 'children'),
    [Input('leaderboard-window', 'value'),
     Input('leaderboard-show-n', 'value'),
     Input('leaderboard-metrics-checklist', 'value')]
)
def update_leaderboard(window_days, show_n, selected_metrics):
    # Ensure window_days and show_n are valid
    window_days = max(1, int(window_days) if window_days else 30)
    show_n = max(1, int(show_n) if show_n else 5)

    if not selected_metrics:
        return html.Div("Please select at least one metric to display the leaderboard.")

    # Initialize dictionary to hold the average scores for each project
    project_scores = {}  # Key: project_name, Value: average_score

    # Iterate over each rollup file to compute scores
    for rollup_file in rollup_files:
        # Extract the project folder and project name from the rollup_file path
        project_folder = os.path.dirname(rollup_file)
        project_name = os.path.basename(project_folder)
        rollup_filename = os.path.splitext(os.path.basename(rollup_file))[0]
        project_label = f"{project_name}"

        # Load rollup data
        try:
            with open(rollup_file, 'r', encoding='utf-8') as f:
                rollup_data = json.load(f)
        except Exception as e:
            print(f"Error loading rollup file '{rollup_file}': {e}")
            continue

        date_data = rollup_data.get('date_data', {})
        if not date_data:
            continue  # No data for this project

        dates = sorted(date_data.keys())
        # Get the most recent date
        most_recent_date_str = dates[-1]
        try:
            most_recent_date = datetime.strptime(most_recent_date_str, '%Y-%m-%d')
        except ValueError:
            print(f"Invalid date format '{most_recent_date_str}' in '{rollup_file}'. Skipping.")
            continue

        # Determine the start date for the window
        start_date = most_recent_date - timedelta(days=window_days - 1)
        start_date_str = start_date.strftime('%Y-%m-%d')

        # Collect data within the window
        window_dates = [date for date in dates if date >= start_date_str]
        if not window_dates:
            continue  # No data within the window

        # Initialize list to collect metric values
        metric_values = {metric: [] for metric in selected_metrics}
        for date in window_dates:
            day_data = date_data[date]

            # Get emotional_metrics
            emotional_metrics = day_data.get('metrics', {}).get('emotional_metrics', {})
            for metric in selected_metrics:
                if metric in emotional_metrics:
                    value = emotional_metrics[metric].get('intensity')
                    if value is not None:
                        metric_values[metric].append(value)

            # Get user_stats
            user_stats = day_data.get('metrics', {}).get('user_stats', {})
            for metric in selected_metrics:
                if metric in user_stats:
                    value = user_stats.get(metric)
                    if value is not None:
                        metric_values[metric].append(value)

        # Compute average for the selected metrics
        total_score = 0
        count = 0
        for metric in selected_metrics:
            values = metric_values.get(metric, [])
            if values:
                average_value = sum(values) / len(values)
                total_score += average_value
                count += 1
        if count > 0:
            project_scores[project_label] = total_score / count

    if not project_scores:
        return html.Div("No data available for the selected metrics and window.")

    # Sort the projects based on the average score
    sorted_scores = sorted(project_scores.items(), key=lambda x: x[1], reverse=True)

    # Prepare data for top N
    top_n_projects = sorted_scores[:show_n]
    top_n_data = []
    rank = 1
    for project_label, score in top_n_projects:
        top_n_data.append({'Rank': rank, 'Project': project_label, 'Score': round(score, 2)})
        rank += 1

    # Prepare data for bottom N
    bottom_n_projects = sorted_scores[-show_n:]
    bottom_n_projects = list(reversed(bottom_n_projects))  # So that rank is from worst to better
    bottom_n_data = []
    rank = len(sorted_scores) - show_n + 1
    for project_label, score in bottom_n_projects:
        bottom_n_data.append({'Rank': rank, 'Project': project_label, 'Score': round(score, 2)})
        rank += 1

    # Create tables
    tables = []
    metric_label = ', '.join(selected_metrics)
    tables.append(html.H3(f'Top {show_n} Projects for {metric_label}'))
    tables.append(dash_table.DataTable(
        columns=[
            {'name': 'Rank', 'id': 'Rank'},
            {'name': 'Project', 'id': 'Project'},
            {'name': 'Score', 'id': 'Score', 'type': 'numeric', 'format': {'specifier': '.2f'}}
        ],
        data=top_n_data,
        style_cell={'textAlign': 'left', 'padding': '5px'},
        style_as_list_view=True,
        style_header={'backgroundColor': 'white', 'fontWeight': 'bold'},
        style_table={'margin': '0', 'padding': '0', 'border': 'none'}
    ))

    tables.append(html.H3(f'Bottom {show_n} Projects for {metric_label}'))
    tables.append(dash_table.DataTable(
        columns=[
            {'name': 'Rank', 'id': 'Rank'},
            {'name': 'Project', 'id': 'Project'},
            {'name': 'Score', 'id': 'Score', 'type': 'numeric', 'format': {'specifier': '.2f'}}
        ],
        data=bottom_n_data,
        style_cell={'textAlign': 'left', 'padding': '5px'},
        style_as_list_view=True,
        style_header={'backgroundColor': 'white', 'fontWeight': 'bold'},
        style_table={'margin': '0', 'padding': '0', 'border': 'none'}
    ))
    return tables


# Callback to render content based on selected tab
@app.callback(
    Output('about-content', 'children'),
    [Input('tabs', 'value')]
)
def render_about_content(tab):
    if tab == 'about':
        return render_about_tab()
    else:
        return []


if __name__ == '__main__':
    app.run_server(debug=True)
