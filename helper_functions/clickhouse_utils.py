import os
import dotenv
import clickhouse_connect as cc
import requests
import pandas as pd
import json
import numpy as np

dotenv.load_dotenv()
# Get OPLabs DB Credentials
env_ch_host = os.getenv("OP_CLICKHOUSE_HOST")
env_ch_user = os.getenv("OP_CLICKHOUSE_USER")
env_ch_pw = os.getenv("OP_CLICKHOUSE_PW")
env_ch_port = os.getenv("OP_CLICKHOUSE_PORT")

def connect_to_clickhouse_db(
    ch_host=env_ch_host,
    ch_port=env_ch_port,
    ch_user=env_ch_user,
    ch_pw=env_ch_pw
):
    client = cc.get_client(host=ch_host, port=ch_port, username=ch_user, password=ch_pw, secure=True)
    return client

def get_clickhouse_type(dtype):
    if pd.api.types.is_integer_dtype(dtype):
        return "Int64"
    elif pd.api.types.is_float_dtype(dtype):
        return "Float64"
    elif pd.api.types.is_bool_dtype(dtype):
        return "UInt8"
    elif pd.api.types.is_datetime64_any_dtype(dtype):
        return "DateTime64(3)"
    elif pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(dtype):
        return "String"
    else:
        return "String"  # Default to String for unknown types

def create_table_if_not_exists(client, table_name, df):
    columns = []
    for col, dtype in df.dtypes.items():
        ch_type = get_clickhouse_type(dtype)
        columns.append(f"`{col}` Nullable({ch_type})")
    
    columns_str = ", ".join(columns)
    query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        {columns_str}
    ) ENGINE = MergeTree() ORDER BY tuple()
    """
    client.command(query)
    print(f"Table '{table_name}' created or already exists.")

def write_api_data_to_clickhouse(api_url, table_name, client=None, if_exists='replace'):
    """
    Fetches data from an API and writes it to a ClickHouse table.
    Creates the table if it doesn't exist.
    """
    if client is None:
        client = connect_to_clickhouse_db()

    # Fetch data from API
    response = requests.get(api_url)
    data = response.json()

    # Convert to DataFrame
    df = pd.DataFrame(data)

    write_df_to_clickhouse(df, table_name, client, if_exists)

def write_csv_to_clickhouse(csv_file_path, table_name, client=None, if_exists='replace'):
    """
    Reads a CSV file and writes its contents to a ClickHouse table.
    Creates the table if it doesn't exist.
    """
    if client is None:
        client = connect_to_clickhouse_db()

    # Read CSV file
    df = pd.read_csv(csv_file_path)

    write_df_to_clickhouse(df, table_name, client, if_exists)

def write_df_to_clickhouse(df, table_name, client=None, if_exists='replace'):
    """
    Writes a DataFrame to a ClickHouse table.
    
    :param df: pandas DataFrame to write
    :param table_name: name of the table in ClickHouse
    :param client: ClickHouse client (if None, a new connection will be established)
    :param if_exists: 'append' to add to existing data, 'replace' to delete existing data and overwrite
    """
    if client is None:
        client = connect_to_clickhouse_db()

    # Convert float columns to strings if they contain any non-numeric values
    for col in df.select_dtypes(include=['float64']).columns:
        if df[col].apply(lambda x: not pd.api.types.is_number(x)).any():
            df[col] = df[col].astype(str)

    # Replace NaN, inf, and -inf values with None
    df = df.replace([np.inf, -np.inf, np.nan], None)

    # Convert all object columns to strings
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].astype(str)

    # Check if table exists
    table_exists = client.command(f"EXISTS TABLE {table_name}") == 1

    if table_exists and if_exists == 'replace':
        # Delete existing data
        client.command(f"TRUNCATE TABLE {table_name}")
        print(f"Existing data in table '{table_name}' has been deleted.")
    elif not table_exists:
        # Create table if it doesn't exist
        create_table_if_not_exists(client, table_name, df)

    # Write to ClickHouse
    client.insert_df(table_name, df)
    
    if if_exists == 'append':
        print(f"Data appended to table '{table_name}' successfully.")
    else:
        print(f"Data written to table '{table_name}' successfully, replacing previous data.")