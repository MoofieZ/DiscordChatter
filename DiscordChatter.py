import requests
import json
import time
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

channels = ["CHANNEL ID", "CHANNEL ID"]
auth = os.getenv("DISCORD_AUTH_TOKEN")
openai_api_key = os.getenv("OPENAI_API_KEY")
bing_api_key = os.getenv("BING_API_KEY")
BOT_NAME = ""


conversation_history = []
channel_conversations = {}
prompt = ""
speech_type = ""

if prompt != "":
    speech_type = "NEVER BREAK CHARACTER. IF YOU CAN'T DO IT. ACT IT IN CHARACTER " + prompt

def getMessage(channel_id):
    API_URL = 'https://discord.com/api/v10/channels/{}/messages'
    headers = {
        'Authorization': f'{auth}'
    }
    url = API_URL.format(channel_id)
    params = {
        'limit': 50
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        messages = response.json()
        topmost_message = None
        for message in messages:
            if message['author']['username'] != BOT_NAME:
                topmost_message = message['content']
                break
        return topmost_message
    else:
        print(f"Failed to fetch messages. Status code: {response.status_code}")
        getMessage(channel_id)

def openai(channel, message):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }
    messages = []
    for msg in conversation_history:
        if "user" in msg:
            messages.append({"role": "user", "content": msg["user"]})
        if "assistant" in msg:
            messages.append({"role": "assistant", "content": msg["assistant"]})
    messages.append({"role": "system", "content": speech_type})
    messages.append({"role": "user", "content": message})
    data = {
        "model": "gpt-4-turbo",
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 4095,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        print("Error:", response.status_code, response.text)

logged = False
channel_chatbots = {}

async def sendMessage(channel_id, message):
    url = f'https://discord.com/api/v10/channels/{channel_id}/messages'
    headers = {
        'Authorization': auth,
        'Content-Type': 'application/json'
    }
    payload = {
        "content": str(message) 
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        print("Message sent successfully!")
    else:
        chunks = split_text(str(message), 1500)
        for chunk in chunks:
            await sendMessage(channel_id, chunk)

def append_to_conversation(user_message, ai_response):
    global conversation_history
    conversation_history.append({"user": user_message, "assistant": ai_response})
    if len(conversation_history) > 10:
        del conversation_history[0]

def split_text(text, chunk_size):
    chunks = []
    start_idx = 0
    while start_idx < len(text):
        end_idx = start_idx + chunk_size
        if end_idx >= len(text):
            chunks.append(text[start_idx:])
            break
        else:
            last_period_idx = text.rfind('.', start_idx, end_idx)
            if last_period_idx == -1:
                last_period_idx = end_idx
            else:
                last_period_idx += 1
            chunks.append(text[start_idx:last_period_idx] + "\n")
            start_idx = last_period_idx
    return chunks

async def process_channel(channel_id):
    print(f"Processing channel {channel_id}")
    if channel_id not in channel_conversations:
        channel_conversations[channel_id] = []
    conversation_history = channel_conversations[channel_id]
    previous_message = getMessage(channel_id)
    while True:
        message = getMessage(channel_id)
        if message and message != previous_message:
            if message != "":
                response = openai(channel_id, message)
                await sendMessage(channel_id, response)
                conversation_history.append({"user": message, "assistant": response})
                if len(conversation_history) > 10:
                    del conversation_history[0]
                previous_message = message  
        await asyncio.sleep(1)

async def main():
    tasks = []
    for channel_id in channels:
        task = asyncio.create_task(process_channel(channel_id))
        tasks.append(task)
    await asyncio.gather(*tasks)

asyncio.run(main())
