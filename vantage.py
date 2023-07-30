import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict
import time
import os
import openai
import datetime


openai.api_key = os.environ.get('OPENAI_TOKEN_EDU')

################################################
# 0️⃣ Step 0: Define helper functions
################################################

def format_custom_date(dates_list):
    formatted_dates = []
    for date_str in dates_list:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        day_of_week = date_obj.strftime("%A")
        day = date_obj.strftime("%d")
        day_suffix = "th" if 11 <= int(day) <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(int(day) % 10, "th")
        month = date_obj.strftime("%B")
        year = date_obj.strftime("%Y")
        formatted_date = f"{day_of_week} {day}{day_suffix} of {month} {year}"
        formatted_dates.append(formatted_date)
    return formatted_dates


def explain_anomalies(anomaly_dates):
    response= openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an expert in anomaly detection for time series. In particular you help people understand pontential explanations for anomalies in cloud usage. The user gives you dates on which they saw spikes and you analyze the dates and explain what could be special about those dates. For example, if they are holidays or close to holidays, quarted ends, month ends, weekends, etc. You always answer in a short parragprah and are concise."},
            {"role": "user", "content": f"Here is the list of dates where I detected spikes in usage in my cloud services:  {format_custom_date(anomaly_dates)}"}
        ]
    )
    return response.choices[0].message.content



if 'stage' not in st.session_state:
    st.session_state.stage = 0

def set_state(i):
    st.session_state.stage = i

# Fetching data with caching
@st.cache_data(ttl=1000)
def fetch_data(url, headers):
    response = requests.get(url, headers=headers)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        st.warning(f'HTTP error occurred: {err}. \n Please enter a valid request.')
        st.stop()
    # Print status code and message
    return response.json()

@st.cache_data(ttl=1000)
def fetch_reports(url, headers):
    response = requests.get(url, headers=headers)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        st.warning(f'HTTP error occurred: {err}. \n Please enter a valid request.')
        st.stop()
    # Print status code and message
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


# Modify the add_confidence_interval function to mark points outside the confidence interval in red
def add_confidence_interval_anomalies(fig, output_data, x, lower_bound, upper_bound):
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
    y_vals = list(output_data["y"].values())[-len(upper_bound):]
    above_confidence_interval = [y > upper for y, upper in zip(y_vals, upper_bound)]
    fig.add_trace(go.Scatter(
        x=[x_val for x_val, above in zip(x[-len(upper_bound):], above_confidence_interval) if above],
        y=[y_val for y_val, above in zip(y_vals, above_confidence_interval) if above],
        mode='markers',
        marker=dict(color='red', size=10),
        name='Above Confidence Interval'
    ))
    return fig

def create_exogenous_variable(series, horizon):
    # Convert the input series to a pandas DataFrame
    df = pd.DataFrame(list(series["y"].items()), columns=['date', 'value'])
    # Convert the 'date' column to pandas datetime format
    df['date'] = pd.to_datetime(df['date'])
    # Get the start and end date from the series
    start_date = df['date'].min()
    end_date = df['date'].max()
    # Generate a list of dates for the entire period, including the horizon
    date_range = pd.date_range(start=start_date, periods=len(df) + horizon)
    # Create the exogenous variable dictionary with initial values as 0
    exogenous_variable = {date.strftime('%Y-%m-%d'): [0] for date in date_range}
    # Set the value to 1 for the initial date of each month in the exogenous variable
    exogenous_variable[start_date.strftime('%Y-%m-%d')][0] = 1
    for i in range(1, len(date_range)):
        if date_range[i].day == 1:
            exogenous_variable[date_range[i].strftime('%Y-%m-%d')][0] = 1
    return exogenous_variable

@st.cache_data(ttl=15)
def time_gpt(url, data, add_ex=True):
    if add_ex:
        x_dates = create_exogenous_variable(data, data["fh"])
        data["x"] = x_dates
    else:
        data["x"] = {}
    response = requests.post(url, json=data, headers={"authorization": f"Bearer {os.environ.get('NIXTLA_TOKEN')}"})
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        st.warning(f'HTTP error occurred: {err}')
        return None
    return response.json()

if 'processed' not in st.session_state:
    st.session_state.processed = {}

st.title('Forecasting Cloud Costs with Vantage and Nixtla')
st.write('''
👋 Welcome to Vantage and Nixtla's forecasting app, your one-stop 🎯 solution for predicting ☁️ cloud costs with precision. Seamlessly integrated with Vantage's cloud cost transparency 💰 and Nixtla's advanced 📊 forecasting capabilities, this app takes the guesswork out of cloud budgeting. 🚀
''')
st.subheader('Get your cloud costs with Vantage')

vantage_token = st.text_input('Token:', 'vntg_tkn_c3f76e12ca64a4e9fadbd9037bc740cc3fde8b9d')

if vantage_token == 'vntg_tkn_c3f76e12ca64a4e9fadbd9037bc740cc3fde8b9d':
    st.warning('Using syntetic data. Please enter your Vantage token. ')
    vantage_token = os.environ.get('VANTAGE_TOKEN')





################################################
# 2️⃣ Step: Get and Forecast cost report grouped by account_id
################################################

'''  **See available reports:** '''

# Create a button for fetching reports
if st.button('Get Reports'):
    # Fetching reports
    # Define the API endpoint and headers
    url = "https://api.vantage.sh/v1/reports"
    headers = {
            "accept": "application/json",
            "authorization": f"Bearer {vantage_token}"
        }
    
    # Show spinner while fetching data
    with st.spinner('Fetching reports...'):
        # Call the previously defined function 'fetch_data'
        data = fetch_reports(url, headers)


    # Extract the 'reports' list from the JSON response
    reports = data['reports']
    st.session_state.processed['reports'] = reports

    # Convert the 'reports' list into a DataFrame
    df = pd.DataFrame(reports)

    # Select only the 'id', 'title', and 'workspace' columns from the DataFrame
    df = df[['id', 'title', 'workspace']]

    # Display the DataFrame as a table in Streamlit
    st.table(df)


'''
**Enter Report ID to get cost details:**
'''



# User input for report ID
report_id = st.text_input('Enter Report ID:', '3637')
if st.button('Get Costs'):
    # Header for GET request
    with st.spinner('Fetching data from the API...'):
        url = f"https://api.vantage.sh/v1/reports/{report_id}/costs?grouping=account_id&?start_date=2023-03-01"
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {vantage_token}"
        }
        data = fetch_data(url, headers)
        # Transform the data into a dictionary for future forecasting
        output_data = {"y": {}, "fh": 30, "level": [90], "finetune_steps": 2}
        for cost in data["costs"]:
            output_data["y"][cost["accrued_at"]] = float(cost["amount"])
        
        st.session_state['output_data'] = output_data
        st.success('Costs fetched successfully!')
        st.session_state.processed['output_data'] = output_data


    # Step 2# Request forecast from time GPT
    with st.spinner('🔮 Forecasting... 💾 Hang tight! 🚀'):
        post_url = os.environ.get('LTM1')
        new_data = time_gpt(post_url, output_data)
        if new_data:
            st.success('✅ Forecasting completed successfully!')
        else:
            st.stop()

    # Header for visualization
    with st.spinner('👩‍💻 Plotting'):
        fig = create_figure('Current and Forecasted Cloud Costs', 'Date', 'Spend in USD')
        fig = add_trace(fig, list(output_data["y"].keys()), list(output_data["y"].values()), 'lines', 'Original Data')
        fig = add_trace(fig, new_data['timestamp'], new_data['value'], 'lines', 'Forecasted Data')
        fig = add_confidence_interval(fig, new_data['timestamp'], new_data['lo-90'], new_data['hi-90'])
        st.plotly_chart(fig)

################################################
# 3 Step: Detect Anomalies for the selected report grouped by account_id
################################################

    # In-sample predictions
    st.header('Anomaly detection with Vantage and Nixtla')
    st.write("""
    "This app leverages the power of Vantage's robust data analytics platform 💼 and Nixtla's cutting-edge forecasting techniques 📈 to identify outliers in your data in real-time. 🔍
    You can view available reports 📋, input specific report IDs 🔢 for more detailed insights, and even fetch cost details 💰 on demand. So go ahead, explore your data 🔎, and let's unveil the hidden anomalies together! 😎"
    """)
    with st.spinner('🔎 Detecting anomalies...'):
        # Making in-sample predictions and creating the plot logic...
        # In-sample predictions
        insample_post_url = os.environ.get('INSAMPLE_LTM_URL')
        insample_data = time_gpt(insample_post_url, output_data, add_ex=False)
        fig_insample = create_figure('Current and In-sample Predicted Cloud Costs', 'Date', 'Spend in USD')
        fig_insample = add_trace(fig_insample, list(output_data["y"].keys()), list(output_data["y"].values()), 'lines', 'Original Data')
        fig_insample = add_trace(fig_insample, insample_data['timestamp'], insample_data['value'], 'lines', 'In-sample Predictions')
        fig_insample = add_confidence_interval_anomalies(fig_insample, output_data, insample_data['timestamp'], insample_data['lo-90'], insample_data['hi-90'])
        st.plotly_chart(fig_insample)

        #st.write(output_data)
        y = list(output_data["y"].values())[-len(insample_data['hi-90']):]
        y_keys = list(output_data["y"].keys())[-len(insample_data['hi-90']):]
        anomalies_list = [y > upper for y, upper in zip(y, insample_data['hi-90'])]

        anomaly_dates = [y_keys[i] for i, (y, upper) in enumerate(zip(y, insample_data['hi-90'])) if y > upper]


        #st.write(anomaly_dates)
        #st.write(anomalies_list)
    with st.spinner('🔎 Explaining anomalies...'):    
        st.write(explain_anomalies(anomaly_dates))


################################################
# 4 Step: Get and Forecast cost report grouped by service or provider
################################################


st.header('Select a specific grouping criteria to forecast its future costs')

start_date = st.text_input('Start date', value='2023-03-01')

grouping = st.text_input('Grouping', value='provider')

report_id = st.text_input('Report ID', value= '')


if report_id == '':
    st.warning('Please enter a valid report ID')
else:


    with st.spinner('Fetching data and creating the plot...'):
        # Fetching data for the selected service and creating the plot logic...
        url_service = f"https://api.vantage.sh/v1/reports/{report_id}/costs?grouping={grouping}&?start_date={start_date}"
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {vantage_token}"
        }
        data_service = fetch_data(url_service, headers)
        st.session_state.processed['data_service'] = data_service

    with st.spinner('Transforming the data for the selected service...'):
        # Data transformation
        if grouping == 'provider':
            service_data = defaultdict(list)
            for cost in data_service["costs"]:
                date = pd.to_datetime(cost["accrued_at"])
                service_data[cost["provider"]].append((date, float(cost["amount"])))
        elif grouping == 'service':
            service_data = defaultdict(list)
            for cost in data_service["costs"]:
                date = pd.to_datetime(cost["accrued_at"])
                service_data[cost["service"]].append((date, float(cost["amount"])))
        elif grouping == 'account_id':
            service_data = defaultdict(list)
            for cost in data_service["costs"]:
                date = pd.to_datetime(cost["accrued_at"])
                service_data[cost["account_id"]].append((date, float(cost["amount"])))
        else:
            #Raise error becuase groupig is not supported
            st.error('Grouping is not supported. Please select a either service, provider or account_id')



    with st.spinner('🔮 Forecasting... 💾 Hang tight! 🚀'):

        # Initialize Session State for st.session_state.selected_service if not already
        if 'st.session_state.selected_service' not in st.session_state:
            st.session_state.selected_service = 0  # default to the first service

        # Service selection
        st.session_state.selected_service = st.selectbox('Select a service or provider:', list(service_data.keys()), st.session_state.selected_service)
        selected_dates, selected_values = zip(*service_data[st.session_state.selected_service])


        # Create figure for service data
        fig_service = create_figure(f'Costs and Forecast for {st.session_state.selected_service}', 'Date', 'Spend in USD', [0, max(selected_values)+10])
        fig_service = add_trace(fig_service, selected_dates, selected_values, 'lines', st.session_state.selected_service)

        # Prepare data for POST request
        output_data_service = {"y": {date.strftime('%Y-%m-%d'): value for date, value in zip(selected_dates, selected_values)}, "fh": 30, "level": [90], 'finetune_steps': 2}
        post_url = os.environ.get('LTM1')
        new_data_service = time_gpt(post_url, output_data_service)

        # Extract forecast and confidence interval data
        new_dates_service = [pd.to_datetime(date) for date in new_data_service['timestamp']]
        new_values_service = new_data_service['value']
        new_lo_service = new_data_service['lo-90'] if 'lo-90' in new_data_service else [0]*len(new_values_service)
        new_hi_service = new_data_service['hi-90'] if 'hi-90' in new_data_service else [0]*len(new_values_service)

        fig_service = add_trace(fig_service, new_dates_service, new_values_service, 'lines', 'Forecasted Data')
        fig_service = add_confidence_interval(fig_service, new_dates_service, new_lo_service, new_hi_service)
        st.plotly_chart(fig_service)



    # In-sample predictions for the selected service



    output_data = st.session_state.processed['output_data']



    st.header(f'Anomaly detections for {st.session_state.selected_service}')
    with st.spinner(f'Making in-sample predictions for {st.session_state.selected_service} and creating the plot...'):
        # Making in-sample predictions for the selected service and creating the plot logic...
        insample_post_url = os.environ.get('INSAMPLE_LTM_URL')
        insample_data_service = time_gpt(insample_post_url, output_data_service, add_ex=False)

        # Create the figure for in-sample predictions
        fig_insample_service = create_figure(f'In-sample Predictions and Actual Costs for {st.session_state.selected_service}', 'Date', 'Spend in USD', [0, max(selected_values)+10])
        fig_insample_service = add_trace(fig_insample_service, selected_dates, selected_values, 'lines', f'Original Data ({st.session_state.selected_service})')
        fig_insample_service = add_trace(fig_insample_service, insample_data_service['timestamp'], insample_data_service['value'], 'lines', 'In-sample Predictions')

        # Add confidence interval if available in the data
        #if 'lo-90' in insample_data_service and 'hi-90' in insample_data_service:
        fig_insample_service = add_confidence_interval_anomalies(fig_insample_service, output_data_service, insample_data_service['timestamp'], insample_data_service['lo-90'], insample_data_service['hi-90'])
        st.plotly_chart(fig_insample_service)



