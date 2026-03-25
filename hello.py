import anthropic

client = anthropic.Anthropic(api_key="floop")

transcript = open("interview.txt", encoding="utf-8").read()
while True:
    question = input("Ask a question: ")
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": transcript + "\n\n" + question}
        ]
    )

    print(message.content[0].text)