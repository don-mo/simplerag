document.addEventListener('DOMContentLoaded', function () {
  const form       = document.getElementById('chat-form');
  const input      = document.getElementById('question-input');
  const messagesEl = document.getElementById('messages');
  const dogLoading = document.getElementById('dog-loading');
  const askBtn     = document.getElementById('ask-btn');
  const chatArea   = document.getElementById('chat-area');

  // ── Scroll chat area to the very bottom ──────────────
  function scrollToBottom() {
    chatArea.scrollTop = chatArea.scrollHeight;
  }

  // Show latest messages on first load
  scrollToBottom();

  // ── Enter = submit  |  Shift+Enter = newline ─────────
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      form.dispatchEvent(new Event('submit', { cancelable: true }));
    }
  });

  // ── Escape HTML to safely insert user text ───────────
  function escapeHtml(text) {
    const d = document.createElement('div');
    d.appendChild(document.createTextNode(text));
    return d.innerHTML;
  }

  // ── Main submit handler ───────────────────────────────
  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const question = input.value.trim();
    if (!question) return;

    // Clear textarea and lock controls
    input.value    = '';
    input.disabled = true;
    askBtn.disabled = true;

    // 1. Add user bubble immediately
    const userDiv = document.createElement('div');
    userDiv.className = 'user-msg';
    userDiv.innerHTML = '<strong>You:</strong> ' + escapeHtml(question);
    messagesEl.appendChild(userDiv);
    scrollToBottom();

    // 2. Show dog animation
    dogLoading.classList.remove('hidden');
    scrollToBottom();

    // 3. Prepare assistant bubble (inserted on first chunk)
    const assistantDiv = document.createElement('div');
    assistantDiv.className = 'assistant-msg';

    let responseSpan   = null;
    let cursorEl       = null;
    let rawText        = '';
    let bubbleInserted = false;

    function insertAssistantBubble() {
      if (bubbleInserted) return;
      bubbleInserted = true;

      dogLoading.classList.add('hidden');

      const label = document.createElement('strong');
      label.textContent = 'Minstoof: ';

      responseSpan = document.createElement('span');
      responseSpan.className = 'response-text';

      cursorEl = document.createElement('span');
      cursorEl.className = 'cursor';

      assistantDiv.appendChild(label);
      assistantDiv.appendChild(responseSpan);
      assistantDiv.appendChild(cursorEl);
      messagesEl.appendChild(assistantDiv);
      scrollToBottom();
    }

    // 4. Stream from /ask
    try {
      const res = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });

      if (!res.ok) throw new Error('Server returned ' + res.status);

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer    = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE events are separated by double newlines
        const events = buffer.split('\n\n');
        buffer = events.pop(); // keep any trailing incomplete chunk

        for (const event of events) {
          if (!event.startsWith('data: ')) continue;

          let data;
          try { data = JSON.parse(event.slice(6)); }
          catch { continue; }

          if (data.error) {
            insertAssistantBubble();
            responseSpan.textContent = 'Error: ' + data.error;
            cursorEl && cursorEl.remove();
            break;
          }

          if (data.text !== undefined) {
            // Typewriter: append each chunk as plain text
            insertAssistantBubble();
            rawText += data.text;
            responseSpan.textContent = rawText;
            scrollToBottom();
          }

          if (data.done) {
            // Swap plain text for markdown-rendered HTML, remove cursor
            cursorEl && cursorEl.remove();
            responseSpan.innerHTML = data.html;
            scrollToBottom();
          }
        }
      }
    } catch (err) {
      console.error(err);
      dogLoading.classList.add('hidden');

      if (!bubbleInserted) {
        assistantDiv.innerHTML = '<strong>Minstoof:</strong> Sorry, something went wrong. Please try again.';
        messagesEl.appendChild(assistantDiv);
      } else if (responseSpan) {
        responseSpan.textContent = 'Sorry, something went wrong. Please try again.';
        cursorEl && cursorEl.remove();
      }
      scrollToBottom();
    }

    // 5. Re-enable input
    input.disabled  = false;
    askBtn.disabled = false;
    input.focus();
  });
});
