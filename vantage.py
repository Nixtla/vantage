import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict
import time
import os



# Fetching data with caching
@st.cache_data(ttl=100)
def fetch_data(url, headers):
    response = requests.get(url, headers=headers)
    return response.json()


def create_figure(title, xaxis_title, yaxis_title, yaxis_range=None):
    fig = go.Figure()
    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        autosize=False,
        width=800,
        height=500,
        yaxis=dict(range=yaxis_range) if yaxis_range else None,
    )
    return fig


def add_trace(fig, x, y, mode, name):
    fig.add_trace(go.Scatter(x=x, y=y, mode=mode, name=name))
    return fig


def add_confidence_interval(fig, x, lo, hi, color='rgba(0,176,246,0.2)'):
    fig.add_trace(go.Scatter(
        x=x + x[::-1],
        y=hi + lo[::-1],
        fill='toself',
        fillcolor=color,
        line_color='rgba(255,255,255,0)',
        showlegend=False,
        name='Confidence Interval',
    ))
    return fig

@st.cache_data(ttl=15)
def post_request(url, data):
    response = requests.post(url, json=data)
    return response.json()


# Main header
st.title('Time Series Data Visualization')

# Description
st.write('''
This application retrieves time series data from a specific API, transforms the data, 
and visualizes the original data and transformed data on a line plot.
''')

# Input field for the API token
vantage_token = st.text_input('Enter your Vantage token:', 'vntg_tkn_c3f76e12ca64a4e9fadbd9037bc740cc3fde8b9d')

if vantage_token == 'vntg_tkn_c3f76e12ca64a4e9fadbd9037bc740cc3fde8b9d':
    st.warning('Using syntetic data. Please enter your Vantage token. ')
    vantage_token = os.environ.get('VANTAGE_TOKEN')

# Header for GET request
st.header('Step 1: Data Retrieval')
with st.spinner('Fetching data from the API...'):
    url = "https://api.vantage.sh/v1/reports/3637/costs?grouping=account_id"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {vantage_token}"
    }
    data = fetch_data(url, headers)
st.success('Data fetched successfully!')

# Header for Data Transformation


# Header for Data Transformation
st.header('Step 2: Data Transformation')
with st.spinner('Transforming the data...'):
    # Data transformation logic...
    output_data = {"y": {}, "fh": 30, "level": [90], "finetune_steps": 1}
    for cost in data["costs"]:
        output_data["y"][cost["accrued_at"]] = float(cost["amount"])
st.success('Data transformed successfully!')    



# Header for POST request
st.header('Step 3: POST Request and Data Retrieval')
with st.spinner('Sending POST request and retrieving new data...'):
    post_url = os.environ.get('LTM1')
    new_data = post_request(post_url, output_data)
st.success('POST request sent and new data retrieved!')

# Header for visualization
st.header('Step 4: Data Visualization')
with st.spinner('Creating the plot...'):
    fig = create_figure('Current and Forecasted Cloud Costs', 'Date', 'Spend in USD')
    fig = add_trace(fig, list(output_data["y"].keys()), list(output_data["y"].values()), 'lines', 'Original Data')
    fig = add_trace(fig, new_data['timestamp'], new_data['value'], 'lines', 'Forecasted Data')
    fig = add_confidence_interval(fig, new_data['timestamp'], new_data['lo-90'], new_data['hi-90'])
    st.plotly_chart(fig)
st.success('Plot created successfully!')






# Data for Step 5: Visualization and Forecast for different services 
st.header('Step 5: Visualization and Forecast for a selected service')
with st.spinner('Fetching data for the selected service and creating the plot...'):
    # Fetching data for the selected service and creating the plot logic...
    url_service = "https://api.vantage.sh/v1/reports/3637/costs?grouping=service&page=3"
    data_service = fetch_data(url_service, headers)
st.success('Plot for the selected service created successfully!')




with st.spinner('Transforming the data for the selected service...'):
    # Data transformation
    service_data = defaultdict(list)
    for cost in data_service["costs"]:
        date = pd.to_datetime(cost["accrued_at"])
        service_data[cost["service"]].append((date, float(cost["amount"])))
st.success('Data transformed successfully!')




with st.spinner('Sending POST request and retrieving new data for the selected service...'):

    # Initialize Session State for st.session_state.selected_service if not already
    if 'st.session_state.selected_service' not in st.session_state:
        st.session_state.selected_service = 0  # default to the first service

    # Service selection
    st.session_state.selected_service = st.selectbox('Select a service:', list(service_data.keys()), st.session_state.selected_service)
    selected_dates, selected_values = zip(*service_data[st.session_state.selected_service])


    # Create figure for service data
    fig_service = create_figure(f'Costs and Forecast for {st.session_state.selected_service}', 'Date', 'Spend in USD', [0, max(selected_values)+10])
    fig_service = add_trace(fig_service, selected_dates, selected_values, 'lines', st.session_state.selected_service)

    # Prepare data for POST request
    output_data_service = {"y": {date.strftime('%Y-%m-%d'): value for date, value in zip(selected_dates, selected_values)}, "fh": 30, "level": [90]}
    new_data_service = post_request(post_url, output_data_service)

    # Extract forecast and confidence interval data
    new_dates_service = [pd.to_datetime(date) for date in new_data_service['timestamp']]
    new_values_service = new_data_service['value']
    new_lo_service = new_data_service['lo-90'] if 'lo-90' in new_data_service else [0]*len(new_values_service)
    new_hi_service = new_data_service['hi-90'] if 'hi-90' in new_data_service else [0]*len(new_values_service)

    fig_service = add_trace(fig_service, new_dates_service, new_values_service, 'lines', 'Forecasted Data')
    fig_service = add_confidence_interval(fig_service, new_dates_service, new_lo_service, new_hi_service)
    st.plotly_chart(fig_service)
st.success('Plot for the selected service created successfully!')


# Modify the add_confidence_interval function to mark points outside the confidence interval in red
def add_confidence_interval(fig, x, lower_bound, upper_bound):
    fig.add_trace(go.Scatter(
        x=x,
        y=lower_bound,
        fill=None,
        mode='lines',
        line_color='rgba(68, 68, 68, 0.2)',
        name='90% Confidence Interval'
    ))
    fig.add_trace(go.Scatter(
        x=x,
        y=upper_bound,
        fill='tonexty',  # Fill area between trace0 and trace1
        mode='lines',
        line_color='rgba(68, 68, 68, 0.2)',
        name='90% Confidence Interval'
    ))
    
    # Mark points above the confidence interval in red
    above_confidence_interval = [y > upper for y, upper in zip(list(output_data["y"].values())[-len(x):], upper_bound)]
    fig.add_trace(go.Scatter(
        x=[x_val for x_val, above in zip(x, above_confidence_interval) if above],
        y=[y_val for y_val, above in zip(list(output_data["y"].values())[-len(x):], above_confidence_interval) if above],
        mode='markers',
        marker=dict(color='red', size=10),
        name='Above Confidence Interval'
    ))
    return fig

# In-sample predictions
st.header('Step 6: In-sample Predictions')
with st.spinner('Making in-sample predictions and creating the plot...'):
    # Making in-sample predictions and creating the plot logic...
    # In-sample predictions
    insample_post_url = os.environ.get('INSAMPLE_LTM_URL')
    insample_data = post_request(insample_post_url, output_data)

    fig_insample = create_figure('Current and In-sample Predicted Cloud Costs', 'Date', 'Spend in USD')
    fig_insample = add_trace(fig_insample, list(output_data["y"].keys()), list(output_data["y"].values()), 'lines', 'Original Data')
    fig_insample = add_trace(fig_insample, insample_data['timestamp'], insample_data['value'], 'lines', 'In-sample Predictions')
    fig_insample = add_confidence_interval(fig_insample, insample_data['timestamp'], insample_data['lo-90'], insample_data['hi-90'])
    st.plotly_chart(fig_insample)
st.success('In-sample predictions plot created successfully!')


# In-sample predictions for the selected service
st.header(f'Step 7: In-sample Predictions and Actual Costs for {st.session_state.selected_service}')
with st.spinner(f'Making in-sample predictions for {st.session_state.selected_service} and creating the plot...'):
    # Making in-sample predictions for the selected service and creating the plot logic...
    insample_data_service = post_request(insample_post_url, output_data_service)

    # Create the figure for in-sample predictions
    fig_insample_service = create_figure(f'In-sample Predictions and Actual Costs for {st.session_state.selected_service}', 'Date', 'Spend in USD', [0, max(selected_values)+10])
    fig_insample_service = add_trace(fig_insample_service, selected_dates, selected_values, 'lines', f'Original Data ({st.session_state.selected_service})')
    fig_insample_service = add_trace(fig_insample_service, insample_data_service['timestamp'], insample_data_service['value'], 'lines', 'In-sample Predictions')

    # Add confidence interval if available in the data
    if 'lo-90' in insample_data_service and 'hi-90' in insample_data_service:
        fig_insample_service = add_confidence_interval(fig_insample_service, insample_data_service['timestamp'], insample_data_service['lo-90'], insample_data_service['hi-90'])
    st.plotly_chart(fig_insample_service)
st.success(f'In-sample predictions plot for {st.session_state.selected_service} created successfully!')