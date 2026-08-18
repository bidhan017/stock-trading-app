import requests
import os
from dotenv import load_dotenv
load_dotenv()
import mysql.connector
from datetime import datetime

API_KEY = os.getenv("MASSIVE_API_KEY")

LIMIT = 100
DS = '2025-09-25'
'''
url= f'https://api.massive.com/v3/reference/tickers?market=indices&active=true&order=asc&limit={LIMIT}&sort=ticker&apiKey={API_KEY}'
response = requests.get(url)


tickers = []
data = response.json()
for ticker in data['results']:
    tickers.append(ticker['ticker'])

print(tickers)
'''
def run_stock_job():
    DS = datetime.now().strftime('%Y-%m-%d')
    #url = f'https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&order=asc&limit={LIMIT}&sort=ticker&apiKey={POLYGON_API_KEY}'
    url= f'https://api.massive.com/v3/reference/tickers?market=indices&active=true&order=asc&limit={LIMIT}&sort=ticker&apiKey={API_KEY}'
    response = requests.get(url)
    tickers = []

    data = response.json()
    for ticker in data['results']:
        ticker['ds'] = DS
        tickers.append(ticker)

    while 'next_url' in data:
        print('requesting next page', data['next_url'])
        response = requests.get(data['next_url'] + f'&apiKey={API_KEY}')
        data = response.json()
        
        # Check if response contains results before processing
        if 'results' not in data:
            print(f'Warning: API response missing results key. Response: {data}')
            break
        
        for ticker in data['results']:
            ticker['ds'] = DS
            tickers.append(ticker)

    example_ticker =  {'ticker': 'ZWS', 
        'name': 'Zurn Elkay Water Solutions Corporation', 
        'market': 'stocks', 
        'locale': 'us', 
        'primary_exchange': 'XNYS', 
        'type': 'CS', 
        'active': True, 
        'currency_name': 'usd', 
        'cik': '0001439288', 
        'composite_figi': 'BBG000H8R0N8', 	'share_class_figi': 'BBG001T36GB5', 	
        'last_updated_utc': '2025-09-11T06:11:10.586204443Z',
        'ds': '2025-09-25'
        }

    fieldnames = list(example_ticker.keys())

    # Load to MySQL instead of CSV
    load_to_mysql(tickers, fieldnames)
    print(f'Loaded {len(tickers)} rows to MySQL')



def load_to_mysql(rows, fieldnames):
    # Build connection kwargs from environment variables
    connect_kwargs = {
        'user': os.getenv('MYSQL_USERNAME'),
        'password': os.getenv('MYSQL_PASSWORD'),
        'host': os.getenv('MYSQL_HOST'),
        'port': int(os.getenv('MYSQL_PORT')),
        'database': os.getenv('MYSQL_DATABASE'),
    }

    print(f"Attempting to connect to MySQL: {connect_kwargs['host']}:{connect_kwargs['port']}/{connect_kwargs['database']}")
    
    try:
        conn = mysql.connector.connect(**connect_kwargs)
    except mysql.connector.Error as err:
        print(f"\n❌ ERROR: Failed to connect to MySQL")
        print(f"   Host: {connect_kwargs['host']}:{connect_kwargs['port']}")
        print(f"   Database: {connect_kwargs['database']}")
        print(f"   Error: {err}")
        print(f"\n📝 Steps to fix:")
        print(f"   1. Start MySQL: sudo service mysql start")
        print(f"   2. Create database: mysql -u root -p -e \"CREATE DATABASE {connect_kwargs['database']};\"")
        print(f"   3. Run script again: python script.py")
        return
    try:
        cs = conn.cursor()
        try:
            table_name = os.getenv('MYSQL_TABLE')

            # Define typed schema based on example_ticker
            type_overrides = {
                'ticker': 'VARCHAR(50)',
                'name': 'VARCHAR(255)',
                'market': 'VARCHAR(50)',
                'locale': 'VARCHAR(50)',
                'primary_exchange': 'VARCHAR(50)',
                'type': 'VARCHAR(50)',
                'active': 'BOOLEAN',
                'currency_name': 'VARCHAR(50)',
                'cik': 'VARCHAR(50)',
                'composite_figi': 'VARCHAR(100)',
                'share_class_figi': 'VARCHAR(100)',
                'last_updated_utc': 'DATETIME',
                'ds': 'VARCHAR(50)'
            }
            columns_sql_parts = []
            for col in fieldnames:
                col_type = type_overrides.get(col, 'VARCHAR(255)')
                columns_sql_parts.append(f'`{col}` {col_type}')

            create_table_sql = f'CREATE TABLE IF NOT EXISTS {table_name} ( ' + ', '.join(columns_sql_parts) + ' )'
            cs.execute(create_table_sql)

            column_list = ', '.join([f'`{c}`' for c in fieldnames])
            placeholders = ', '.join(['%s' for c in fieldnames])
            insert_sql = f'INSERT INTO {table_name} ( {column_list} ) VALUES ( {placeholders} )'  

            # Conform rows to fieldnames
            transformed = []
            for t in rows:
                row_values = []
                for k in fieldnames:
                    row_values.append(t.get(k, None))
                #print(row_values)
                transformed.append(row_values)

            if transformed:
                for row in transformed:
                    cs.execute(insert_sql, row)
            conn.commit()
        finally:
            cs.close()
    finally:
        conn.close()


if __name__ == '__main__':
    run_stock_job()