import pymysql
import paramiko
import pandas as pd
from paramiko import SSHClient
from sshtunnel import SSHTunnelForwarder
import streamlit as st
import io

def sql_query(query_string, type = 'simple'):

    if type == 'ssh':
        #mypkey = paramiko.RSAKey.from_private_key_file('krinya_ssh')
        private_key_file = io.StringIO(st.secrets['database']['rsa_private_key'])
        mypkey = paramiko.RSAKey.from_private_key(private_key_file)
        
    
        # comments are the fields in SequelPro
        MySQL_hostname = st.secrets['ssh']['MySQL_hostname'] #MySQL Host
        sql_username = st.secrets['ssh']['sql_username'] #Username
        sql_main_database = st.secrets['ssh']['sql_main_database'] #Database Name
        sql_port = st.secrets['ssh']['sql_port']
        ssh_host = st.secrets['ssh']['ssh_host'] #SSH Host
        ssh_user = st.secrets['ssh']['ssh_user'] #SSH Username
        ssh_port = st.secrets['ssh']['ssh_port']
        sql_ip = st.secrets['ssh']['sql_ip']
        pw = st.secrets['ssh']['pw']

        with SSHTunnelForwarder(
            (ssh_host, ssh_port),
            ssh_username=ssh_user,
            ssh_pkey=mypkey,
            remote_bind_address=(MySQL_hostname, sql_port)) as tunnel:
            conn = pymysql.connect(host='127.0.0.1', user=sql_username,
                                passwd=pw,
                                ssl_key='krinya_ssh', db=sql_main_database,
                                port=tunnel.local_bind_port)
            query = query_string
            data = pd.read_sql_query(query, conn)
            conn.close()

    if type == 'simple':
        hostname = st.secrets['simple']['hostname'] #MySQL Host
        username = st.secrets['simple']['sql_username'] #username
        pw = st.secrets['simple']['pw'] #password
        port = st.secrets['simple']['port'] #port
        main_db = st.secrets['simple']['sql_main_database'] #database
        
        # Establish a connection to the database
        conn = pymysql.connect(host=hostname, port=port, user=username, passwd=pw, db=main_db)
    
        # Execute the SQL query and retrieve data
        query = query_string
        data = pd.read_sql_query(query, conn)
    
        # Close the database connection
        conn.close()

    return data

def create_connection(type='simple'):

    if type == 'simple':
        hostname = st.secrets['simple']['hostname'] #MySQL Host
        username = st.secrets['simple']['sql_username'] #username
        pw = st.secrets['simple']['pw'] #password
        port = st.secrets['simple']['port'] #port
        main_db = st.secrets['simple']['sql_main_database'] #database
        
        # Establish a connection to the database
        conn = pymysql.connect(host=hostname, port=port, user=username, passwd=pw, db=main_db)

    return conn
