import requests
import os, json
from dotenv import load_dotenv

load_dotenv()
CLIENT_URL = os.getenv('CLIENT_URL')

def is_from_assistant(content):
    if 'role' not in content:
        return False
    if content['role'] == 'assistant':
        return True
    return False

def trim_history(q_history):
    if is_from_assistant(q_history[len(q_history)-1]):
        return q_history[:-1]
    else:
        return q_history

def build_content(text, role="user"):
    return {"role": role, "content": text}

def get_prompt(id):
    #get valid prompt
    system = ""
    user = ""
    return system, user

def call_back(data, action):
    if action == 'search':
        url = f'{CLIENT_URL}/Search'
    elif action == 'play':
        url = f'{CLIENT_URL}/PlayVideo'
    elif action == 'tag':
        url = f'{CLIENT_URL}/AddTag'
    else:
        return 'Error'
    dump_data = json.dumps(data)
    x = requests.post(url, data=dump_data)
    return x

def post_process(response):
    if 'Command:' not in response:
        return None, None
    command_line = response.split('Command:')[1]
    command = command_line.split('\n')[0].lower()
    command = command.replace('"','').replace("'",'').strip()
    action_list = ['search', 'play', 'add']
    action = None
    for act in action_list:
        if command.startswith(act):
            action = act
            break
    if action == None:
        return None, None
    
    if action == 'search':
        result = {}
        result['Keyword'] = command.split('search')[1].strip()
        return result, action
    
    if action == 'play':
        result = {}
        result['VideoIndex'] = command.split('video')[1].strip()
        return result, action
    
    if action == 'add':
        action = 'tag'
        result = {}
        infos = command.split('video')[1].strip()
        video_num = infos.split(':')[0].strip()
        tag = infos.split(':')[1].strip()
        result['VideoIndex'] = video_num
        result['Tag'] = tag
        return result, action

    return None, None