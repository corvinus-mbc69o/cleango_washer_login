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
import time
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

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
    
    st.markdown("Üdvözöllek, " + name + "!")
    
    washes_sql_query = "SELECT * FROM cleango.valid_washes where wash_date is not NULL;"

    if 'valid_washes' not in st.session_state:
        with st.spinner('Please wait, Downloading Data from SQL (aprox. 2 mins)'):
            valid_washes = sql_query(washes_sql_query)
            st.session_state['valid_washes'] = valid_washes
    else:
        valid_washes = st.session_state.valid_washes

    st.markdown("## Mosások")
    valid_washes = format_data_washing_complex_data(valid_washes)
    cols_to_filter = ['washer_name', 'wash_date', 'wash_date_day', 'b2b_b2c_limo', 'mosas_tipus', 'wash_type', 'car_category', 'brand_name', 'make_name' , 'plate_number', 'base_wash_commission', 'count_extra', 'extra_commision_price', 'total_commision_price', 'user_id', 'id']
    valid_washes = valid_washes[cols_to_filter]

    valid_washes['wash_date'] = pd.to_datetime(valid_washes['wash_date'])
    valid_washes['wash_date_day'] = pd.to_datetime(valid_washes['wash_date_day'])
    # convert wash_date_day to only date
    valid_washes['wash_date_day'] = valid_washes['wash_date_day'].dt.date


    with st.form(key='filter_washers'):
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            # create a date filter called "date_from"
            date_from = st.date_input('Start Date', value=pd.to_datetime('2023-01-01'))
        with col2:
            # create a date filter called "date_to" set value to today
            date_to = st.date_input('End Date', value=pd.to_datetime(datetime.today().strftime('%Y-%m-%d')))
            # add one day to the date_to
            date_to = date_to + pd.DateOffset(days=1)
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

        # get bonus mosasszam
        bonus_sql_query = "SELECT name, type, bonus_mosasszam FROM cleango.bi_bonus_mosasszam"
        bonus_mosasszam_df = sql_query(bonus_sql_query)
        # rename type column to wash_type and name to mosas_tipus
        bonus_mosasszam_df = bonus_mosasszam_df.rename(columns={'type': 'wash_type', 'name': 'mosas_tipus'})
        # merge bonus mosasszam wih valid_washes
        valid_washes = valid_washes.merge(bonus_mosasszam_df, how='left', left_on=['mosas_tipus', 'wash_type'], right_on=['mosas_tipus', 'wash_type'])

        st.dataframe(valid_washes)
        # total number of washes
        st.markdown("Összes mosás száma: {}".format(valid_washes.shape[0]))
        # total number of bonus washes
        st.markdown("Összes bonus mosás száma: {}".format(round(valid_washes['bonus_mosasszam'].sum())))
        # total commission
        st.markdown("Összes jutalék: {} Ft".format(round(valid_washes['total_commision_price'].sum())))
        st.download_button(label="Download data as CSV",
                            data=convert_df(valid_washes),
                            file_name='valid_washes.csv', mime='text/csv')
    
        st.markdown("## Mosó statisztika")
        # count the number of washes per washer
        washes_per_washer = valid_washes.groupby(['washer_name']).agg(
            total_commision_price = ('total_commision_price', 'sum'),
            mosas_db = ('id', 'count'),
            mosas_bonus_db = ('bonus_mosasszam', 'sum')
        ).reset_index(drop=False)

        st.dataframe(washes_per_washer)
        
    st.markdown("## Levonasok")

    deductions_sql_query = "SELECT * FROM cleango.bi_moso_levonas"
    deductions_data = sql_query(deductions_sql_query)
    if washer_names != ['All']:
        deductions_data = deductions_data[deductions_data['washer_name'].isin(washer_names)]
    #deductions_data = deductions_data[((deductions_data['date'] >= date_from) & (deductions_data['date'] <= date_to)) | (deductions_data['date'].isnull())]

    st.dataframe(deductions_data)

    # add record to the table
    st.markdown("## Levonas hozzaadasa")
    with st.form(key='add_deduction'):
        created_at = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            washer_names = valid_washes['washer_name'].unique()
            washer_names = np.insert(washer_names, 0, 'Select a washer')
            washer_name = st.selectbox('Washer Name', washer_names)
        with col2:
            date_of_deduction = st.date_input('Date of deduction', value=pd.to_datetime(datetime.today().strftime('%Y-%m-%d')))
        with col3:
            value = st.number_input('Value', value=0)
        
        comment = st.text_input('Comment', value='')
        add_deduction = st.form_submit_button('Add Deduction')

    if add_deduction:
        if washer_name == 'Select a washer':
            st.error('Please select a washer')
        else:
            # add record to the table
            query_to_insert = "INSERT INTO cleango.bi_moso_levonas (washer_name, date, value, comment, created_at) VALUES ('{}', '{}', '{}', '{}', '{}')".format(washer_name, date_of_deduction, value, comment, created_at)
            conn = create_connection()
            cursor = conn.cursor()
            cursor.execute(query_to_insert)
            conn.commit()
            cursor.close()
            conn.close()
            st.write(query_to_insert)
            st.write('Deduction added successfully')

    st.markdown("## Levonas torlese")
    with st.form(key='delete_deduction'):
        # just make it possible to select an ID and delete that record from the cleango.bi_moso_levonas table
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            deduction_ids = deductions_data['id'].unique()
            # convert deduction_ids to string
            deduction_ids = deduction_ids.astype(str)
            deduction_ids = np.insert(deduction_ids, 0, 'Select an ID')
            deduction_id = st.selectbox('Deduction ID', deduction_ids)
        delete_deduction = st.form_submit_button('Delete Deduction')

    if delete_deduction:
        if deduction_id == 'Select an ID':
            st.error('Please select an ID')
        else:
            # delete record from the table
            query_to_delete = "DELETE FROM cleango.bi_moso_levonas WHERE id = {}".format(deduction_id)
            conn = create_connection()
            cursor = conn.cursor()
            cursor.execute(query_to_delete)
            conn.commit()
            cursor.close()
            conn.close()
            st.write(query_to_delete)
            st.write('Deduction deleted successfully')

    st.markdown("## Bonus mosasszam frissitese")
    show_bonus_table = st.checkbox('Show bonus mosaszam table', value=False)
    if show_bonus_table:
        bonus_sql_query = "SELECT * FROM cleango.bi_bonus_mosasszam"
        bonus_data = sql_query(bonus_sql_query)
        st.dataframe(bonus_data)
        st.download_button(label="Download data as CSV",
                        data=convert_df(bonus_data),
                        file_name='bonus_data.csv', mime='text/csv')
        st.markdown('Toltsd le ezt a tablat, modositsd, majd toltsd fel ujra az ez alatt levo formmal.')

    with st.form(key='update_bonus_wash_count'):
        # upload a csv_file that contains the bonus mosaszam data
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
        update_bonus_wash = st.form_submit_button('Update Bonus Wash Count')

    if update_bonus_wash:
        # check that the uploaded file is not empty
        if uploaded_file is None:
            st.write('Please upload a file')
        else:
            # check that the uploaded file has the correct columns
            columns_to_check = ['name', 'type', 'bonus_mosasszam']
            df_bonus = pd.read_csv(uploaded_file)
            # there is a delated_at column
            if 'deleted_at' in df_bonus.columns:
                df_bonus = df_bonus.drop(['deleted_at'], axis=1)
            if not set(columns_to_check).issubset(df_bonus.columns):
                st.write('Please upload a file that contains the following columns: {}'.format(columns_to_check))
            else:
                # delete the table called: cleango.bi_bonus_mosasszam
                query_to_delete = "DELETE FROM cleango.bi_bonus_mosasszam where id > 0"
                conn = create_connection()
                cursor = conn.cursor()
                cursor.execute(query_to_delete)
                conn.commit()
                cursor.close()
                conn.close()
                st.write(query_to_delete)
                st.write('Table deleted successfully')

                # sleep for 5 seconds
                time.sleep(30)
                # update the table with the new data
                created_at = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
                for index, row in df_bonus.iterrows():
                    query_to_insert = "INSERT INTO cleango.bi_bonus_mosasszam (name, type, bonus_mosasszam, created_at) VALUES ('{}', '{}', '{}', '{}')".format(row['name'], row['type'], row['bonus_mosasszam'], created_at)
                    st.write(query_to_insert)
                    conn = create_connection()
                    cursor = conn.cursor()
                    cursor.execute(query_to_insert)
                    conn.commit()
                    cursor.close()
                    conn.close()
                


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
            # add one day to the date_to
            date_to = date_to + pd.DateOffset(days=1)
        
        # create a button
        submitted = st.form_submit_button('Szűrés')
    
    if submitted:
        washes_sql_query = "SELECT * FROM cleango.valid_washes where wash_date is not NULL;"

        if 'valid_washes' not in st.session_state:
            with st.spinner('Please wait, Downloading Data from SQL (aprox. 2 mins)'):
                valid_washes = sql_query(washes_sql_query)
                st.session_state['valid_washes'] = valid_washes
        else:
            valid_washes = st.session_state.valid_washes


        st.markdown("## Mosások - Mosó: {}".format(name))
        valid_washes = format_data_washing_complex_data(valid_washes)
        cols_to_filter = ['washer_name', 'wash_date', 'wash_date_day', 'b2b_b2c_limo', 'mosas_tipus', 'wash_type', 'car_category', 'brand_name', 'make_name' , 'plate_number', 'base_wash_commission', 'count_extra', 'extra_commision_price', 'total_commision_price', 'user_id', 'id']
        valid_washes = valid_washes[cols_to_filter]

         # get bonus mosasszam
        bonus_sql_query = "SELECT name, type, bonus_mosasszam FROM cleango.bi_bonus_mosasszam"
        bonus_mosasszam_df = sql_query(bonus_sql_query)
        # rename type column to wash_type and name to mosas_tipus
        bonus_mosasszam_df = bonus_mosasszam_df.rename(columns={'type': 'wash_type', 'name': 'mosas_tipus'})
        # merge bonus mosasszam wih valid_washes
        valid_washes = valid_washes.merge(bonus_mosasszam_df, how='left', left_on=['mosas_tipus', 'wash_type'], right_on=['mosas_tipus', 'wash_type'])


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
            # total commission
            st.markdown("Összes jutalék: {} Ft".format(round(valid_washes['total_commision_price'].sum())))

        with col2:
            # total number of washes
            st.markdown("Összes mosás száma bonus szerint: {}".format(round(valid_washes['bonus_mosasszam'].sum(), 2)))
        
        with col1:
            st.download_button(label="Adat letöltése",
                            data=convert_df(valid_washes),
                            file_name='valid_washes.csv', mime='text/csv')
            
        st.markdown("## Levonasok")

        deductions_sql_query = "SELECT * FROM cleango.bi_moso_levonas"
        deductions_data = sql_query(deductions_sql_query)
        deductions_data = deductions_data[(deductions_data['date'] >= date_from) & (deductions_data['date'] <= date_to)]
        deductions_data = deductions_data[deductions_data['washer_name'].isin([config['credentials']['usernames'][username]['moso_db_name']])]
        
        st.dataframe(deductions_data)
        # calculate total value of deduction
        total_deduction = deductions_data['value'].sum()
        st.markdown("Összes levonás: {} Ft".format(round(total_deduction), 2))
        st.markdown('Ha ez az összeg negatív, akkor a kivalasztott időszakban valamiért levonást kaptál. Ha pozitiv, akkor pedig a CleanGo tartozik neked ekkora összegget.')
        st.markdown('***')
        st.markdown("## Jutalek + Levonas")
        st.markdown("Összes jutalék - Összes levonás: {} Ft".format(round(valid_washes['total_commision_price'].sum() +total_deduction, 2)))