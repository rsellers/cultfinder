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


def load_env()
    # Load environment variables from .env file
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

# Read the prompt from prompt.ini
try:
    with open('prompt.ini', 'r', encoding='utf-8') as file:
        prompt_template = file.read()
    print("Loaded prompt.ini successfully.")
except Exception as e:
    print(f"Error loading prompt.ini: {e}")
    exit(1)

# Create the Telegram client
tg_client = TelegramClient('session_name', api_id, api_hash)


async def fetch_telegram_messages(
    group='debug',
    limit=1000,
    username='debug',
    check_spam=False
):
    """Fetch text messages from a Telegram group and save to a file, ignoring specific users.

    Parameters:
    - group (str): Name of the group, used for directory and file naming.
    - output_file (str): Name of the output file (will be overridden by naming convention).
    - limit (int): Number of messages to fetch.
    - username (str): Telegram group username or link.
    - check_spam (bool): If True, checks for spam users to ignore after accumulating 300 messages.
    """
    print("Starting fetch_telegram_messages function.")
    await tg_client.start(phone)
    print("Telegram client started.")

    print(f"Fetching messages from group: {username}")
    # Get the channel entity
    try:
        channel = await tg_client.get_entity(username)
        print(f"Successfully obtained entity for {username}")
    except Exception as e:
        print(f"Error getting Telegram entity for '{username}': {e}")
        return

    # Create the group directory if it doesn't exist
    group_dir = os.path.join('tg', group)
    os.makedirs(group_dir, exist_ok=True)

    message_log = []
    total_messages = 0
    filtered_messages_count = 0
    all_messages_text = ""
    timestamps = []

    ignore_list = []  # Initialize ignore_list
    spam_check_messages = []

    print(f"Retrieving the last {limit} messages...")

    async for message in tg_client.iter_messages(channel, limit=limit):
        total_messages += 1  # Track total number of messages fetched

        if message.message:
            sender = await message.get_sender()
            
            sender_username = sender.username if sender.username else f"id_{sender.id}"
            
            # If check_spam is enabled, also ignore all messages from designated bot accounts
            if check_spam == True and sender.bot == True:
                continue
                # # Accumulate messages for spam checking
                # if check_spam and len(spam_check_messages) < 100:
                #     spam_check_messages.append({
                #         'message': message.message,
                #         'sender_username': sender_username
                #     })
                #     if len(spam_check_messages) == 100:
                #         # Call check_spam_with_openai() (to be implemented)
                #         ignore_list = check_spam_with_openai(spam_check_messages)
                #         print(f"Spam users identified: {ignore_list}")

                # # Skip messages from users in the ignore list
                # if any(normalize_username(sender_username) == normalize_username(ignored_user) for ignored_user in ignore_list):
                #     continue

            timestamp = message.date.strftime('%Y-%m-%d %H:%M')
            text = message.message
            timestamps.append(message.date)

            # Create a formatted message entry
            message_entry = f"Date:{timestamp}\nUsr:@{sender_username}\nMsg:{text}\n--\n"

            # Append the message entry to the log
            message_log.append(message_entry)
            all_messages_text += text + " "  # Accumulate all text for token counting
            filtered_messages_count += 1  # Track number of messages after filtering

    print(f"Total messages fetched: {total_messages}")
    print(f"Messages after filtering: {filtered_messages_count}")

    # Calculate total tokens
    tokens = word_tokenize(all_messages_text)
    total_tokens = len(tokens)
    print(f"Total tokens in messages: {total_tokens}")

    # Get date range
    if timestamps:
        date_min = min(timestamps).strftime('%Y-%m-%d_%H-%M')
        date_max = max(timestamps).strftime('%Y-%m-%d_%H-%M')
    else:
        date_min = date_max = 'no_dates'

    # Prepare file name
    nmsg = f"{total_messages}msg"
    ntok = f"{total_tokens//1000}ktok"
    checkspam_flag = 'spamchk' if check_spam else 'nospamchk'
    output_filename = f"{group}_{checkspam_flag}_{nmsg}_{ntok}_{date_min}_{date_max}.txt"
    output_path = os.path.join(group_dir, output_filename)

    # Save the message log to a file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(message_log)
        print(f"Telegram messages saved to '{output_path}'.")
    except Exception as e:
        print(f"Error writing to '{output_path}': {e}")

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
    ############################
    # Main tg loop
    ############################
    #Run the fetching function within the client's event loop
    # with tg_client:
    #     tg_client.loop.run_until_complete(fetch_telegram_messages(
    #         group='pollen',
    #         limit=500,
    #         #username='https://t.me/+F37V2KpUcJZmMDFh', #spx6900
    #         #username='https://t.me/XNETgossip',  #xnet  
    #         #username='https://t.me/max2049cto'
    #         username='@pollenfuture2023',
    #         check_spam=False
    #     ))
    # print("Finished fetching Telegram messages.")



    ############################
    # Main LLM process loop
    ############################
    #Now run the OpenAI analysis
    analyze_messages_with_openai(
        input_file='tg/pollen/pollen_nospamchk_500msg_5ktok_2023-02-24_17-00_2024-06-12_19-33.txt',
        output_file='openai_response_debug.json'
    )
    print("Script finished.")
