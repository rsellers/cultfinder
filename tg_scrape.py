from telethon import TelegramClient
from telethon.utils import get_display_name
from telethon.errors import FloodWaitError
from telethon.tl.types import User, Channel
from datetime import datetime
import asyncio
from openai import OpenAI
import os
from dotenv import load_dotenv
from prompt import ChatLogAnalysisResponse, CommunityMetrics
import tiktoken
import json
from datetime import datetime, timedelta, timezone
import time
import configparser
from collections import Counter
import re
from prompt import __version__
from price import fetch_price_data




load_dotenv()
print("Loaded environment variables.")

# Retrieve environment variables
try:
    api_id = int(os.getenv('TELEGRAM_API_ID'))
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    openai_version = os.getenv('OPENAI_VERSION') #version of the LLM to use

    client = OpenAI(api_key=openai_api_key)

    # Check for missing environment variables
    required_vars = {
        'TELEGRAM_API_ID': api_id,
        'TELEGRAM_API_HASH': api_hash,
        'TELEGRAM_PHONE': phone,
        'OPENAI_API_KEY': openai_api_key
    }

    for var_name, var_value in required_vars.items():
        if not var_value:
            raise EnvironmentError(f"The environment variable {var_name} is missing.")

    print("Environment variables loaded successfully.")

except Exception as e:
    print(f"Error loading environment variables: {e}")
    exit(1)

# URL pattern to match x.com and twitter.com URLs, case-insensitive
url_pattern = re.compile(r"https?://(x|twitter)\.com/([A-Za-z0-9_]+)/status/\d+", re.IGNORECASE)

def extract_metadata_socials_and_user_stats(data):
    # THIS EXPECTS JSON INPUTS!

    account_mentions = []
    unique_users = set()
    total_messages = 0

    # Check if the data input is valid
    if not isinstance(data, list):
        raise ValueError("Invalid data format. Expected a list of dictionaries.")
    
    # Parse the messages
    for entry in data:
        # Ensure the entry is a dictionary with both 'user' and 'message' fields
        if not isinstance(entry, dict):
            continue  # Skip invalid entries
        user = entry.get('user')
        message = entry.get('message')
        
        if not user or not message:
            continue  # Skip if either field is missing

        # Strip and normalize user data to avoid duplicates
        user = user.strip().lower()
        unique_users.add(user)
        total_messages += 1

        # Find all URLs in the message that match x.com or twitter.com
        try:
            matches = url_pattern.findall(message)
            for match in matches:
                # Normalize the URL to lowercase to avoid duplicates based on case
                account_url = f"https://{match[0].lower()}.com/{match[1].lower()}"
                account_mentions.append(account_url)
        except Exception as e:
            print(f"Error processing message: {message} | Error: {e}")

    # Tally the top 8 mentioned accounts
    account_counts = Counter(account_mentions)
    top_8_accounts = account_counts.most_common(8)

    # Prepare the result in JSON format
    result = {
        "socials": {
            "top_mentioned_accounts": [{"url": account, "mentions": count} for account, count in top_8_accounts]
        },
        "user_stats": {
            "unique_user_count": len(unique_users),
            "total_message_count": total_messages
        },
        "llm": {
            "llm_version": openai_version,
            "prompt_version": __version__
        },
        "date": {
            "date_process": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }

    return result



async def fetch_telegram_messages(
    tg_client,
    group,
    username,
    date_offset,
    max_filtered_filesize=150 * 1024,  # Default to 150 KB
    n=25  # For logging every nth message
):
    """
    Fetch text messages from a Telegram group starting from a specific date until constraints are met.

    Parameters:
    - tg_client: The TelegramClient instance to use.
    - group (str): Name of the group.
    - username (str): Telegram group username or link.
    - date_offset (datetime): The date from which to start fetching messages.
    - max_filtered_filesize (int): Maximum size of filtered messages in bytes.
    - n (int): Print metadata every nth message.

    Returns:
    - message_log_raw: List of dictionaries containing raw messages.
    - message_log_filtered: List of dictionaries containing filtered messages.
    """

    print("Fetching messages from group:", username)
    
    try:
        channel = await tg_client.get_entity(username)
        print(f"Successfully obtained entity for {username}")
    except Exception as e:
        print(f"Error getting Telegram entity for '{username}': {e}")
        return [], []

    message_log_raw = []
    message_log_filtered = []
    total_messages = 0
    filtered_messages_size = 0  # Accumulated size of filtered messages in bytes
    previous_message_text = None  # For duplicate message checking in filtered output
    last_message_id = None  # Keep track of the last message ID

    # Set date boundaries
    start_date = date_offset
    end_date = start_date + timedelta(days=1)

    # Ensure start_date and end_date are timezone-aware in UTC
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)

    print(f"Retrieving messages starting from {start_date} until {end_date}...")

    delay_between_requests = 0  # Adjust this value as needed (in seconds)

    last_message_id = 0  # Initialize to 0 to avoid NoneType issues

    while True:
        try:
            async for message in tg_client.iter_messages(
                channel,
                reverse=True,
                offset_date=start_date,
                min_id=last_message_id,  # Start from the last message ID
            ):
                message_date = message.date

                if message_date >= end_date:
                    print("Reached the end of the day.")
                    return message_log_raw, message_log_filtered

                if message_date < start_date:
                    continue  # Skip messages before the start date (shouldn't happen)

                total_messages += 1  # Track total number of messages fetched

                if message.message:
                    sender = await message.get_sender()

                    # Extract sender username
                    try:
                        sender_username = sender.username if sender.username else f"id_{sender.id}"
                    except:
                        sender_username = "null"

                    # Every nth message, print out some metadata
                    if total_messages % n == 0:
                        print(f"Pulling message #{total_messages}, date={message_date}, user={sender_username}")

                    timestamp = message_date.strftime('%Y-%m-%d %H:%M')
                    text = message.message

                    # Create a message entry as a dictionary
                    message_entry = {
                        'timestamp': timestamp,
                        'sender_username': sender_username,
                        'text': text
                    }

                    # Append the message entry to the raw log
                    message_log_raw.append(message_entry)

                    # For filtered output, apply filters:
                    # - Skip messages from bots
                    # - Skip duplicate messages (same as previous message)
                    try:
                        is_bot = isinstance(sender, User) and sender.bot
                        if is_bot:
                            continue  # Skip bots in filtered output
                        if previous_message_text is not None and text == previous_message_text:
                            continue  # Skip duplicate messages in filtered output
                    except Exception as e:
                        pass  # Handle exception silently

                    # If passes filters, add to filtered log
                    message_log_filtered.append(message_entry)

                    # Update previous message text
                    previous_message_text = text

                    # Calculate the size of the message entry when formatted
                    formatted_message_entry = f"Date:{timestamp}\nUsr:@{sender_username}\nMsg:{text}\n--\n"
                    message_entry_size = len(formatted_message_entry.encode('utf-8'))
                    filtered_messages_size += message_entry_size

                    if filtered_messages_size >= max_filtered_filesize:
                        print("Reached maximum filtered file size.")
                        return message_log_raw, message_log_filtered

                    # Update last_message_id to resume later if needed
                    last_message_id = message.id

                    # Optional: Add a small delay between processing messages to avoid rate limits
                    await asyncio.sleep(delay_between_requests)

            # If the loop completes without hitting the end date or size limit, break
            break

        except FloodWaitError as e:
            print(f"FloodWaitError: Telegram is asking you to wait for {e.seconds} seconds.")
            # Wait for the required amount of time
            for remaining in range(e.seconds, 0, -1):
                sys.stdout.write(f"\rWaiting for {remaining} seconds...")
                sys.stdout.flush()
                time.sleep(1)
            print("\nResuming message retrieval...")
            # After waiting, the loop will restart and continue fetching messages

        # except Exception as e:
        #     print(f"An unexpected error occurred: {e}")
        #     # Optionally, you can choose to handle other exceptions or exit
        #     return message_log_raw, message_log_filtered

    print(f"Total messages fetched: {total_messages}")
    print(f"Messages after filtering: {len(message_log_filtered)}")

    return message_log_raw, message_log_filtered

async def fetch_telegram_messages_for_date_range(
    group,
    date_start,
    date_end,
    ini_file='coins.ini',
    ini_index='tg',  # New parameter for specifying the INI index (default to 'tg')
    max_filtered_filesize=1024 * 1024  # Default to 1MB
):
    """
    Fetch telegram messages for a date range, and save the chat histories into subdirectories.

    Parameters:
    - group (str): Name of the group.
    - date_start (datetime): Starting date of the range (timezone-aware in UTC).
    - date_end (datetime): Ending date of the range (timezone-aware in UTC).
    - ini_file (str): Path to the INI file for group info.
    - ini_index (str): The index in the INI file to reference for the username (default is 'tg').
    - max_filtered_filesize (int): Maximum size of filtered messages in bytes.
    """

    # Load the INI file and retrieve the group information
    config = configparser.ConfigParser()
    config.read(ini_file)

    if group not in config:
        raise ValueError(f"Group '{group}' not found in {ini_file}")

    # Fetch the specified ini_index (e.g., 'tg', 'contract_address', etc.) for the group
    username = config[group].get(ini_index)
    if not username:
        raise ValueError(f"'{ini_index}' for group '{group}' not found in {ini_file}")

    async with TelegramClient('session_name', api_id, api_hash) as tg_client:
        print("Telegram client started.")

        current_date = date_start

        while current_date <= date_end:
            print(f"Fetching messages for date: {current_date.strftime('%Y-%m-%d')}")

            message_log_raw, message_log_filtered = await fetch_telegram_messages(
                tg_client,
                group=group,
                username=username,
                date_offset=current_date,
                max_filtered_filesize=max_filtered_filesize,
                n=25
            )

            timestamps = [datetime.strptime(entry['timestamp'], '%Y-%m-%d %H:%M') for entry in message_log_filtered]

            if timestamps:
                date_min = min(timestamps).strftime('%Y-%m-%d_%H-%M')
                date_max = max(timestamps).strftime('%Y-%m-%d_%H-%M')
            else:
                date_min = date_max = current_date.strftime('%Y-%m-%d')

            total_messages_raw = len(message_log_raw)
            total_messages_filtered = len(message_log_filtered)

            all_messages_text_raw = " ".join(entry['text'] for entry in message_log_raw)
            all_messages_text_filtered = " ".join(entry['text'] for entry in message_log_filtered)

            if total_messages_filtered > 4:
                tokens_raw = word_tokenize(all_messages_text_raw)
                total_tokens_raw = len(tokens_raw)

                tokens_filtered = word_tokenize(all_messages_text_filtered)
                total_tokens_filtered = len(tokens_filtered)

                group_dir = os.path.join('tg', group, current_date.strftime('%Y-%m-%d'))
                os.makedirs(group_dir, exist_ok=True)

                nmsg_raw = f"{total_messages_raw}msg"
                ntok_raw = f"{total_tokens_raw//1000}ktok"
                output_filename_raw = f"{group}_raw_{nmsg_raw}_{ntok_raw}_{date_min}_{date_max}.txt"
                output_path_raw = os.path.join(group_dir, output_filename_raw)

                nmsg_filtered = f"{total_messages_filtered}msg"
                ntok_filtered = f"{total_tokens_filtered//1000}ktok"
                output_filename_filtered = f"{group}_filtered_{nmsg_filtered}_{ntok_filtered}_{date_min}_{date_max}.txt"
                output_path_filtered = os.path.join(group_dir, output_filename_filtered)

                def format_message(entry):
                    return f"Date:{entry['timestamp']}\nUsr:@{entry['sender_username']}\nMsg:{entry['text']}\n--\n"

                message_entries_raw = [format_message(entry) for entry in message_log_raw]
                message_entries_filtered = [format_message(entry) for entry in message_log_filtered]

                try:
                    with open(output_path_raw, 'w', encoding='utf-8') as f:
                        f.writelines(message_entries_raw)
                    print(f"Raw Telegram messages saved to '{output_path_raw}'.")
                except Exception as e:
                    print(f"Error writing to '{output_path_raw}': {e}")

                try:
                    with open(output_path_filtered, 'w', encoding='utf-8') as f:
                        f.writelines(message_entries_filtered)
                    print(f"Filtered Telegram messages saved to '{output_path_filtered}'.")
                except Exception as e:
                    print(f"Error writing to '{output_path_filtered}': {e}")

                print("Pausing for 2 seconds...")
                time.sleep(2)

            current_date += timedelta(days=1)
    print("Telegram client disconnected.")

async def fetch_telegram_messages_for_date_range_json(
    group,
    date_start,
    date_end,
    ini_file='coins.ini',
    ini_index='tg',
    max_filtered_filesize=1024 * 1024
):
    """
    Fetch telegram messages for a date range, and save the chat histories in JSON format.

    Parameters:
    - group (str): Name of the group.
    - date_start (datetime): Starting date of the range (timezone-aware in UTC).
    - date_end (datetime): Ending date of the range (timezone-aware in UTC).
    - ini_file (str): Path to the INI file for group info.
    - ini_index (str): The index in the INI file to reference for the username (default is 'tg').
    - max_filtered_filesize (int): Maximum size of filtered messages in bytes.
    """

    # Load the INI file and retrieve the group information
    config = configparser.ConfigParser()
    config.read(ini_file)

    if group not in config:
        raise ValueError(f"Group '{group}' not found in {ini_file}")

    # Fetch the specified ini_index (e.g., 'tg', 'contract_address', etc.) for the group
    username = config[group].get(ini_index)
    if not username:
        raise ValueError(f"'{ini_index}' for group '{group}' not found in {ini_file}")

    async with TelegramClient('session_name', api_id, api_hash) as tg_client:
        print("Telegram client started.")

        current_date = date_start

        while current_date <= date_end:
            print(f"Fetching messages for date: {current_date.strftime('%Y-%m-%d')}")

            # Fetch messages for the current date
            message_log_raw, message_log_filtered = await fetch_telegram_messages(
                tg_client,
                group=group,
                username=username,
                date_offset=current_date,
                max_filtered_filesize=max_filtered_filesize,
                n=25
            )

            # Process timestamps to get date ranges
            timestamps = [datetime.strptime(entry['timestamp'], '%Y-%m-%d %H:%M') for entry in message_log_filtered]

            if timestamps:
                date_min = min(timestamps).strftime('%Y-%m-%d')
            else:
                date_min = current_date.strftime('%Y-%m-%d')

            total_messages_raw = len(message_log_raw)
            total_messages_filtered = len(message_log_filtered)

            if total_messages_filtered > 4:
                # Format raw messages for JSON
                discussions_raw = [
                    {
                        "date": entry['timestamp'],
                        "user": entry['sender_username'],
                        "message": entry['text']
                    }
                    for entry in message_log_raw
                ]

                # Format filtered messages for JSON
                discussions_filtered = [
                    {
                        "date": entry['timestamp'],
                        "user": entry['sender_username'],
                        "message": entry['text']
                    }
                    for entry in message_log_filtered
                ]

                # Create the group directory if it doesn't exist
                group_dir = os.path.join('tg', group, date_min)
                os.makedirs(group_dir, exist_ok=True)

                # Prepare the JSON output filenames, using only date_min (YYYY-MM-DD)
                output_filename_raw = f"{group}_raw_{date_min}.json"
                output_path_raw = os.path.join(group_dir, output_filename_raw)

                output_filename_filtered = f"{group}_filtered_{date_min}.json"
                output_path_filtered = os.path.join(group_dir, output_filename_filtered)

                # Save the raw messages to a JSON file
                try:
                    with open(output_path_raw, 'w', encoding='utf-8') as f:
                        json.dump({"discussions": discussions_raw}, f, indent=4, ensure_ascii=False)
                    print(f"Raw Telegram messages saved to '{output_path_raw}'.")
                except Exception as e:
                    print(f"Error writing to '{output_path_raw}': {e}")

                # Save the filtered messages to a JSON file
                try:
                    with open(output_path_filtered, 'w', encoding='utf-8') as f:
                        json.dump({"discussions": discussions_filtered}, f, indent=4, ensure_ascii=False)
                    print(f"Filtered Telegram messages saved to '{output_path_filtered}'.")
                except Exception as e:
                    print(f"Error writing to '{output_path_filtered}': {e}")

                print("Pausing for 2 seconds...")
                time.sleep(2)

            current_date += timedelta(days=1)

    print("Telegram client disconnected.")

async def fetch_telegram_messages_for_date_range_fill_in_blanks_json(
    group,
    date_start,
    date_end,
    ini_file='coins.ini',
    ini_index='tg',
    max_filtered_filesize=1024 * 1024
):
    """
    Fetch telegram messages for a date range, working backwards in 7-day batches,
    and save the chat histories in JSON format. Skips dates where data already exists,
    and stops if 5 out of 7 days have no new messages.

    Parameters:
    - group (str): Name of the group.
    - date_start (datetime): Starting date of the range (inclusive, timezone-aware in UTC).
    - date_end (datetime): Ending date of the range (inclusive, timezone-aware in UTC).
    - ini_file (str): Path to the INI file for group info.
    - ini_index (str): The index in the INI file to reference for the username (default is 'tg').
    - max_filtered_filesize (int): Maximum size of filtered messages in bytes.
    """

    # Load the INI file and retrieve the group information
    config = configparser.ConfigParser()
    config.read(ini_file)

    if group not in config:
        raise ValueError(f"Group '{group}' not found in {ini_file}")

    # Fetch the specified ini_index (e.g., 'tg', 'contract_address', etc.) for the group
    username = config[group].get(ini_index)
    if not username:
        raise ValueError(f"'{ini_index}' for group '{group}' not found in {ini_file}")

    async with TelegramClient('session_name', api_id, api_hash) as tg_client:
        print("Telegram client started.")

        current_date = date_end  # Start from the end date
        overall_start_date = date_start

        # Variables to track empty days
        consecutive_empty_days = 0

        while current_date >= overall_start_date:
            # Work in 7-day batches
            batch_end_date = current_date
            batch_start_date = max(overall_start_date, current_date - timedelta(days=6))

            print(f"\nProcessing batch from {batch_start_date.strftime('%Y-%m-%d')} to {batch_end_date.strftime('%Y-%m-%d')}")

            # Iterate over each day in the batch
            for day_offset in range((batch_end_date - batch_start_date).days + 1):
                fetch_date = batch_end_date - timedelta(days=day_offset)
                fetch_date_str = fetch_date.strftime('%Y-%m-%d')
                print(f"\nFetching messages for date: {fetch_date_str}")

                # Check if data for this date already exists
                group_dir = os.path.join('tg', group, fetch_date_str)
                if os.path.exists(group_dir) and os.listdir(group_dir):
                    print(f"Data for {fetch_date_str} already exists and is not empty. Skipping.")
                    continue

                # Fetch messages for the current date
                message_log_raw, message_log_filtered = await fetch_telegram_messages(
                    tg_client,
                    group=group,
                    username=username,
                    date_offset=fetch_date,
                    max_filtered_filesize=max_filtered_filesize,
                    n=25
                )

                total_messages_filtered = len(message_log_filtered)

                if total_messages_filtered > 0:
                    consecutive_empty_days = 0  # Reset consecutive empty days

                    # Format raw messages for JSON
                    discussions_raw = [
                        {
                            "date": entry['timestamp'],
                            "user": entry['sender_username'],
                            "message": entry['text']
                        }
                        for entry in message_log_raw
                    ]

                    # Format filtered messages for JSON
                    discussions_filtered = [
                        {
                            "date": entry['timestamp'],
                            "user": entry['sender_username'],
                            "message": entry['text']
                        }
                        for entry in message_log_filtered
                    ]

                    # Create the group directory if it doesn't exist
                    os.makedirs(group_dir, exist_ok=True)

                    # Prepare the JSON output filenames
                    output_filename_raw = f"{group}_raw_{fetch_date_str}.json"
                    output_path_raw = os.path.join(group_dir, output_filename_raw)

                    output_filename_filtered = f"{group}_filtered_{fetch_date_str}.json"
                    output_path_filtered = os.path.join(group_dir, output_filename_filtered)

                    # Save the raw messages to a JSON file
                    try:
                        with open(output_path_raw, 'w', encoding='utf-8') as f:
                            json.dump({"discussions": discussions_raw}, f, indent=4, ensure_ascii=False)
                        print(f"Raw Telegram messages saved to '{output_path_raw}'.")
                    except Exception as e:
                        print(f"Error writing to '{output_path_raw}': {e}")

                    # Save the filtered messages to a JSON file
                    try:
                        with open(output_path_filtered, 'w', encoding='utf-8') as f:
                            json.dump({"discussions": discussions_filtered}, f, indent=4, ensure_ascii=False)
                        print(f"Filtered Telegram messages saved to '{output_path_filtered}'.")
                    except Exception as e:
                        print(f"Error writing to '{output_path_filtered}': {e}")

                    print("Pausing for 2 seconds...")
                    await asyncio.sleep(2)
                else:
                    print(f"No new messages found for {fetch_date_str}.")
                    consecutive_empty_days += 1

                # Check if we've hit 5 empty days out of the last 7
                if consecutive_empty_days >= 5:
                    print(f"\nReached {consecutive_empty_days} consecutive empty days. Assuming beginning of chat logs. Ending execution.")
                    return

            # Move to the next batch
            current_date = batch_start_date - timedelta(days=1)

        print("Finished processing all batches.")
    print("Telegram client disconnected.")

def normalize_username(username):
    # Remove leading special characters like '!', '@', '#', etc.
    return username.lstrip('!@#')

def check_spam_with_openai(messages,llm_model):
    """
    Identify spam users from a list of messages using OpenAI.

    Parameters:
    - messages: List of dictionaries containing 'message' and 'sender_username'.

    Returns:
    - ignore_list: List of usernames identified as spam.
    """
    print("Starting spam check with OpenAI...")

    # Read the prompt from prompt_spam.ini
    try:
        with open('prompt_spam.ini', 'r', encoding='utf-8') as file:
            spam_prompt_template = file.read()
        #print("Loaded prompt_spam.ini successfully.")
    except Exception as e:
        print(f"Error loading 'prompt_spam.ini': {e}")
        return []

    message_log_text = ''
    for entry in messages:
        message_log_text += f"Usr:@{entry['sender_username']}\nMsg:{entry['message']}\n--\n"

    final_prompt = prompt_template.replace('{message_log}', message_log_text)

    # Prepare the final prompt
    final_prompt = spam_prompt_template.replace('{message_log}', message_log_text)
    print("Prepared the final prompt for OpenAI API.")

    # Call the OpenAI API
    try:
        print("Sending spam check request to OpenAI API...")
        response = client.beta.chat.completions.parse(
            model=llm_model,
            messages=[{'role': 'user', 'content': final_prompt}],
            max_tokens=500
        )
        print("Received response from OpenAI API.")
    except Exception as e:
        print(f"OpenAI API Error during spam check: {e}")
        return []

    # Extract the assistant's response
    ai_response = response.choices[0].message.content.strip()

    # Transform the AI response into a list of usernames
    try:
        if ai_response.strip():
            ignore_list = [
                username.strip().lstrip('@')
                for username in ai_response.split(',')
                if username.strip()
                ]
        else:
            ignore_list = []
        print(f"Spam users identified: {ignore_list}")
        return ignore_list
    except Exception as e:
        print(f"Error processing AI response: {e}")
        print("Raw AI Response:")
        print(ai_response)
        return []

def analyze_messages_with_openai(input_file, output_file, llm_model):
    """Read messages from a file, trim content to be under a specified size, send to OpenAI API, and save the response.

    Parameters:
    - input_file (str): Path to the input text file containing messages.
    - output_file (str): Path to the output file where the response will be saved.
    - llm_model (str): The OpenAI model to use.
    """
    max_token_limit = 110000  # Set the maximum token limit

    print("Starting analyze_messages_with_openai function.")
    # Read the initialization prompt from prompt.ini
    # NOTE: the meat of the prompt is contained in the structured output prompt.py document
    try:
        with open('prompt.ini', 'r', encoding='utf-8') as file:
            prompt_template = file.read()
        print("Loaded prompt.ini successfully.")
    except Exception as e:
        print(f"Error loading prompt.ini: {e}")
        exit(1)
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            message_log_text = f.read()
        print(f"Loaded '{input_file}' successfully.")
    except Exception as e:
        print(f"Error reading '{input_file}': {e}")
        return

    # Parse message_log_text into message_log_data
    try:
        message_log_data = json.loads(message_log_text)
        # Access the 'discussions' list
        discussions = message_log_data.get('discussions', [])
        n_messages = len(discussions)
        print(f"Total number of messages: {n_messages}")
    except Exception as e:
        print(f"Error parsing '{input_file}': {e}")
        return

    # Get the encoding for the model
    try:
        encoding = tiktoken.encoding_for_model(llm_model)
    except Exception as e:
        print(f"Error getting encoding for model '{llm_model}': {e}")
        return

    # Calculate the number of tokens in message_log_text
    token_length = len(encoding.encode(message_log_text))
    print(f"Total token size for message_log_text: {token_length}")

    # Check if trimming is needed
    if token_length > max_token_limit:
        # Calculate the proportion to keep
        proportion_to_keep = max_token_limit / token_length
        n_messages_to_keep = int(n_messages * proportion_to_keep)
        print(f"Token length exceeds {max_token_limit}. Trimming messages to first {n_messages_to_keep} messages.")

        # Trim 'discussions' list
        discussions = discussions[:n_messages_to_keep]
        message_log_data['discussions'] = discussions

        # Reconstruct message_log_text
        message_log_text = json.dumps(message_log_data, ensure_ascii=False)

        # Recalculate token_length
        token_length = len(encoding.encode(message_log_text))
        print(f"New total token size after trimming: {token_length}")
    else:
        print("No trimming needed.")

    # Proceed to call the OpenAI API
    try:
        print("Sending request to OpenAI API...")
        response = client.beta.chat.completions.parse(
            model=llm_model,
            messages=[
                {'role': 'system', 'content': prompt_template},
                {'role': 'user', 'content': message_log_text}],
                response_format=ChatLogAnalysisResponse
        )
        print("Received response from OpenAI API.")
    except Exception as e: 
        print(f"OpenAI API Error: {e}")
        return

    # Extract the assistant's response
    ai_response = response.choices[0].message.content.strip()

    # Attempt to parse the response as JSON
    try:
        response_data = json.loads(ai_response)
        # Validate against the Pydantic model
        metrics = ChatLogAnalysisResponse(**response_data)
        print("Successfully parsed and validated the AI response.")
    except Exception as e:
        print(f"Error parsing or validating the AI response: {e}")
        print("Raw AI Response:")
        print(ai_response)
        return

    # Perform some additional processing with non-LLM analysis
    try:
        # discussions variable is already available from earlier
        additional_metrics = extract_metadata_socials_and_user_stats(discussions)
        
        # Convert the Pydantic model to a dictionary for easier manipulation
        metrics_dict = metrics.dict()

        # Append the results to the existing OpenAI output under "metrics"
        if "metrics" not in metrics_dict:
            metrics_dict["metrics"] = {}

        metrics_dict["metrics"].update(additional_metrics)

    except Exception as e:
        print(f"Error processing additional metrics: {e}")

    # Save the structured response to a JSON file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(metrics_dict, f, indent=4, ensure_ascii=False)
        print(f"OpenAI response saved to '{output_file}'.")
    except Exception as e:
        print(f"Error writing to '{output_file}': {e}")

    # Optionally, display the response
    print("\n--- OpenAI GPT-4 Response ---\n")
    
    try:
        print(json.dumps(metrics_dict, indent=4, ensure_ascii=False))
    except json.JSONDecodeError:
        # If the response is not valid JSON, print as raw text
        print(ai_response)

def process_chat_logs(project_name, date_min, date_max,model=openai_version):
    """
    Process chat logs by calling analyze_messages_with_openai() for each date in the date range.

    Parameters:
    - project_name (str): The name of the project.
    - date_min (str): The start date in 'YYYY-MM-DD' format.
    - date_max (str): The end date in 'YYYY-MM-DD' format.
    """
    # Parse the date strings
    date_start = datetime.strptime(date_min, '%Y-%m-%d')
    date_end = datetime.strptime(date_max, '%Y-%m-%d')

    # For each date in the range
    current_date = date_start
    while current_date <= date_end:
        date_str = current_date.strftime('%Y-%m-%d')
        directory = os.path.join('tg',project_name, date_str)

        if os.path.exists(directory):
            # List files in the directory
            files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

            # Filter files that have 'filtered' in the filename, end with '.json', and do not contain 'llm=' or 'prompt='
            # Do this to not accidentially select a post-processed file as our LLM target. 
            filtered_files = [f for f in files if 'filtered' in f and f.endswith('.json') and 'llm=' not in f and 'prompt=' not in f]

            if filtered_files:
                # If duplicates exist, use the one with the latest modification time
                files_with_mtime = []
                for f in filtered_files:
                    file_path = os.path.join(directory, f)
                    mtime = os.path.getmtime(file_path)
                    files_with_mtime.append((file_path, mtime))

                # Sort files by modification time, latest first
                files_with_mtime.sort(key=lambda x: x[1], reverse=True)

                # Select the latest file
                input_file = files_with_mtime[0][0]

                # Prepare the output file path
                output_directory = os.path.join(project_name)
                if not os.path.exists(output_directory):
                    os.makedirs(output_directory)

                output_file = os.path.join('tg',output_directory,date_str, f"{project_name}_filtered_{date_str}_llm={model}_prompt={__version__}.json")

                # Call analyze_messages_with_openai()
                analyze_messages_with_openai(input_file=input_file, output_file=output_file, llm_model=model)

            else:
                print(f"No filtered text files found in directory {directory}")
        else:
            print(f"Directory {directory} does not exist")

        # Move to the next date
        current_date += timedelta(days=1)

def rollup_project_data(project_name, ll_name, prompt_version):
    """
    Roll up data from JSON files in date-based folders into a central rollup JSON.

    Parameters:
    - project_name (str): The name of the project.
    - llm_name (str): Name of model (ie, gpt-4o-mini) 
    - prompt_version (str): prompt version (ie, 1.0.5)

    The function creates a rollup JSON file named '<project_name>_rollup.json' in the root project folder.
    """

    project_dir = os.path.join('tg', project_name)
    rollup_data = {
        "project_name": project_name,
        "date_data": {}
    }

    if not os.path.exists(project_dir):
        print(f"Project directory '{project_dir}' does not exist.")
        return

    # List all subdirectories in the project directory
    subdirs = [d for d in os.listdir(project_dir) if os.path.isdir(os.path.join(project_dir, d))]
    # Filter subdirectories that match the date format 'YYYY-MM-DD'
    date_dirs = [d for d in subdirs if is_valid_date(d)]

    if not date_dirs:
        print(f"No date directories found in '{project_dir}'.")
        return

    for date_dir in sorted(date_dirs):
        date_path = os.path.join(project_dir, date_dir)
        # Construct the expected JSON filename
        json_filename = f"{project_name}_filtered_{date_dir}_llm={ll_name}_prompt={prompt_version}.json"
        json_filepath = os.path.join(date_path, json_filename)

        if os.path.exists(json_filepath):
            try:
                with open(json_filepath, 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)
                print(f"Loaded data from '{json_filepath}'.")

                # Extract required data
                emotional_metrics = data.get("metrics", {})

                # Add data to rollup_data
                rollup_data["date_data"][date_dir] = {
                    "metrics": emotional_metrics
                }

            except Exception as e:
                print(f"Error processing '{json_filepath}': {e}")
        else:
            print(f"JSON file '{json_filepath}' does not exist.")

    # Save the rollup_data to a JSON file in the root project folder
    output_filepath = os.path.join(project_dir, f"{project_name}_llm={ll_name}_prompt={prompt_version}_rollup.json")
    try:
        with open(output_filepath, 'w', encoding='utf-8') as outfile:
            json.dump(rollup_data, outfile, indent=4)
        print(f"Rollup data saved to '{output_filepath}'.")
    except Exception as e:
        print(f"Error writing rollup data to '{output_filepath}': {e}")

def is_valid_date(date_str):
    """Check if a string is a valid date in 'YYYY-MM-DD' format."""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

async def check_telegram_activity(
    groupname,
    ini_file='coins.ini',
    ini_index='tg',
    n=25  # For logging every nth message
):
    """
    Check if a Telegram group is active based on the number of non-bot messages in the last 3 days.

    Parameters:
    - groupname (str): The name of the group as specified in the coins.ini file.
    - ini_file (str): The path to the ini file (default is 'coins.ini').
    - ini_index (str): The field in the ini file to use for the username (default is 'tg').
    - n (int): Print metadata every nth message.

    Returns:
    - bool: True if the group is active, False otherwise.
    """

    # Load the INI file and retrieve the group information
    config = configparser.ConfigParser()
    config.read(ini_file)

    if groupname not in config:
        print(f"Group '{groupname}' not found in {ini_file}")
        return False

    # Fetch the 'tg' field for the group
    tg_address = config[groupname].get(ini_index)
    if not tg_address:
        print(f"'{ini_index}' (Telegram address) for group '{groupname}' not found in {ini_file}")
        return False

    # Extract the username from the tg_address
    # Assuming the tg_address is in the format 'https://t.me/username'
    if 't.me/' in tg_address:
        username = tg_address.split('t.me/')[-1].strip('/')
    else:
        username = tg_address.strip('/')

    # Initialize the Telegram client within an async context manager
    async with TelegramClient('session_name', api_id, api_hash) as tg_client:
        print("Telegram client started.")

        try:
            # Get the entity for the group
            channel = await tg_client.get_entity(username)
            print(f"Successfully obtained entity for {username}")
        except Exception as e:
            print(f"Error getting Telegram entity for '{username}': {e}")
            return False

        # Calculate the date range: last 3 days starting from yesterday
        today = datetime.now(timezone.utc).date()
        start_date = today - timedelta(days=4)
        end_date = today - timedelta(days=2)

        # Initialize counters
        non_bot_messages = 0
        total_messages_fetched = 0

        # Set date boundaries
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_datetime = datetime.combine(end_date + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc)

        print(f"Retrieving messages from {start_datetime} until {end_datetime}...")

        try:
            async for message in tg_client.iter_messages(
                channel,
                reverse=True,
                offset_date=end_datetime,
                limit=50
            ):
                message_date = message.date.astimezone(timezone.utc)

                if message_date < start_datetime:
                    continue  # Skip messages outside the date range

                total_messages_fetched += 1

                # Check if the sender is a bot
                sender = await message.get_sender()
                is_bot = isinstance(sender, User) and sender.bot

                if not is_bot:
                    non_bot_messages += 1

                # Every nth message, print out some metadata
                if total_messages_fetched % n == 0:
                    sender_username = sender.username if sender.username else f"id_{sender.id}"
                    print(f"Pulling message #{total_messages_fetched}, date={message_date}, user={sender_username}")

                # If we have fetched 100 messages, break
                if total_messages_fetched >= 100:
                    break

            # Determine if the group is active
            is_active = non_bot_messages > 5

            # Update the coins.ini file
            config[groupname]['tg_healthy'] = str(is_active)
            with open(ini_file, 'w') as configfile:
                config.write(configfile)

            print(f"Group '{groupname}' is {'healthy' if is_active else 'not healthy (Safeguard?)'}.")
            print(f"Non-bot messages are above 'healthy' threshold in a 3 day window: {non_bot_messages}")

            return is_active

        except FloodWaitError as e:
            print(f"FloodWaitError: Telegram is asking you to wait for {e.seconds} seconds.")
            # Handle flood wait as appropriate (e.g., wait or skip)

            return False

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return False

async def check_telegram_activity_loop():
    # Loop through all coins.ini entries and check health status. Assign True, False or skip. 
    # Load the INI file
    config = configparser.ConfigParser()
    config.read('coins.ini')

    # Iterate over each section (group) in the INI file
    for groupname in config.sections():
        group = config[groupname]
        tg_health = group.get('tg_healthy')
        tg = group.get('tg')

        # Check if 'tg_healthy' is unassigned and 'tg' is not blank
        if (tg_health is None or tg_health.strip() == '') and tg and tg.strip() != '':
            print(f"\nChecking Telegram activity for group '{groupname}'...")
            # Call check_telegram_activity() and await its completion
            await check_telegram_activity(groupname)
            print("Pausing...")
            time.sleep(5)
        else:
            print(f"\nSkipping group '{groupname}': 'tg_healthy' is assigned or 'tg' is blank.")

def analyze_coins_ini(ini_file='coins.ini'):
    """
    Analyzes the coins.ini file to count entries based on the 'tg_healthy' field
    and outputs a list of entries where 'tg_healthy' is 'True'.

    Parameters:
    - ini_file (str): The path to the ini file (default is 'coins.ini').
    """
    config = configparser.ConfigParser()
    config.read(ini_file)

    true_count = 0
    false_count = 0
    undefined_count = 0
    true_entries = []

    for section in config.sections():
        tg_healthy = config[section].get('tg_healthy')

        if tg_healthy is None:
            undefined_count += 1
        elif tg_healthy.strip().lower() == 'true':
            true_count += 1
            true_entries.append(section)
        elif tg_healthy.strip().lower() == 'false':
            false_count += 1
        else:
            undefined_count += 1  # Handle unexpected values as undefined

    total_entries = len(config.sections())

    print(f"Total entries in '{ini_file}': {total_entries}")
    print(f"Entries with 'tg_healthy = True': {true_count}")
    print(f"Entries with 'tg_healthy = False': {false_count}")
    print(f"Entries with 'tg_healthy' undefined or invalid: {undefined_count}")

    if true_entries:
        print("\nList of entries where 'tg_healthy = True':")
        for entry in true_entries:
            print(f"- {entry}")
    else:
        print("\nNo entries found where 'tg_healthy = True'.")

if __name__ == '__main__':

    # Create the Telegram client and load environmental variables
    # tg_client = TelegramClient('session_name', api_id, api_hash)
    # print(tg_client)
    ############################
    # Main tg loop
    ############################
    
    # asyncio.run(check_telegram_activity(group_name))    
    # asyncio.run(check_telegram_activity_loop())
    # analyze_coins_ini()
    # max_filtered_filesize = 1024 * 1024  # 150 KB

    date_start = datetime(2024, 11, 2, tzinfo=timezone.utc)
    date_end = datetime(2024, 11, 7, tzinfo=timezone.utc)

    dir_list1 = ['habibi-sol','wawa-cat','whiskey','spx6900','retardio','analos']
    dir_list1 = ['shoggoth','maga-again','asteroid-shiba','dinolfg','k9-finance-dao','pollen','lookbro']
    dir_list2 = ['pepe-trump','fairfun','poupe','hoge-finance','jesus-coin','samoyedcoin','goat','osaka-protocol','misha','inferno-2','sigma','catwifhat-2','cafe','hund','pundu','zyn','4trump','michi','orc','lfgo','max2049','lol-3','remilia','venko']
    dir_list3 = ['cheese-2','mellow-man','dogwifcoin','brainrot']
    
    # dir_list_batch1 = ['habibi-sol','wawa-cat','whiskey','spx6900','retardio']
    # dir_list_batch2 = ['analos','shoggoth','maga-again','asteroid-shiba','dinolfg']
    # dir_list_batch3 = ['k9-finance-dao','lookbro','pepe-trump','fairfun']
    # dir_list_batch4 = ['poupe','hoge-finance','jesus-coin','samoyedcoin','goat']
    # dir_list_batch5 = ['osaka-protocol','misha','inferno-2','sigma','catwifhat-2']
    # dir_list_batch6 = ['cafe','hund','pundu','4trump','michi','orc','lfgo']
    # dir_list_batch7 = ['lol-3','remilia','venko','cheese-2','mellow-man','dogwifcoin']

    for group_name in dir_list3:

        # Run the fetching function within the event loop
        # asyncio.run(fetch_telegram_messages_for_date_range_fill_in_blanks_json(
        #     group=group_name,
        #     date_start=date_start,
        #     date_end=date_end
        # ))
        #process_chat_logs(group_name, date_min='2024-11-2', date_max='2024-11-7', model=openai_version)
        #rollup_project_data(group_name, 'gpt-4o-mini', __version__)
        fetch_price_data(group_name)

    # group_name = 'nailong'
    
    # asyncio.run(fetch_telegram_messages_for_date_range_fill_in_blanks_json(
    #     group=group_name,
    #     date_start=date_start,
    #     date_end=date_end
    # ))
    print("Finished fetching Telegram messages.")
  

    ############################
    # Main LLM process loop
    ############################
    #Now run the OpenAI analysi

    # batch process
    #process_chat_logs('brainrot', date_min='2024-1-1', date_max='2024-11-1', model=openai_version)

    ############################
    # Roll it up n smoke it
    ############################
    
    #combine it all 
    #rollup_project_data('brainrot', 'gpt-4o-mini', '1.0.5')
    