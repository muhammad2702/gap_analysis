import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import numpy as np
from matplotlib.dates import DateFormatter

API_KEY = 'whXh4oYmhSxw1SYOlu5HZnw6NPTJFOF5'


def fetch_data(ticker, start_date, end_date, multiplier=1, timespan='day'):
    url = f'https://api.polygon.io/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{start_date}/{end_date}'
    headers = {
        'Authorization': f'Bearer {API_KEY}'
    }
    params = {
        'adjusted': 'true',
        'sort': 'asc',
        'limit': 50000
    }
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        st.error(f"Error fetching data for {ticker}: {response.status_code}, {response.text}")
        return []
    
    data = response.json()
    if 'results' in data:
        st.info(f"Fetched {len(data['results'])} data points for {ticker}")
        return data['results']
    st.warning(f"No results found for {ticker}")
    return []

def get_historical_data(tickers, start_date, end_date):
    all_data = []
    for ticker in tickers:
        data = fetch_data(ticker, start_date, end_date)
        if data:
            for entry in data:
                all_data.append({
                    'ticker': ticker,
                    'date': datetime.fromtimestamp(entry['t'] / 1000).strftime('%Y-%m-%d'),
                    'open': entry['o'],
                    'high': entry['h'],
                    'low': entry['l'],
                    'close': entry['c'],
                    'volume': entry['v'],
                })
    df = pd.DataFrame(all_data)
    st.info(f"Total data points fetched: {len(df)}")
    return df

def calculate_gaps(stock_data, gap_percentage_threshold):
    gapped_stocks = set()
    grouped_data = stock_data.groupby('ticker')

    for ticker, group in grouped_data:
        group = group.sort_values('date')
        for i in range(1, len(group)):
            prev_close = group.iloc[i-1]['close']
            current_open = group.iloc[i]['open']
            if prev_close > 0:
                gap_percentage = ((current_open - prev_close) / prev_close) * 100
                if abs(gap_percentage) >= gap_percentage_threshold:
                    gapped_stocks.add(ticker)
                    break  # We only need to find one gap to include the stock

    return list(gapped_stocks)
def plot_stock_data(data, ticker):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    fig.suptitle(f"{ticker} Stock Analysis", fontsize=16)

    x = range(len(data))

    # Price chart
    ax1.plot(x, data['close'], label='Close Price')
    ax1.plot(x, data['open'], label='Open Price', alpha=0.7)
    ax1.fill_between(x, data['low'], data['high'], alpha=0.3, label='Price Range')
    ax1.set_ylabel("Price")
    ax1.legend()
    ax1.set_title("Stock Price")

    # Volume chart
    ax2.bar(x, data['volume'], label='Volume', alpha=0.7)
    ax2.set_xlabel("Trading Days")
    ax2.set_ylabel("Volume")
    ax2.set_title("Trading Volume")

    plt.tight_layout()
    st.pyplot(fig)

def plot_price_distribution(data):
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.histplot(data=data, x='close', kde=True, ax=ax)
    ax.set_title("Distribution of Closing Prices")
    ax.set_xlabel("Closing Price")
    ax.set_ylabel("Frequency")
    st.pyplot(fig)

def plot_correlation_heatmap(data):
    numeric_columns = ['open', 'high', 'low', 'close', 'volume']
    corr_matrix = data[numeric_columns].corr()

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', ax=ax)
    ax.set_title("Correlation Heatmap of Stock Data")
    st.pyplot(fig)

def plot_candlestick_chart(data):
    fig, ax = plt.subplots(figsize=(12, 6))

    # Candlestick chart
    width = 0.6
    width2 = 0.05

    up = data[data.close >= data.open]
    down = data[data.close < data.open]

    x_up = range(len(up))
    x_down = range(len(down))

    ax.bar(x_up, up.close - up.open, width, bottom=up.open, color='g')
    ax.bar(x_up, up.high - up.close, width2, bottom=up.close, color='g')
    ax.bar(x_up, up.low - up.open, width2, bottom=up.open, color='g')

    ax.bar(x_down, down.close - down.open, width, bottom=down.open, color='r')
    ax.bar(x_down, down.high - down.open, width2, bottom=down.open, color='r')
    ax.bar(x_down, down.low - down.close, width2, bottom=down.close, color='r')

    ax.set_title("Candlestick Chart")
    ax.set_xlabel("Trading Days")
    ax.set_ylabel("Price")
    plt.tight_layout()
    st.pyplot(fig)

def plot_gap_analysis(data, gap_percentage_threshold):
    data['prev_close'] = data['close'].shift(1)
    data['gap_percentage'] = (data['open'] - data['prev_close']) / data['prev_close'] * 100
    data['significant_gap'] = abs(data['gap_percentage']) >= gap_percentage_threshold

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.scatter(range(len(data)), data['gap_percentage'], c=data['significant_gap'], cmap='coolwarm', alpha=0.7)
    ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    ax.axhline(y=gap_percentage_threshold, color='red', linestyle='--', alpha=0.5)
    ax.axhline(y=-gap_percentage_threshold, color='red', linestyle='--', alpha=0.5)
    ax.set_title("Gap Analysis")
    ax.set_xlabel("Trading Days")
    ax.set_ylabel("Gap Percentage")
    plt.tight_layout()
    st.pyplot(fig)

def main():
    st.title("Stock Gap Analysis")

    # User inputs
    start_date = st.date_input("Start Date", value=pd.to_datetime("2022-01-01"))
    end_date = st.date_input("End Date", value=pd.to_datetime("2023-12-31"))
    gap_percentage_threshold = st.slider("Gap Percentage Threshold", 1.0, 20.0, 5.0, 0.1)
    tickers = st.text_input("Enter stock tickers (comma-separated)", "AAPL,GOOGL,TSLA,MSFT,AMZN").split(',')

    if st.button("Analyze Stocks"):
        historical_data = get_historical_data(tickers, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        
        gapped_stocks = calculate_gaps(historical_data, gap_percentage_threshold)
        st.success(f"Number of stocks with gaps >= {gap_percentage_threshold}%: {len(gapped_stocks)}")

        # Filter the dataset to include only the gapped stocks
        filtered_data = historical_data[historical_data['ticker'].isin(gapped_stocks)]

        # Save the full dataset for gapped stocks
        filtered_data.to_csv('gapped_stocks_full_data.csv', index=False)
        st.success(f"Full dataset for gapped stocks saved as 'gapped_stocks_full_data.csv'. Shape: {filtered_data.shape}")

        # Display gapped stocks
        st.subheader("Stocks with Significant Gaps:")
        st.write(", ".join(gapped_stocks))

        # Plot data for each gapped stock
        for ticker in gapped_stocks:
            st.subheader(f"{ticker} Stock Analysis")
            stock_data = filtered_data[filtered_data['ticker'] == ticker]
            
            plot_stock_data(stock_data, ticker)
            plot_price_distribution(stock_data)
            plot_correlation_heatmap(stock_data)
            plot_candlestick_chart(stock_data)
            plot_gap_analysis(stock_data, gap_percentage_threshold)

        # Display the dataframe
        st.subheader("Gapped Stocks Data")
        st.dataframe(filtered_data)

if __name__ == "__main__":
    main()