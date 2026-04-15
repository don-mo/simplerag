from flask import Flask, request, render_template, redirect
from flask_session import Session

import anthropic
from dotenv import load_dotenv
import os
import markdown



load_dotenv()

app = Flask(__name__)

app.config['SESSION_TYPE'] = False # Sessions (accounts) expire when the browser is closed
app.config['SESSION_TYPE'] = "filesystem" # Store session data in files (on your own local computer)

# Initialize the flask-session (login request using cookies)
Session(app)

client = anthropic.Anthropic(api_key=os.getenv('API_KEY'))
transcript = open("interview.txt", encoding="utf-8").read()

messages=[
            {"role": "user", "content": "This is a transcript from a business interview: \n\n"
            + transcript + "\n\nYou are Minstoof, assistant of OpDecision AI. questions to be answered are"
            + "one's related to this business's inventory, operations, and ordering decisions."
            + "Politely decline any unrelated requests"},
            {"role": "assistant", "content": "I've read the interview. Ask me anything about"
            + " this business."}
        ]

@app.route('/', methods=['GET', 'POST'])
def hello_world():
  answer = None
  if request.method == 'POST':
    question = request.form['question']
    messages.append({"role": "user", "content": question})
    report = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=messages
    )
    answer = report.content[0].text
    answer = markdown.markdown(answer)
    messages.append({"role": "assistant", "content": answer})


  return render_template('index.html', messages=messages)

@app.route('/second')
def second():
  return render_template('indexSite.html')

@app.route('/reset')
def reset():
  messages.clear()
  messages.extend([
    {"role": 'user', 'content': 'Here is a business interview transcript:\n\n' + transcript + '\n\nYou are minstoof. Only answer questions about this business.'},
    {"role": "assistant", "content": "I've read the interview. Ask me anything about this business"}
  ])
  return redirect('/')

app.run(port=5000, debug=True)