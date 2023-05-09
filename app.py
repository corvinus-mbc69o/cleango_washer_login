import streamlit as st
import pandas as pd
import numpy as np

import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from utils.custom_functions import *
from utils.moso_view import *
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

#set streamlit page name
st.set_page_config(page_title='CleanGo - B2B Rendelő felület', page_icon='data/cleango-logo-small.png', layout='wide')

col1, col2 = st.columns([2, 8])
with col1:
    add_picture_to_streamlit('data/cleango-logo-small.png', caption = None)

st.title("CleanGo - Mosó Elszámolás")

with open('.streamlit/washer_users_data.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

col1, col2 = st.columns([6, 3])

with col1:
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config['preauthorized'])
    name, authentication_status, username = authenticator.login('Login', 'main')
with col2:
    if authentication_status == False or authentication_status == None:
        add_picture_to_streamlit('data/mosas.png', caption = None)
    
if authentication_status:
    if username == 'admin':
        col1, col2 = st.columns([8, 1])
        with col1:
            st.markdown('Adminként vagy bejelentkezve')
        with col2:
            authenticator.logout('Kijelentkezés', 'main')
        create_admin_view(authenticator=authenticator, username=username, name=name, config=config)
    else:
        create_washer_view(authenticator=authenticator, username=username, name=name, config=config)
elif authentication_status == False:
    with col1:
        st.error('Username/password is incorrect')
elif authentication_status == None:
    with col1:
        st.warning('Kérlek jelentkezz be!')
        st.write("Ha problémád van a bejelentkezéssel, kérlek vedd fel a kapcsolatot velünk!")