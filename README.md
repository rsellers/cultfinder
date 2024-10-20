# cultfinder
NEW CACHE
CultFinder is a LLM-powered evaluation and ranking framework for public chat groups. 

Requirements:
1. You will credentials for OpenAI API access. See: https://platform.openai.com/
2. You will need Telegram login credentials. See: https://my.telegram.org/apps

The project has three main functions:
1. Scrape a public Telegram group across a time/date period, filter bots/spam and break into chunks which fit OpenAI's token context window.
2. Submit chat logs to OpenAI alongside a prompt and JSON structured output request.
3. Visualize emotional grade over time.

Python package requirements
1. OpenAI's python library: pip install openai
2. Pydantic for LLM structured output: pip install pydantic
3. Telethon for an easy to use Telegram library: pip install telethon
4. Others: dotenv, nltk
