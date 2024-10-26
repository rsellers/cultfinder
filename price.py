import os
import json
import requests
from datetime import datetime, timedelta
from configparser import ConfigParser
from dotenv import load_dotenv

def fetch_price_data(project_name):
    """
    Fetch hourly price data for a cryptocurrency over the date range
    present in the project folder, compute daily OHLC data,
    and save it to a JSON file.

    Parameters:
    - project_name (str): The name of the project.

    Output:
    - Saves the OHLC data to /tg/<project>/<project>_price.json
    """

    # Load environment variables
    load_dotenv()
    COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')

    if not COINGECKO_API_KEY:
        print("CoinGecko API key not found in environment variables.")
        return

    # Read the coin information from coins.ini
    config = ConfigParser()
    if not os.path.exists('coins.ini'):
        print("coins.ini file not found.")
        return

    config.read('coins.ini')

    if project_name not in config.sections():
        print(f"Project '{project_name}' not found in coins.ini.")
        return

    # Get the api_id for the project
    api_id = config.get(project_name, 'api_id', fallback=None)

    if not api_id:
        print(f"api_id not found for project '{project_name}' in coins.ini.")
        return

    # Construct the project directory path
    project_dir = os.path.join('tg', project_name)

    if not os.path.exists(project_dir):
        print(f"Project directory '{project_dir}' does not exist.")
        return

    # Get the list of date directories
    date_dirs = [d for d in os.listdir(project_dir) if os.path.isdir(os.path.join(project_dir, d))]
    # Filter directories that match 'YYYY-MM-DD' format
    date_dirs = [d for d in date_dirs if is_valid_date(d)]

    if not date_dirs:
        print(f"No date directories found in '{project_dir}'.")
        return

    # Determine the date range
    start_date = min(date_dirs)
    end_date = max(date_dirs)
    print(f"Fetching price data from {start_date} to {end_date} for '{api_id}'.")

    # Convert dates to UNIX timestamps (in seconds)
    start_timestamp = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
    end_timestamp = int((datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)).timestamp())  # Include the end date

    # Fetch price data from CoinGecko
    url = f"https://api.coingecko.com/api/v3/coins/{api_id}/market_chart/range"
    params = {
        'vs_currency': 'usd',
        'from': start_timestamp,
        'to': end_timestamp,
        'x_cg_api_key': COINGECKO_API_KEY
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
    except Exception as e:
        print(f"Error fetching data from CoinGecko: {e}")
        return

    if 'prices' not in data:
        print(f"Error: 'prices' not found in the response for '{api_id}'.")
        print(f"Response: {data}")
        return

    # Process the data to compute daily OHLC
    price_data = {}
    for timestamp, price in data['prices']:
        date = datetime.utcfromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')
        if date not in price_data:
            price_data[date] = {
                'open': price,
                'high': price,
                'low': price,
                'close': price
            }
            last_price = price  # Keep track of the last price for close
        else:
            price_data[date]['high'] = max(price_data[date]['high'], price)
            price_data[date]['low'] = min(price_data[date]['low'], price)
            price_data[date]['close'] = price  # Update close price to the latest price in the day
            last_price = price

    # Save the OHLC data to JSON file
    output_filepath = os.path.join(project_dir, f"{project_name}_price.json")
    try:
        with open(output_filepath, 'w', encoding='utf-8') as outfile:
            json.dump(price_data, outfile, indent=4)
        print(f"Price data saved to '{output_filepath}'.")
    except Exception as e:
        print(f"Error writing price data to '{output_filepath}': {e}")

def is_valid_date(date_str):
    """Check if a string is a valid date in 'YYYY-MM-DD' format."""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False
    
def search_project_data(project_name):
    """
    Search for the project using the CoinGecko Pro API and return project data like
    social media links, category, and other relevant information.
    
    Parameters:
    - project_name (str): The name of the project to search for.

    Output:
    - Returns the project details in JSON format.
    """
    # Load environment variables
    load_dotenv()
    COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')

    if not COINGECKO_API_KEY:
        print("CoinGecko API key not found in environment variables.")
        return

    # Construct the search URL
    search_url = "https://api.coingecko.com/api/v3/search"
    headers = {"accept": "application/json"}
    params = {'query': project_name, 'x_cg_api_key': COINGECKO_API_KEY}

    try:
        response = requests.get(search_url, headers=headers, params=params)
        project_data = response.json()

        # Print the data for review
        print(f"Project data for '{project_name}':")
        print(json.dumps(project_data, indent=4))

        return project_data

    except Exception as e:
        print(f"Error fetching search data from CoinGecko: {e}")
        return None

if __name__ == '__main__':
    #fetch_price_data('spx6900')
    print(json.dumps(search_project_data('Kamala Horris'), indent=4))