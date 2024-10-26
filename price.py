import os
import json
import requests
import urllib 
from datetime import datetime, timedelta
from configparser import ConfigParser
import configparser
import time

from bs4 import BeautifulSoup
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
    Search for the project using the CoinGecko API and return project data
    including api_id, ticker, and market_cap_rank.

    Parameters:
    - project_name (str): The name of the project to search for.

    Returns:
    - dict: A dictionary with keys 'api_id', 'ticker', and 'market_cap_rank'.
    """
    # Load environment variables
    load_dotenv()
    COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')

    if not COINGECKO_API_KEY:
        print("CoinGecko API key not found in environment variables.")
        return None

    # Construct the search URL
    search_url = "https://api.coingecko.com/api/v3/search"
    headers = {"accept": "application/json"}
    params = {'query': project_name, 'x_cg_api_key': COINGECKO_API_KEY}

    try:
        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()
        project_data = response.json()

        # Check if any coins are found
        coins = project_data.get('coins', [])
        if not coins:
            print(f"No coins found for project '{project_name}'.")
            return None

        # Find the best matching coin
        for coin in coins:
            if coin.get('name').lower() == project_name.lower():
                break
        else:
            coin = coins[0]  # Default to the first coin if no exact match

        # Extract the required fields
        result = {
            'api_id': coin.get('api_symbol'),
            'ticker': coin.get('symbol'),
            'market_cap_rank': coin.get('market_cap_rank'),
        }

        # Print the result for review
        #print(f"Project data for '{project_name}':")
        #print(json.dumps(result, indent=4))

        return result

    except Exception as e:
        print(f"Error fetching search data from CoinGecko: {e}")
        return None

def scrape_project_socials_coingecko(api_id):
    req = urllib.request.Request(f"https://www.coingecko.com/en/coins/{api_id}")
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0')
    req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8')
    req.add_header('Accept-Language', 'en-US,en;q=0.5')

    try:
        response = urllib.request.urlopen(req).read().decode('utf-8')
    except urllib.error.URLError as e:
        print(f"Error fetching CoinGecko page: {e}")
        return {}

    soup = BeautifulSoup(response, 'html.parser')
    
    social_links = {}
    
    # Gather all anchor tags with URLs
    for link in soup.find_all('a', href=True):
        href = link['href'].lower()
        
        # Skip unwanted URLs
        if 'gecko' in href or href == 'https://discord.gg/ehrkach':
            continue
        
        # Detect and add Telegram URLs
        if href.startswith('https://t.me/'):
            key = 'tg'
            count = 1
            while key in social_links:  # Increment key for duplicates
                count += 1
                key = f'telegram{count}'
            social_links[key] = href
        
        # Detect and add Discord URLs
        elif href.startswith('https://discord.gg/'):
            key = 'discord'
            count = 1
            while key in social_links:
                count += 1
                key = f'discord{count}'
            social_links[key] = href
            
        # Detect and add Twitter URL if found
        elif 'twitter' in href and 'twitter' not in social_links:
            social_links['twitter'] = href

    return social_links

def search_project_data_full(api_id):
    """
    Fetch specific project data from the CoinGecko Pro API for the given api_id.

    Parameters:
    - api_id (str): The CoinGecko API ID for the project.

    Returns:
    - dict: A dictionary containing 'api_id', 'ticket', 'market_cap_rank', 'chain', 'ca', 'tg_id', and 'twitter_id'.
    """
    # Load environment variables
    load_dotenv()
    COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')

    if not COINGECKO_API_KEY:
        print("CoinGecko API key not found in environment variables.")
        return None

    # Construct the URL
    url = f"https://api.coingecko.com/api/v3/coins/{api_id}"
    headers = {"accept": "application/json"}
    params = {'x_cg_api_key': COINGECKO_API_KEY}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        project_data = response.json()

        # Extract the required fields
        result = {
            'api_id': project_data.get('id'),
            'ticker': project_data.get('symbol'),
            'market_cap_rank': project_data.get('market_cap_rank'),
            'chain': project_data.get('asset_platform_id'),
            'ca': project_data.get('contract_address'),
            'tg_id': project_data.get('links', {}).get('telegram_channel_identifier'),
            'twitter_id': project_data.get('links', {}).get('twitter_screen_name'),
        }

        # Print the result for review
        # print(f"Extracted data for '{api_id}':")
        # print(json.dumps(result, indent=4))

        return result

    except requests.RequestException as e:
        print(f"Error fetching project data from CoinGecko: {e}")
        return None

def update_coins_ini(project_data_full, social_scrape, ini_file='coins.ini'):
    """
    Update the coins.ini file with data from project_data_full and social_scrape.

    Parameters:
    - project_data_full (dict): Dictionary containing project data.
    - social_scrape (dict): Dictionary containing social scrape data.
    - ini_file (str): The path to the ini file (default is 'coins.ini').

    Rules:
    1. Create a new entry called [<api_id>].
    2. If the entry already exists, update it without duplicating.
    3. The fields in the ini file are derived from the keys in the provided dictionaries.
    """
    # Create a ConfigParser object
    config = configparser.ConfigParser()

    # Read the existing ini file if it exists
    if os.path.exists(ini_file):
        config.read(ini_file)
    else:
        # If the file doesn't exist, create it
        open(ini_file, 'a').close()

    # Extract the api_id from project_data_full
    api_id = project_data_full.get('api_id')
    if not api_id:
        print("Error: 'api_id' not found in project_data_full.")
        return

    # Ensure the section exists
    if not config.has_section(api_id):
        config.add_section(api_id)

    # Combine the dictionaries
    combined_data = {**project_data_full, **social_scrape}

    # Remove any keys with None values and convert all values to strings
    cleaned_data = {k: str(v) for k, v in combined_data.items() if v is not None}

    # Update the ini file with the combined data
    for key, value in cleaned_data.items():
        config.set(api_id, key, value)

    # Write the changes back to the ini file
    with open(ini_file, 'w') as configfile:
        config.write(configfile)

    print(f"Successfully updated '{ini_file}' with data for '[{api_id}]'.")


if __name__ == '__main__':
    
    memelist = [
    "Beercoin", "Balls of Fate",  "Based Chad", "Hege", 
    "HeeeHeee", "Zack Morris", "Vita Inu", "PIKA to PIKO", "Bamboo on Base", 
    "ORC", "RyuJin", "SNAP", "MAD", "Gou", 
    "Baby Neiro", "Nya", "autism", "Feisty Doge NFT", "Mochi", 
    "Andy", "coby", "ChompCoin", "Elon", "Inferno", 
    "Gondola", "catownkimono", "MAGA Fight for Trump", "Dark MAGA", 
    "MEDUSA", "BASED INTERNET PANDA", "Fairfun", "SunWukong",
    "Look bro", "nomnom", "Chihuahua Chain", "Hana", "WEWECOIN", 
    "BOB", "Shina Inu", "SEIYAN", "Roaring Kitty", "Invest Zone", 
    "Cheeseball", "TAO INU", "Kimbo", "Popo The Frog", "Crash On Base", 
    "Wrapped DOG", "MILKBAG", "Kamala Horris", "Pozo Coin", "monkeyhaircut", 
    "AXOL", "LFGO", "Goatseus Maximus", "r/snoofi", "DRIP", 
    "Dagknight Dog", "Solchat", "Fefe", "Draggy CTO", "AndyBlast", 
    "aaa cat", "GUMMY", "Ton Cat", "Bog", "MACHI", 
    "1GUY", "Catcoin", "AI INU", "Bitcoin on Base", "Bad Idea AI", 
    "Black Dragon", "Optimus AI", "Hemule", "Kekistan", "GOOFY", 
    "Manifest", "Sharbi", "Pundu", "Dejitaru Tsuka", "Valhalla Index", 
    "INFERNO", "Elon", "Gondola", "catownkimono", "Dark MAGA"
    ]   

    # Trial function calls 
    # print(search_project_data('kamala horris'))
    # update_coins_ini(search_project_data_full('kamala-horris'), scrape_project_socials_coingecko('kamala-horris'))

    for project_name in memelist:
        time.sleep(30)
        print(f"\nProcessing project: {project_name}")
        # Step 2: Call search_project_data with the project_name
        project_data = search_project_data(project_name)
        if project_data:
            # Extract api_id from the returned data
            api_id = project_data.get('api_id')
            if api_id:
                # Step 3: Call search_project_data_full with api_id
                project_data_full = search_project_data_full(api_id)
                if project_data_full:
                    # Step 4: Check if chain is 'solana' or 'ethereum'
                    chain = project_data_full.get('chain')
                    if chain in ['solana', 'ethereum', 'base']:
                        # Step 5: Call scrape_project_socials_coingecko(api_id)
                        social_scrape = scrape_project_socials_coingecko(api_id)
                        if social_scrape:
                            # Step 6: Call update_coins_ini with the collected data
                            update_coins_ini(project_data_full, social_scrape)
                        else:
                            print(f"No social media links found for '{api_id}'.")
                    else:
                        print(f"Project '{api_id}' is on chain '{chain}', which is not 'solana' or 'ethereum'. Skipping.")
                else:
                    print(f"No full data found for project '{api_id}'.")
            else:
                print(f"No 'api_id' found in project data for '{project_name}'.")
        else:
            print(f"No data found for project '{project_name}'.")