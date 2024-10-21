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
    username,
    date_start,
    date_end,
    max_filtered_filesize=1024 * 1024  # Default to 150 KB
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
                max_filtered_filesize=max_filtered_filesize,
                n=25
                )

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

            # Insure the day has chat in it before making directories and saving
            if (total_messages_filtered > 4):

                tokens_raw = word_tokenize(all_messages_text_raw)
                total_tokens_raw = len(tokens_raw)

                tokens_filtered = word_tokenize(all_messages_text_filtered)
                total_tokens_filtered = len(tokens_filtered)

                # Create the group directory if it doesn't exist
                group_dir = os.path.join('tg', group, current_date.strftime('%Y-%m-%d'))
                os.makedirs(group_dir, exist_ok=True)
                

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

                # Pause for 2 seconds to avoid hitting throttle limits
                
                print("Pausing for 2 seconds...")
                time.sleep(2)

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
    """Read messages from a file, trim content to be under a specified size, send to OpenAI API, and save the response.

    Parameters:
    - input_file (str): Path to the input text file containing messages.
    - output_file (str): Path to the output file where the response will be saved.
    """
    max_input_size=250 * 1024

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

    # Prepare the final prompt by inserting the message_log_text into the prompt_template
    final_prompt = prompt_template.replace('{message_log}', message_log_text)
    final_prompt_size = len(final_prompt.encode('utf-8'))

    if final_prompt_size > max_input_size:
        print(f"Final prompt exceeds the maximum allowed size of {max_input_size} bytes. Trimming the message log.")
        # Compute the size of the prompt without the message log
        prompt_without_log = prompt_template.replace('{message_log}', '')
        prompt_without_log_size = len(prompt_without_log.encode('utf-8'))
        # Calculate the maximum allowed size for the message log
        max_log_size = max_input_size - prompt_without_log_size
        if max_log_size <= 0:
            print("The prompt without the message log exceeds the maximum input size.")
            return

        # Encode the message log to bytes
        message_log_bytes = message_log_text.encode('utf-8')
        # Trim the message log from the end to fit within max_log_size
        message_log_bytes = message_log_bytes[:max_log_size]
        # Find the last complete message (ensure we don't cut in the middle)
        last_newline = message_log_bytes.rfind(b'\n')
        if last_newline != -1:
            message_log_bytes = message_log_bytes[:last_newline]
        else:
            # If there's no newline, we might be in the middle of a message
            print("No newline character found; the message may be incomplete.")
            # Optionally, you can choose to proceed or return
            # return
        # Decode back to string
        message_log_text = message_log_bytes.decode('utf-8', errors='ignore')
        # Reconstruct the final prompt with the trimmed message log
        final_prompt = prompt_template.replace('{message_log}', message_log_text)
        final_prompt_size = len(final_prompt.encode('utf-8'))
        print(f"Trimmed message log to {len(message_log_bytes)} bytes. Final prompt size is {final_prompt_size} bytes.")
    else:
        print("Final prompt is within the size limit.")

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

def process_chat_logs(project_name, date_min, date_max):
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

            # Filter files that have 'filtered' in the filename and end with '.txt'
            filtered_files = [f for f in files if 'filtered' in f and f.endswith('.txt')]

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

                output_file = os.path.join('tg',output_directory,date_str, f"{project_name}_filtered_{date_str}.json")

                # Call analyze_messages_with_openai()
                analyze_messages_with_openai(input_file=input_file, output_file=output_file)
            else:
                print(f"No filtered text files found in directory {directory}")
        else:
            print(f"Directory {directory} does not exist")

        # Move to the next date
        current_date += timedelta(days=1)

def rollup_project_data(project_name):
    """
    Roll up data from JSON files in date-based folders into a central rollup JSON.

    Parameters:
    - project_name (str): The name of the project.

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
        json_filename = f"{project_name}_filtered_{date_dir}.json"
        json_filepath = os.path.join(date_path, json_filename)

        if os.path.exists(json_filepath):
            try:
                with open(json_filepath, 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)
                print(f"Loaded data from '{json_filepath}'.")

                # Extract required data
                metrics = data.get("metrics", {})
                message_metrics = metrics.get("message", {})
                emotional_metrics = metrics.get("emotional_metrics", {})

                # Get 'message_count_ex_bot' and 'user_count_ex_bot'
                message_count_ex_bot = message_metrics.get("message_count_ex_bot", 0)
                user_count_ex_bot = message_metrics.get("user_count_ex_bot", 0)

                # Add data to rollup_data
                rollup_data["date_data"][date_dir] = {
                    "message_count_ex_bot": message_count_ex_bot,
                    "user_count_ex_bot": user_count_ex_bot,
                    "emotional_metrics": emotional_metrics
                }

            except Exception as e:
                print(f"Error processing '{json_filepath}': {e}")
        else:
            print(f"JSON file '{json_filepath}' does not exist.")

    # Save the rollup_data to a JSON file in the root project folder
    output_filepath = os.path.join(project_dir, f"{project_name}_rollup.json")
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



if __name__ == '__main__':

    # Create the Telegram client and load environmental variables
    tg_client = TelegramClient('session_name', api_id, api_hash)

    ############################
    # Main tg loop
    ############################
    group_name = 'spx6900'
    #username = 'https://t.me/+F37V2KpUcJZmMDFh'  #spx6900
    #username = 'https://t.me/ZynCoinERC20_Zynm' #zyn - real or fake channel? idk
    #username = 'https://t.me/billy_cto_sol' #billy coin - prob need the invite link to work
    #username = 'https://t.me/michicoinsolana' #michi
    #username = 'https://t.me/retardiosol' #retardio
    #username = 'https://t.me/SIGMAonsolportal' #sigma - DOESNT WORK
    #username = 'https://t.me/+YmwhVSPoX_84ZGYy'#priv sigma invite link
    #username = 'https://t.me/POPCATSOLANA'#apu
    #username='https://t.me/XNETgossip',  #xnet  
    #username='https://t.me/max2049cto' #max2049
    #username='https://t.me/GoatseusMaximusSolana'
    #username='@pollenfuture2023' #pollenfuture (case study in rug pull sentiment)
    #username='Pollen Gossip' #pollenfuture (case study in rug pull sentiment)
    date_start = datetime(2024, 10, 11, tzinfo=timezone.utc)
    date_end = datetime(2024, 10, 11, tzinfo=timezone.utc)
    max_filtered_filesize = 1024 * 1024  # 150 KB

    # Run the fetching function within the event loop
    # asyncio.run(fetch_telegram_messages_for_date_range(
    #     group=group_name,
    #     username=username,
    #     date_start=date_start,
    #     date_end=date_end,
    #     max_filtered_filesize=max_filtered_filesize
    # ))

    # print("Finished fetching Telegram messages.")
    ############################
    # END main tg loop
    ############################

    ############################
    # Main LLM process loop
    ############################
    #Now run the OpenAI analysis
    # analyze_messages_with_openai(
    #     input_file='tg/spx6900/spx6900_raw_2000msg_14ktok_2024-10-20_00-21_2024-10-20_21-13.txt',
    #     output_file='openai_response_debug.json'
    # )
    # print("Script finished.")

    # batch process
    process_chat_logs('zyn', date_min='2024-10-15', date_max='2024-10-21')

    ############################
    # END Main LLM process loop
    ############################
    
    #combine it all 
    rollup_project_data('zyn')