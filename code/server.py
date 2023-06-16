import os, json
from flask import Flask, render_template, request
import threading
from dotenv import load_dotenv
from sherlock import Sherlock
from util import *

load_dotenv()
CONFIG_PATH = os.getenv('CONFIG_PATH')

app = Flask(__name__)
sherlock = Sherlock(CONFIG_PATH)

@app.route("/")
def home():
    return render_template("index.html")

def output_correction():
    correction_instruction = '''Please follow the 3-step process given the most recent observation and then output one of the possible commands, search or play.'''
    q_history = sherlock.get_history()['q_history']
    if q_history[-1]['role'] == 'user':
        context = correction_instruction + '\n' + q_history[-1]['content']
    else:
        return
    sherlock.pop_history()
    sherlock.save_history(context, 'user')

def summarise_history():
    q_history = sherlock.get_history()['q_history']
    if len(q_history) % 10 != 0:
        return
    _, summarize_input = get_prompt("herstory_summary_v1.1")
    sherlock.save_history(summarize_input, 'user')
    raw_output = sherlock.get_gpt_response()
    if raw_output == None:
        raw_output = sherlock.get_gpt_response_azure()
    if raw_output == None:
        print("Summarization Error")
    sherlock.pop_history()
    sherlock.save_summary(raw_output)
    print(f"summarization complete : {raw_output}")

def get_response():
    raw_output = sherlock.get_gpt_response()
    if raw_output == None:
        print("gpt-4 open-ai error, try again in gpt-3.5")
        raw_output = sherlock.get_gpt_response_azure()
    if raw_output == None:
        print("gpt-3.5 open-ai error")
    return raw_output


def generate_response(data, mode):

    summarise_history()

    if mode == 'search':
        sherlock.save_keyword(f"{data['SearchedKeyword']} ({data['EntriesNum']})")
        context = generate_search_input(data)
        sherlock.save_history(context, 'user')
    elif mode == 'play':
        context = generate_play_input(data)
        sherlock.save_history(context, 'user')
    elif mode == 'tag':
        context = "User tags have been added."
        sherlock.save_history(context, 'user')
    elif mode == 'start':
        pass

    raw_output = get_response()
    if raw_output == None:
        return None, None
    response, action = post_process(raw_output)

    if action == None:
        output_correction()
        raw_output = get_response()
        if raw_output == None:
            return None, None
        response, action = post_process(raw_output)

    if action != None:
        sherlock.save_history(raw_output, 'assistant')
        return response, action
        
    return None, None
        
def generate_play_input(data):
    new_data = {}
    empty_context = f"No Video found."
    if 'Session' not in data:
        return empty_context
    if data['Session'] == '':
        return empty_context

    keys = ['Session', 'Person', 'Transcript']
    for key in keys:
        new_data[key] = data[key]
    context = json.dumps(new_data)
    return context

def generate_search_input(data):
    entry_num = int(data['EntriesNum'])
    if entry_num <= 5:
        context = f"Search result of {data['SearchedKeyword']}: {data['EntriesNum']} entries found. Unwatched video index: {data['UnseenVideoIndexes']}."
    else:
        context = f"Search result of {data['SearchedKeyword']}: {data['EntriesNum']} entries found. ACCESS LIMITED TO THE FIRST 5 ENTRIES. Unwatched video index: {data['UnseenVideoIndexes']}."
    return context

def main(req):
    mode = req['mode']
    data = req['result']
    data = json.loads(data)

    if mode not in ['search', 'play', 'tag', 'start']:
        return "INVAID MODE ERROR"
    response, action = generate_response(data, mode)
    if response is None or action is None:
        return 'GPT ERROR'
    try:
        res = call_back(response, action)
        return 'Success'
    except:
        return 'CALLBACK ERROR'

@app.route("/solve", methods=["POST"])
def solve():
    req = json.loads(request.data)
    threading.Thread(target=main, args=[req]).start()
    return '200'

if __name__ == "__main__":
    #app.run()
    app.run(host='0.0.0.0', port=5060)
