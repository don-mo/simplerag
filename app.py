from flask import Flask, request, render_template, redirect
from flask import url_for, session, Response, stream_with_context
from authlib.integrations.flask_client import OAuth
import anthropic
from dotenv import load_dotenv
import os
import markdown
import json



load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
oauth = OAuth(app)
oauth.register(
  name='google',
  server_metadata_url=CONF_URL,
  client_kwargs={
    'scope': 'openid email profile'
  }
)
client = anthropic.Anthropic(api_key=os.getenv('API_KEY'))
transcript = open("interview.txt", encoding="utf-8").read()
messages=[
            {"role": "user", "content": "This is a transcript from a eat together club interview: \n\n"
            + transcript + "\n\nYou are Minstoof, assistant of OpDecision AI. questions to be answered are"
            + "one's related to this companys past advice, know how to handle similar situations, and past lessons, and anything that would help the future operators or ceos."
            + "Politely decline any unrelated requests"},
            {"role": "assistant", "content": "I've read the interview. Ask me anything about"
            + " this company."}
        ]

@app.route('/', methods=['GET', 'POST'])
def hello_world():
  user = session.get('user')

  if not user:
    return redirect('/login') # or render a sign-in page

  # original chat logic
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


  return render_template('index.html', messages=messages, user=user)

@app.route('/login')
def login():
  redirect_url = url_for('callback', _external=True) # where does auth come from, it comes from the route auth
  return oauth.google.authorize_redirect(redirect_url) # this makes sense

@app.route('/callback')
def callback():
  token = oauth.google.authorize_access_token()
  session['user'] = token['userinfo']
  return redirect('/')

@app.route('/logout')
def logout():
  session.pop('user', None)
  return redirect('/')

@app.route('/ask', methods=['POST'])
def ask():
    if not session.get('user'):
        return {'error': 'Not logged in'}, 401

    data = request.get_json()
    question = (data or {}).get('question', '').strip()
    if not question:
        return {'error': 'No question'}, 400

    messages.append({"role": "user", "content": question})

    def generate():
        full_response = ""
        try:
            with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=messages
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    yield f"data: {json.dumps({'text': text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        md_response = markdown.markdown(full_response)
        messages.append({"role": "assistant", "content": md_response})
        yield f"data: {json.dumps({'done': True, 'html': md_response})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )

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