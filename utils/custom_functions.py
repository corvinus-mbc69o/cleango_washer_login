import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from utils.sql_functions import *
from unidecode import unidecode

from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)

def multi(x, y):
    number = x * y
    return number

def filter_dataframe(df):
    """
    Adds a UI on top of a dataframe to let viewers filter columns

    Args:
        df (pd.DataFrame): Original dataframe

    Returns:
        pd.DataFrame: Filtered dataframe
    """
    modify = st.checkbox("Add filters", value=True)

    if not modify:
        return df

    df = df.copy()

    # Try to convert datetimes into a standard format (datetime, no timezone)
    for col in df.columns:
        if is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass

        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    modification_container = st.container()

    with modification_container:
        to_filter_columns = st.multiselect(label="Filter dataframe on", options=df.columns)
        for column in to_filter_columns:
            left, right = st.columns((1, 20))
            # Treat columns with < 10 unique values as categorical
            if is_categorical_dtype(df[column]) or df[column].nunique() < 10:
                user_cat_input = right.multiselect(
                    f"Values for {column}",
                    df[column].unique(),
                    default=list(df[column].unique()),
                )
                df = df[df[column].isin(user_cat_input)]
            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100
                user_num_input = right.slider(
                    f"Values for {column}",
                    min_value=_min,
                    max_value=_max,
                    value=(_min, _max),
                    step=1.00,
                )
                df = df[df[column].between(*user_num_input)]
            elif is_datetime64_any_dtype(df[column]):
                user_date_input = right.date_input(
                    f"Values for {column}",
                    value=(
                        df[column].min(),
                        df[column].max(),
                    ),
                )
                if len(user_date_input) == 2:
                    user_date_input = tuple(map(pd.to_datetime, user_date_input))
                    start_date, end_date = user_date_input
                    df = df.loc[df[column].between(start_date, end_date)]
            else:
                user_text_input = right.text_input(
                    f"Substring or regex in {column}",
                )
                if user_text_input:
                    df = df[df[column].astype(str).str.contains(user_text_input)]
    
    df.insert(0, 'select', [False]* len(df.index))
    df_selected = st.experimental_data_editor(df, num_rows="fixed")

    return df_selected

def convert_df(df):
    return df.to_csv().encode('utf-8')


def format_data_washing_complex_data(df_input, afa = 1.27, add_historical_data = True):

    df_new = df_input.copy()

    try:
        df_new['b2b_b2c_limo'] = np.where(df_new['b2b_b2c_limo'] == 1, 'b2b', 'b2c')
    except:
        pass

    col_to_convert = ['wash_date', 'wash_date_day', 'wash_date_week', 'wash_date_month', 'wash_date_quarter']
    for col in col_to_convert:
        if col != 'wash_date':
            try:
                df_new[col] = pd.to_datetime(df_new[col])
            except:
                print(f'Could not convert {col} to datetime')
                pass
        else:
            try:
                df_new[col] = pd.to_datetime(df_new[col])
            except:
                print(f'Could not convert {col} to datetime')
                pass

    if add_historical_data:
        washes_hist = sql_query("SELECT * FROM cleango.bi_past_transaction_formated")
        col_to_convert_hist = ['wash_date', 'wash_date_day', 'wash_date_week', 'wash_date_month', 'wash_date_quarter']
        for col in col_to_convert_hist:
            if col != 'wash_date':
                try:
                    washes_hist[col] = pd.to_datetime(washes_hist[col]).dt.date
                except:
                    print(f'Could not convert {col} to datetime')
                    pass
            else:
                try:
                    washes_hist[col] = pd.to_datetime(washes_hist[col])
                except:
                    print(f'Could not convert {col} to datetime')
                    pass

        df_only_b2c = df_new[((df_new['b2b_b2c_limo'].isin(['b2c'])) | (df_new['wash_date'] >= '2023-03-19'))].copy()
        
        # concat washes_hist with df
        df_all = pd.concat([df_only_b2c, washes_hist], ignore_index=True)
        df = df_all.copy()
       
    else:
        df = df_new.copy()

    try:
        df['price'] = np.where(((df['b2b_b2c_limo'].isin(['Limo', 'b2b']) & (df['price'] <= 0 ))), df['base_wash_price'], df['price'])
    except:
        pass

    try:
        df['price'] = np.where((df['price']) < (df['original_price'] + 3500), df['original_price'], df['price'])
    except:
        pass

    try:
        df['price'] = np.where(df['b2b_b2c_limo'].isin(['b2c']), (df['price'] / afa), (df['price']))
    except:
        pass
    
    try:
        df['zip_code'] = df['zip_code'].astype(str)
    except:
        pass
    
    try:
        df['zip_code'] = np.where(df['zip_code'] == 'None',
                                df['street'].str.extract(r'(\d{4})', expand=False),
                                df['zip_code'].astype(str))
    except:
        pass

    try:
        df['district'] = df['zip_code'].apply(lambda x: x[1:3] if isinstance(x, str) and x.startswith('1') and len(x) == 4 else np.nan)
    except:
        pass

    try:
        df['margin'] = df['price'] - df['total_commision_price']
    except:
        pass

    try:
        df['profit_ratio'] = (df['margin'] / df['price'])
    except:
        pass

    try:
        # convert wash_date which is a datetime column to yyyy-Q1, yyyy-Q2, yyyy-Q3, yyyy-Q4
        df['wash_date_quarter'] = pd.to_datetime(df['wash_date_day']).dt.to_period('Q').dt.start_time
    except:
        print('Could not convert wash_date to quarter')
        pass

    return df

def calculate_active_users(df, window_days):
    # Make a copy of the input DataFrame to avoid modifying the original DataFrame
    df_calc = df.copy()

    # Convert the 'date' column to a datetime object
    df_calc['wash_date'] = pd.to_datetime(df_calc['wash_date'])

    # Set the index of the DataFrame to the 'date' column
    df_calc.set_index('wash_date', inplace=True)

    # Group the DataFrame by the user_id column and resample by day, counting the number of unique users per day
    active_users_series = df_calc.groupby('user_id').resample('D')['user_id'].nunique()

    # Create a new DataFrame from the resulting Series and fill any missing values with 0
    active_users_df = active_users_series.to_frame()

    # Rename the columns of the resulting DataFrame
    active_users_df.columns = ['active_users']

    # Shift the 'active_users' column up by one day to calculate the previous day's active users
    active_users_df['prev_day_active_users'] = active_users_df['active_users'].shift(1)

    # Reindex the DataFrame to include all days in the date range
    date_range = pd.date_range(df_calc.index.min(), df_calc.index.max(), freq='D').date
    active_users_df = active_users_df.reindex(date_range)

    # Fill any missing values with 0
    active_users_df.fillna(0, inplace=True)

    # Create a new DataFrame that contains the previous 'window_days' days of unique users for each day in the input DataFrame
    active_users_window = pd.DataFrame()
    for i in range(window_days):
        active_users_window[f'prev_{i+1}_day_active_users'] = active_users_df['prev_day_active_users'].rolling(i+1).sum().shift(-i-1)
    active_users_window.dropna(inplace=True)

    # Reset the index of the resulting DataFrame and rename the column to 'date'
    active_users_window.reset_index(inplace=True)
    active_users_window.rename(columns={'index': 'date'}, inplace=True)

    return active_users_window

def calculate_wash_number(df, window_days):
    # Convert the date column to a datetime object and sort the dataframe by date
    df_calc = df.copy()
    df_calc['date'] = pd.to_datetime(df_calc['wash_date_day'])
    df_calc = df_calc.sort_values('date')

    # Calculate unique user counts for each date and create a time series
    wash_counts = df_calc.groupby(pd.Grouper(key='date', freq='D'))['id'].nunique()
    wash_counts_ts = wash_counts.asfreq('D', fill_value=0)

    # Calculate the rolling window of unique user IDs for each date
    rolling_active_washes = wash_counts_ts.rolling(f'{window_days}D').sum()

    # Reset the index of the resulting dataframe and rename the column
    active_washes_df = pd.DataFrame({'date': rolling_active_washes.index, 'active_washes': rolling_active_washes.values})

    return active_washes_df

def add_logo(logo_path):
    with open(logo_path, "rb") as f:
        image_bytes = f.read()
        encoded_image = base64.b64encode(image_bytes).decode()

    st.markdown(
        f"""
        <style>
            [data-testid="stSidebarNav"] {{
                background-image: url('data:image/png;base64,{encoded_image}');
                background-repeat: no-repeat;
                padding-top: 0px;
                background-position: center top;
                background-size: contain;
                background-size: 250px;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def create_user_purchase_df(df):
    # create a copy of the input dataframe
    df_copy = df.copy()
    
    # group transactions by user_id and date_of_purchase
    grouped = df_copy.groupby(['user_id', 'wash_date_day'])

    # create an empty dictionary to store the dataframes for each user
    user_dfs = {}

    # loop through each group of transactions for each user
    for (user_id, wash_date_day), group in grouped:

        # create a new dataframe for this user and date
        user_df = pd.DataFrame(columns=['date', 'user_id', 'transaction_count', 'previous_transaction_date', 'next_transaction_date'])

        # fill in the values for each column using the transactions data for that user
        user_df.loc[0, 'date'] = wash_date_day
        user_df.loc[0, 'user_id'] = user_id
        user_df.loc[0, 'transaction_count'] = len(group)

        # count the number of purchases until that day for this user
        transaction_count = df_copy[(df_copy['user_id'] == user_id) & (df_copy['wash_date_day'] <= wash_date_day)].shape[0]
        user_df.loc[0, 'transaction_count'] = transaction_count

        # get the previous and next transaction dates for this user
        previous_transaction_date = df_copy[(df_copy['user_id'] == user_id) & (df_copy['wash_date_day'] < wash_date_day)]['wash_date_day'].max()
        next_transaction_date = df_copy[(df_copy['user_id'] == user_id) & (df_copy['wash_date_day'] > wash_date_day)]['wash_date_day'].min()

        # fill in the values for prev_purchase_date and next_transaction_date
        if pd.notnull(previous_transaction_date):
            user_df.loc[0, 'previous_transaction_date'] = previous_transaction_date
        if pd.notnull(next_transaction_date):
            user_df.loc[0, 'next_transaction_date'] = next_transaction_date

        # add the new dataframe to the dictionary using the user_id as the key
        if user_id in user_dfs:
            user_dfs[user_id] = pd.concat([user_dfs[user_id], user_df], ignore_index=True)
        else:
            user_dfs[user_id] = user_df

    # concatenate all the dataframes in the dictionary into one big dataframe
    result = pd.concat(user_dfs.values(), ignore_index=True)
    result['days_since_last_purchase'] = (pd.to_datetime(result['date']) - pd.to_datetime(result['previous_transaction_date'])).dt.days
    result['days_until_next_purchase'] = (pd.to_datetime(result['next_transaction_date']) - pd.to_datetime(result['date'])).dt.days
    # convert a date column to datetime format
    result['date'] = pd.to_datetime(result['date'])
    return result






