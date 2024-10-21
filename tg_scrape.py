from telethon import TelegramClient
from telethon.utils import get_display_name
from datetime import datetime
import asyncio
from openai import OpenAI
import os
from dotenv import load_dotenv
from prompt import ChatLogAnalysisResponse, CommunityMetrics
import nltk
nltk.download('punkt')  # Download the tokenizer data
from nltk.tokenize import word_tokenize
import json
from datetime import timezone
import time



load_dotenv()
print("Loaded environment variables.")

# Retrieve environment variables
try:
    api_id = int(os.getenv('TELEGRAM_API_ID'))
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE')
    openai_api_key = os.getenv('OPENAI_API_KEY')

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

from datetime import datetime, timedelta

async def fetch_telegram_messages(
    tg_client,
    group,
    username,
    date_offset,
    max_filtered_filesize=150 * 1024  # Default to 150 KB
):
    """
    Fetch text messages from a Telegram group starting from a specific date until constraints are met.

    Parameters:
    - tg_client: The TelegramClient instance to use.
    - group (str): Name of the group.
    - username (str): Telegram group username or link.
    - date_offset (datetime): The date from which to start fetching messages.
    - max_filtered_filesize (int): Maximum size of filtered messages in bytes.

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

    # Set date boundaries
    start_date = date_offset
    end_date = start_date + timedelta(days=1)

    print(f"Retrieving messages starting from {start_date} until {end_date}...")

    async for message in tg_client.iter_messages(channel, reverse=False, offset_date=start_date):
        message_date = message.date
        if message_date >= end_date:
            print("Reached the end of the day.")
            break

        total_messages += 1  # Track total number of messages fetched

        if message.message:
            sender = await message.get_sender()
            sender_username = sender.username if sender.username else f"id_{sender.id}"

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
            if sender.bot:
                continue  # Skip bots in filtered output
            if previous_message_text is not None and text == previous_message_text:
                continue  # Skip duplicate messages in filtered output

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
                break

    print(f"Total messages fetched: {total_messages}")
    print(f"Messages after filtering: {len(message_log_filtered)}")

    return message_log_raw, message_log_filtered

async def fetch_telegram_messages_for_date_range(
    group,
    username,
    date_start,
    date_end,
    max_filtered_filesize=150 * 1024  # Default to 150 KB
):
    """
    Fetch telegram messages for a date range, and save the chat histories into subdirectories.

    Parameters:
    - group (str): Name of the group.
    - username (str): Telegram group username or link.
    - date_start (datetime): Starting date of the range (timezone-aware in UTC).
    - date_end (datetime): Ending date of the range (timezone-aware in UTC).
    - max_filtered_filesize (int): Maximum size of filtered messages in bytes.
    """
    # Create the Telegram client once
    async with TelegramClient('session_name', api_id, api_hash) as tg_client:
        print("Telegram client started.")

        current_date = date_start

        while current_date <= date_end:
            print(f"Fetching messages for date: {current_date.strftime('%Y-%m-%d')}")

            # Fetch messages for the current date
            message_log_raw, message_log_filtered = await fetch_telegram_messages(
                tg_client,  # Pass the client
                group=group,
                username=username,
                date_offset=current_date,
                max_filtered_filesize=max_filtered_filesize
                )

            # Create directories and manage files
            # Create the group directory if it doesn't exist
            group_dir = os.path.join('tg', group, current_date.strftime('%Y-%m-%d'))
            os.makedirs(group_dir, exist_ok=True)

            # Process timestamps to get date ranges
            timestamps = [datetime.strptime(entry['timestamp'], '%Y-%m-%d %H:%M') for entry in message_log_filtered]

            if timestamps:
                date_min = min(timestamps).strftime('%Y-%m-%d_%H-%M')
                date_max = max(timestamps).strftime('%Y-%m-%d_%H-%M')
            else:
                date_min = date_max = current_date.strftime('%Y-%m-%d')

            # Calculate total messages and tokens for raw and filtered logs
            total_messages_raw = len(message_log_raw)
            total_messages_filtered = len(message_log_filtered)

            all_messages_text_raw = " ".join(entry['text'] for entry in message_log_raw)
            all_messages_text_filtered = " ".join(entry['text'] for entry in message_log_filtered)

            tokens_raw = word_tokenize(all_messages_text_raw)
            total_tokens_raw = len(tokens_raw)

            tokens_filtered = word_tokenize(all_messages_text_filtered)
            total_tokens_filtered = len(tokens_filtered)

            # Prepare file names
            nmsg_raw = f"{total_messages_raw}msg"
            ntok_raw = f"{total_tokens_raw//1000}ktok"
            output_filename_raw = f"{group}_raw_{nmsg_raw}_{ntok_raw}_{date_min}_{date_max}.txt"
            output_path_raw = os.path.join(group_dir, output_filename_raw)

            nmsg_filtered = f"{total_messages_filtered}msg"
            ntok_filtered = f"{total_tokens_filtered//1000}ktok"
            output_filename_filtered = f"{group}_filtered_{nmsg_filtered}_{ntok_filtered}_{date_min}_{date_max}.txt"
            output_path_filtered = os.path.join(group_dir, output_filename_filtered)

            # Format messages for writing
            def format_message(entry):
                return f"Date:{entry['timestamp']}\nUsr:@{entry['sender_username']}\nMsg:{entry['text']}\n--\n"

            message_entries_raw = [format_message(entry) for entry in message_log_raw]
            message_entries_filtered = [format_message(entry) for entry in message_log_filtered]

            # Save the raw message log to a file
            try:
                with open(output_path_raw, 'w', encoding='utf-8') as f:
                    f.writelines(message_entries_raw)
                print(f"Raw Telegram messages saved to '{output_path_raw}'.")
            except Exception as e:
                print(f"Error writing to '{output_path_raw}': {e}")

            # Save the filtered message log to a file
            try:
                with open(output_path_filtered, 'w', encoding='utf-8') as f:
                    f.writelines(message_entries_filtered)
                print(f"Filtered Telegram messages saved to '{output_path_filtered}'.")
            except Exception as e:
                print(f"Error writing to '{output_path_filtered}': {e}")

            # Pause for 10 seconds to avoid hitting throttle limits
            if (total_messages_filtered > 5):
                print("Pausing for 5 seconds...")
                time.sleep(5)

            # Move to the next day (ensure current_date remains timezone-aware)
            current_date += timedelta(days=1)
    print("Telegram client disconnected.")


def normalize_username(username):
    # Remove leading special characters like '!', '@', '#', etc.
    return username.lstrip('!@#')

def check_spam_with_openai(messages):
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
            model='gpt-4o-mini',
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


def analyze_messages_with_openai(input_file='telegram_messages.txt', output_file='openai_response.txt'):
    """Read messages from a file, send to OpenAI API, and save the response."""
    
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
    
    # Read the message log from the file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            message_log_text = f.read()
        print(f"Loaded '{input_file}' successfully.")
    except Exception as e:
        print(f"Error reading '{input_file}': {e}")
        return

    # Prepare the final prompt
    final_prompt = prompt_template.replace('{message_log}', message_log_text)
    print("Prepared the final prompt for OpenAI API.")

    # Call the OpenAI API
    try:
        print("Sending request to OpenAI API...")
        response = client.beta.chat.completions.parse(
            model='gpt-4o-mini',
            messages=[{
                'role': 'user', 
                'content': final_prompt}],
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

    # Save the structured response to a JSON file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(metrics.model_dump_json(indent=4))
        print(f"OpenAI response saved to '{output_file}'.")
    except Exception as e:
        print(f"Error writing to '{output_file}': {e}")

    # Optionally, display the response
    print("\n--- OpenAI GPT-4 Response ---\n")
    
    try:
        print(json.dumps(json.loads(ai_response), indent=4))
    except json.JSONDecodeError:
        # If the response is not valid JSON, print as raw text
        print(ai_response)

if __name__ == '__main__':

    # Create the Telegram client and load environmental variables
    tg_client = TelegramClient('session_name', api_id, api_hash)

    ############################
    # Main tg loop
    ############################
    group_name = 'pollen'
    #username = 'https://t.me/+F37V2KpUcJZmMDFh'  # Replace with actual username or link
    #username='https://t.me/XNETgossip',  #xnet  
    #username='https://t.me/max2049cto' #max2049
    username='@pollenfuture2023' #pollenfuture (case study in rug pull sentiment)
    date_start = datetime(2022, 12, 1, tzinfo=timezone.utc)
    date_end = datetime(2023, 5, 1, tzinfo=timezone.utc)
    max_filtered_filesize = 500 * 1024  # 150 KB

    # Run the fetching function within the event loop
    asyncio.run(fetch_telegram_messages_for_date_range(
        group=group_name,
        username=username,
        date_start=date_start,
        date_end=date_end,
        max_filtered_filesize=max_filtered_filesize
    ))

    print("Finished fetching Telegram messages.")



    ############################
    # Main LLM process loop
    ############################
    #Now run the OpenAI analysis
    # analyze_messages_with_openai(
    #     input_file='tg/spx6900/spx6900_raw_2000msg_14ktok_2024-10-20_00-21_2024-10-20_21-13.txt',
    #     output_file='openai_response_debug.json'
    # )
    # print("Script finished.")
