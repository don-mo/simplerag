import anthropic

client = anthropic.Anthropic(api_key="floop")

transcript = open("interview.txt", encoding="utf-8").read()

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": transcript + "\n\nBased on this interview, how many mahogany caskets should we order for spring?"}
    ]
)

print(message.content[0].text)