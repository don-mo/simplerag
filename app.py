from flask import Flask, request, render_template
import anthropic
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

client = anthropic.Anthropic(api_key=os.getenv('API_KEY'))
transcript = open("interview.txt", encoding="utf-8").read()

@app.route('/', methods=['GET', 'POST'])
def hello_world():
  answer = None
  if request.method == 'POST':
    question = request.form['question']
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": transcript + "\n\n" + question}
        ]
    )
    answer = message.content[0].text
  return render_template('index.html', answer=answer)
app.run(port=5000)