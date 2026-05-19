from flask import Flask, request, render_template, redirect
from flask import url_for, session, Response, stream_with_context
from authlib.integrations.flask_client import OAuth
import anthropic
from dotenv import load_dotenv
import os
import markdown
import json
import sqlite3

load_dotenv()

def init_db():
  # connect to a file, get cursor, CREATE TABLE IF NOT EXISTS FOR users
  # CREATE TABLE IF NOT EXISTS for messages
  # commit, close
  conn = sqlite3.connect("opdecision.db")
  with open("schema.sql") as f: # opens schema create table and closes it
      conn.executescript(f.read())
  conn.commit()
  conn.close()

## define the app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

init_db() # initialize the database when the app starts


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
SYSTEM_PROMPT = (
    "You are Minstoof, assistant of OpDecision AI. "
    "Here is the interview transcript:\n\n" + transcript +
    "\n\nAnswer questions about this company's past advice, lessons, "
    "and anything that helps future operators or CEOs. "
    "Politely decline unrelated requests."
)

@app.route('/', methods=['GET', 'POST'])
def hello_world():
    user = session.get('user')
    user_id = session.get('user_id')

    if not user:
        return redirect('/login')

    conn = sqlite3.connect("opdecision.db")
    conn.row_factory = sqlite3.Row  # rows as dicts
    cursor = conn.cursor()

    if request.method == 'POST':
        question = request.form['question']

        # Save user message to DB
        cursor.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, 'user', question)
        )
        conn.commit()

        # Load all of THIS user's messages to send to Claude
        cursor.execute(
            "SELECT role, content FROM messages WHERE user_id = ? ORDER BY id",
            (user_id,)
        )
        history = [{"role": r["role"], "content": r["content"]} for r in cursor.fetchall()]

        # Call Claude
        report = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=history
        )
        answer = markdown.markdown(report.content[0].text)

        # Save assistant message to DB
        cursor.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, 'assistant', answer)
        )
        conn.commit()

    # Load messages for rendering
    cursor.execute(
        "SELECT role, content FROM messages WHERE user_id = ? ORDER BY id",
        (user_id,)
    )
    messages_for_template = [{"role": r["role"], "content": r["content"]} for r in cursor.fetchall()]

    conn.close()

    return render_template('index.html', messages=messages_for_template, user=user)

@app.route('/login')
def login():
  redirect_url = url_for('callback', _external=True) # where does auth come from, it comes from the route auth
  return oauth.google.authorize_redirect(redirect_url) # this makes sense

@app.route('/callback')
def callback():
    token = oauth.google.authorize_access_token()
    userinfo = token['userinfo']

    conn = sqlite3.connect("opdecision.db")
    cursor = conn.cursor()

    # Try to find existing user by their Google sub
    cursor.execute("SELECT id FROM users WHERE sub = ?", (userinfo['sub'],))
    row = cursor.fetchone()

    if row:
        user_id = row[0]
    else:
        cursor.execute(
            "INSERT INTO users (sub, email, name, picture) VALUES (?, ?, ?, ?)",
            (userinfo['sub'], userinfo['email'], userinfo['name'], userinfo.get('picture'))
        )
        user_id = cursor.lastrowid
        conn.commit()

    conn.close()

    session['user'] = userinfo
    session['user_id'] = user_id
    return redirect('/')

@app.route('/logout')
def logout():
  session.pop('user', None)
  return redirect('/')

@app.route('/ask', methods=['POST'])
def ask():
    user_id = session.get('user_id')
    if not user_id:
        return {'error': 'Not logged in'}, 401

    data = request.get_json()
    question = (data or {}).get('question', '').strip()
    if not question:
        return {'error': 'No question'}, 400

    conn = sqlite3.connect("opdecision.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Save user message
    cursor.execute(
        "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, 'user', question)
    )
    conn.commit()

    # Load this user's full history
    cursor.execute(
        "SELECT role, content FROM messages WHERE user_id = ? ORDER BY id",
        (user_id,)
    )
    history = [{"role": r["role"], "content": r["content"]} for r in cursor.fetchall()]
    conn.close()

    def generate():
        full_response = ""
        try:
            with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=history
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    yield f"data: {json.dumps({'text': text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        md_response = markdown.markdown(full_response)

        # Save assistant message — need fresh connection since generator
        # runs after the route function returns
        conn = sqlite3.connect("opdecision.db")
        conn.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, 'assistant', md_response)
        )
        conn.commit()
        conn.close()

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
    user_id = session.get('user_id')
    if user_id:
        conn = sqlite3.connect("opdecision.db")
        conn.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)