# Vantage+TimeGPT - Forecasting Cloud Costs ☁️⏲️

Welcome 🙏 to the Vantage+TimeGPT code repository. This project offers a powerful 🔥 tool to predict cloud costs 💰 and detect anomalies with Vantage and Nixtla, leveraging the power of Nixtla's TimeGPT and OpenAI's GPT-4 to provide explanations 💡.

## Prerequisites 📚

Before running 🏃 the project, make sure you have installed the following:

```bash
pip install -r requirements.txt
```

## Configuration 🔧

In order to run this project, you need to set several environment variables. These variables are:

- `OPENAI_TOKEN`: Your OpenAI API key 🔑
- `VANTAGE_TOKEN`: Your Vantage API key 🔑
- `TIMEGPT_TOKEN`: Your Nixtla API key 🔑

## Clone the Repository 🔄

To clone the repository, run the following command:

```bash
git clone https://github.com/Nixtla/vantage.git
```

## Running the Project 🏃‍♀️

After setting up the environment variables and installing the dependencies, you can run the project using the following command:

```bash
streamlit run streamlit.py
```

This command will start a local server, and you can access the web application by navigating to the provided URL (usually `http://localhost:8501`) in your web browser 🌐.

## How to Use 🛠️

1. When you open the application, enter your Vantage token to fetch cloud cost data. If you don't change the default Vantage token, the app will use synthetic data.
2. You can view available cost reports by clicking the 'Get reports' button. 
3. To fetch historical data for a specific report, enter its ID and click 'Fetch historic data'.
4. Click 'Forecast costs and Detect anomalies' to request a forecast and detect any cost anomalies.
5. You can also forecast costs for a specific grouping criteria. Enter the start date, grouping criteria, and report ID in the relevant fields and click 'Fetch data and create the plot'.
6. The application will display the forecast and any detected anomalies for the selected report.

Please note that some of the operations may take some time due to the complex computations involved. Patience is appreciated. Enjoy the magic of forecasting! ✨

## Contributing 👥

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License 📃

Please see the [LICENSE](LICENSE.md) file for details.

## Contact 📞

If you have any questions, feel free to reach out to us. We'd be happy to help!