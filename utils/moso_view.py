import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from utils.custom_functions import *
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from PIL import Image
from datetime import datetime

def add_picture_to_streamlit(image_path, caption = None):
    image = Image.open(image_path)
    st.image(image, caption=caption)

    hide_img_fs = '''
        <style> 
            button[title="View fullscreen"]{
                visibility: hidden;}
        </style>
    '''

    st.markdown(hide_img_fs, unsafe_allow_html=True)

def send_email(recipient_address, subject, body):
    # create a message object
    msg = MIMEMultipart()
    msg['From'] = st.secrets['email']['smtp_username']
    msg['To'] = recipient_address
    msg['Subject'] = subject

    # add some text to the email body allow use html
    msg.attach(MIMEText(body, 'html'))
    #msg.attach(MIMEText(body, 'plain'))

    # create a SMTP client session
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    smtp_username = st.secrets['email']['smtp_username']
    smtp_password = st.secrets['email']['smtp_password']
    with smtplib.SMTP(smtp_server, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_username, smtp_password)
        smtp.send_message(msg)

def create_admin_view(authenticator, username, name, config):
    
    st.sidebar.markdown("Üdvözöllek, " + name + "!")
    
    washes_sql_query = "SELECT * FROM cleango.valid_washes where wash_date is not NULL;"

    if 'valid_washes' not in st.session_state:
        with st.spinner('Please wait, Downloading Data from SQL (aprox. 2 mins)'):
            valid_washes = sql_query(washes_sql_query)
            st.session_state['valid_washes'] = valid_washes
    else:
        valid_washes = st.session_state.valid_washes

    st.markdown("## Mosások")
    valid_washes = format_data_washing_complex_data(valid_washes)
    cols_to_filter = ['washer_name', 'wash_date', 'wash_date_day', 'b2b_b2c_limo', 'mosas_tipus', 'car_category', 'brand_name', 'make_name' , 'plate_number', 'base_wash_commission', 'count_extra', 'extra_commision_price', 'total_commision_price', 'user_id', 'id']
    valid_washes = valid_washes[cols_to_filter]

    valid_washes['wash_date'] = pd.to_datetime(valid_washes['wash_date'])
    valid_washes['wash_date_day'] = pd.to_datetime(valid_washes['wash_date_day'])
    # convert wash_date_day to only date
    valid_washes['wash_date_day'] = valid_washes['wash_date_day'].dt.date


    with st.form(key='filter_washers'):
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            # create a date filter called "date_from"
            date_from = st.date_input('Start Date', value=pd.to_datetime('2022-01-01'))
        with col2:
            # create a date filter called "date_to" set value to today
            date_to = st.date_input('End Date', value=pd.to_datetime(datetime.today().strftime('%Y-%m-%d')))
        with col3:
            # create a filter with washer_names multislect
            washer_names = valid_washes['washer_name'].unique()
            # add all option to the begining of the list
            washer_names = np.insert(washer_names, 0, 'All')
            washer_names = st.multiselect('Washer Name', washer_names, default='All')
        
        # create a button
        submitted = st.form_submit_button('Filter')
    
    if submitted:
        # filter the data
        if 'All' not in washer_names:
            valid_washes = valid_washes[valid_washes['washer_name'].isin(washer_names)]
        valid_washes = valid_washes[(valid_washes['wash_date'] >= pd.to_datetime(date_from)) & (valid_washes['wash_date'] <= pd.to_datetime(date_to))]

        st.dataframe(valid_washes)
        # total number of washes
        st.markdown("Összes mosás száma: {}".format(valid_washes.shape[0]))
        # total commission
        st.markdown("Összes jutalék: {} Ft".format(valid_washes['total_commision_price'].sum()))
        st.download_button(label="Download data as CSV",
                        data=convert_df(valid_washes),
                        file_name='valid_washes.csv', mime='text/csv')

def create_washer_view(authenticator, username, name, config):

    col1, col2 = st.columns([8, 1])
    with col1:
        st.markdown("Üdvözöllek, " + name + "!")
    with col2:
        authenticator.logout('Kijelentkezes', 'main')

    with st.form(key='filter_washers'):
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            # create a date filter called "date_from"
            date_from = st.date_input('Start Date', value=pd.to_datetime('2023-01-01'))
        with col2:
            # create a date filter called "date_to"
            date_to = st.date_input('End Date', value=pd.to_datetime(datetime.today().strftime('%Y-%m-%d')))
        
        # create a button
        submitted = st.form_submit_button('Filter')
    
    if submitted:
        washes_sql_query = "SELECT * FROM cleango.valid_washes where wash_date is not NULL;"

        if 'valid_washes' not in st.session_state:
            with st.spinner('Please wait, Downloading Data from SQL (aprox. 2 mins)'):
                valid_washes = sql_query(washes_sql_query)
                st.session_state['valid_washes'] = valid_washes
        else:
            valid_washes = st.session_state.valid_washes

        st.markdown("## Mosások")
        valid_washes = format_data_washing_complex_data(valid_washes)
        cols_to_filter = ['washer_name', 'wash_date', 'wash_date_day', 'b2b_b2c_limo', 'mosas_tipus', 'car_category', 'brand_name', 'make_name' , 'plate_number', 'base_wash_commission', 'count_extra', 'extra_commision_price', 'total_commision_price', 'user_id', 'id']
        valid_washes = valid_washes[cols_to_filter]

        valid_washes['wash_date'] = pd.to_datetime(valid_washes['wash_date'])
        valid_washes['wash_date_day'] = pd.to_datetime(valid_washes['wash_date_day'])
        # convert wash_date_day to only date
        valid_washes['wash_date_day'] = valid_washes['wash_date_day'].dt.date

        valid_washes = valid_washes[valid_washes['washer_name'].isin([config['credentials']['usernames'][username]['moso_db_name']])]
        valid_washes = valid_washes[(valid_washes['wash_date'] >= pd.to_datetime(date_from)) & (valid_washes['wash_date'] <= pd.to_datetime(date_to))]
        valid_washes = valid_washes.reset_index(drop=True)

        st.dataframe(valid_washes)

        col1, col2, col3, col4 = st.columns([2, 2, 5, 1])
        with col1:
            # total number of washes
            st.markdown("Összes mosás száma: {}".format(valid_washes.shape[0]))
        
        with col2:
            # total commission
            st.markdown("Összes jutalék: {} Ft".format(round(valid_washes['total_commision_price'].sum())))

        with col1:
            st.download_button(label="Download data",
                            data=convert_df(valid_washes),
                            file_name='valid_washes.csv', mime='text/csv')
        