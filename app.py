from flask import Flask, request, render_template, redirect

import anthropic
from dotenv import load_dotenv
import os
import markdown



load_dotenv()

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)