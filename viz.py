import requests
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import seaborn as sns
import matplotlib.pyplot as plt
import io

API_KEY = 'wERjETOkx4U_xE6fyCA6z9wODWUarDxa'  # Replace with your actual Polygon.io API key

def get_stock_tickers(market, type, active, sort, order, limit):
    url = f"https://api.polygon.io/v3/reference/tickers?market={market}&type={type}&active={active}&sort={sort}&order={order}&limit={limit}&apiKey={API_KEY}"
    tickers = []
    response = requests.get(url).json()
    
    if 'results' in response:
        tickers.extend([ticker['ticker'] for ticker in response['results']])
        st.info(f"Found {len(tickers)} tickers.")
    else:
        st.warning("No results found or unexpected response structure")
    
    return tickers

def get_stock_data(symbol, date, adjusted):
    url = f'https://api.polygon.io/v1/open-close/{symbol}/{date}?adjusted={adjusted}&apiKey={API_KEY}'
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        #st.warning(f"Failed to fetch data for {symbol} on {date}. Status Code: {response.status_code}")
        return None

def get_previous_dates(num_days):
    today = datetime.now() - timedelta(days=1)
    dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(0, num_days)]
    return dates

def plot_gap_distribution(df, min_gap):
    plt.figure(figsize=(10, 6))
    sns.histplot(df[df['gap_percentage'] >= min_gap]['gap_percentage'], kde=True)
    plt.title(f'Distribution of Gap Up Percentages (>= {min_gap}%)')
    plt.xlabel('Gap Up Percentage')
    plt.ylabel('Frequency')
    st.pyplot(plt)

def plot_top_gappers(df, min_gap):
    top_10 = df[df['gap_percentage'] >= min_gap].nlargest(10, 'gap_percentage')
    plt.figure(figsize=(12, 6))
    sns.barplot(x='symbol', y='gap_percentage', data=top_10)
    plt.title(f'Top 10 Gappers (>= {min_gap}%)')
    plt.xlabel('Symbol')
    plt.ylabel('Gap Up Percentage')
    plt.xticks(rotation=45)
    st.pyplot(plt)

def main():
    st.title("Stock Gap Up Analysis")

    # User inputs
    num_days = st.number_input("Enter the number of days to retrieve data (up to today)", min_value=1, max_value=30000, value=5)
    use_custom_tickers = st.checkbox("Use custom list of tickers")
    
    if use_custom_tickers:
        custom_tickers = st.text_input("Enter comma-separated list of tickers").upper().split(',')
        tickers = [ticker.strip() for ticker in custom_tickers if ticker.strip()]
    else:
        market = st.selectbox("Select market", ["stocks", "crypto", "fx"])
        type = st.selectbox("Select type", ["CS", "ADRC", "ADRP", "ADRR", "ETF", "FUND", "SP"])
        active = st.checkbox("Active stocks only", value=True)
        sort = st.selectbox("Sort by", ["ticker", "name", "market", "locale", "primary_exchange", "type", "currency_name", "cik"])
        order = st.selectbox("Order", ["asc", "desc"])
        limit = st.number_input("Limit", min_value=1, max_value=10000, value=100)
    
    adjusted = st.checkbox("Adjusted prices", value=True)
    gap_percentage = st.number_input("Minimum gap up percentage for separate sheet", min_value=0.0, max_value=100.0, value=5.0)
    vis_gap_percentage = st.number_input("Minimum gap up percentage for visualizations", min_value=0.0, max_value=100.0, value=5.0)

    if st.button("Analyze"):
        dates_to_check = get_previous_dates(num_days)
        
        if not use_custom_tickers:
            tickers = get_stock_tickers(market, type, str(active).lower(), sort, order, limit)
        
        if not tickers:
            st.error("No tickers to analyze. Please check your inputs.")
            return

        all_results = []
        high_gap_results = []

        progress_bar = st.progress(0)
        total_iterations = len(tickers) * len(dates_to_check)
        current_iteration = 0

        for symbol in tickers:
            for date in dates_to_check:
                today_data = get_stock_data(symbol, date, str(adjusted).lower())
                if today_data and 'preMarket' in today_data:
                    previous_pre_market_price = today_data['preMarket']
                    
                    next_date = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
                    next_day_data = get_stock_data(symbol, next_date, str(adjusted).lower())
                    if next_day_data and 'open' in next_day_data:
                        next_day_open_price = next_day_data['open']
                        
                        gap_up = ((next_day_open_price - previous_pre_market_price) / previous_pre_market_price) * 100
                        
                        result = {
                            'symbol': symbol,
                            'date': date,
                            'previous_pre_market_price': previous_pre_market_price,
                            'next_day_open_price': next_day_open_price,
                            'gap_percentage': gap_up,
                            'open': next_day_data.get('open'),
                            'high': next_day_data.get('high'),
                            'low': next_day_data.get('low'),
                            'close': next_day_data.get('close'),
                            'volume': next_day_data.get('volume')
                        }
                        
                        all_results.append(result)
                        
                        if gap_up >= gap_percentage:
                            high_gap_results.append(result)
                
                current_iteration += 1
                progress_bar.progress(current_iteration / total_iterations)

        if all_results:
            all_df = pd.DataFrame(all_results)
            high_gap_df = pd.DataFrame(high_gap_results)

            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                all_df.to_excel(writer, sheet_name='All Gapped Up Stocks', index=False)
                if not high_gap_df.empty:
                    high_gap_df.to_excel(writer, sheet_name=f'Gap Up {gap_percentage}%+', index=False)

            excel_buffer.seek(0)
            st.success(f'Analysis complete with {len(all_results)} entries.')
            st.download_button(
                label="Download Excel file",
                data=excel_buffer,
                file_name='gapped_up_stocks.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

            # Visualizations
            st.subheader("Visualizations")
            plot_gap_distribution(all_df, vis_gap_percentage)
            plot_top_gappers(all_df, vis_gap_percentage)

            # Display Excel file contents
            st.subheader("Excel File Contents")
            st.write("All Gapped Up Stocks:")
            st.dataframe(all_df)
            if not high_gap_df.empty:
                st.write(f"Gap Up {gap_percentage}%+:")
                st.dataframe(high_gap_df)

        else:
            st.warning('No stocks found that gapped up.')

if __name__ == '__main__':
    main()
