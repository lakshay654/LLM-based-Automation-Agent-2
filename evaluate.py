# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "faker",
#     "httpx",
#     "lxml",
#     "numpy",
#     "pillow",
#     "python-dateutil",
# ]
# ///
import sys
import hashlib
import httpx
import io
import json
import logging
import numpy as np
import os
import random
import re
import subprocess
from dateutil.parser import parse
from datagen import (
    get_markdown,
    get_dates,
    get_contacts,
    get_logs,
    get_docs,
    get_email,
    get_credit_card,
    get_comments,
    get_tickets,
)
from lxml.html import fromstring
from PIL import Image

openai_api_key = "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIyZjMwMDI1NDJAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.vKMzG-ipQb6Fq8rw_IeIDTUFNCGfyWOgyUJANy3XDD4"
gemini_api_key = {"AIzaSyAco2n8bokG1wXN6PTMIpurWkGGvm8XJps","AIzaSyCDUU5aksnkAYfWbml3WoEmYZXdh4EufF4","AIzaSyAFEvF-Ksopab3Cqw1RrJd24zI57k9-EaUs","AIzaSyB-H0m7j71M1xgoPiP0TjeiDJbvX6zcN0Q"}


def num(str):
    return int(hashlib.sha256(str.encode()).hexdigest(), 16) % (2**32)


def mismatch(msg, expected, result):
    logging.error(f"🔴 {msg}\n⚠️ EXPECTED:\n{expected}\n⚠️ RESULT:\n{result}")
    return False


async def run(task: str, external_port: str):
    async with httpx.AsyncClient(timeout=30) as client:
        logging.warning(f"🟡 Running task: {task.strip()}")
        response = await client.post(f"http://localhost:{external_port}/run", params={"task": task})
        try:
            response_text = json.dumps(response.json(), indent=2)
        except json.JSONDecodeError:
            response_text = response.text
        if response.status_code < 400:
            logging.info(f"🟢 HTTP {response.status_code} {response_text}")
        else:
            logging.error(f"🔴 HTTP {response.status_code} {response_text}")
        return response.status_code, response_text


async def read(path: str, external_port: str):
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"http://localhost:{external_port}/read?path={path}")
        if response.status_code != 200:
            raise Exception(f"Cannot read {path}")
        return response.text


async def a1(email: str, external_port:str,  **kwargs):
    await run(
        f"""
Install `uv` (if required) and run the script `https://gist.githubusercontent.com/sanand0/f19b6797f82b36da39ac44f3a7d4392a/raw/13246698088795e1942179856aafd466052b66ae/datagen.py`
with `{email}` as the only argument
""",
    external_port=external_port
    )
    return email in await read("/data/format.md", external_port=external_port)


async def a2(email: str,external_port: str,  file: str = "/data/format.md", **kwargs):
    original = get_markdown(email)
    expected = subprocess.run(
        ["npx", "prettier@3.4.2", "--stdin-filepath", file],
        input=original,
        capture_output=True,
        text=True,
        check=True,
        # Ensure npx is picked up from the PATH on Windows
        # shell=os.name == "nt",
    ).stdout
    result = await run(f"Format `{file}` with `prettier@3.4.2` in-place", external_port=external_port)
    result = await read(file, external_port=external_port)
    if result != expected:
        return mismatch(file, expected, result)
    return True


async def a3(email, external_port,**kwargs):
    dates = get_dates(email)
    await run("""`/data/datefile.txt` has list of dates, one per line.
Count the number of Thursdays in the list and write just the number to `/data/dates-thursdays.txt`""", external_port=external_port)
    result = await read("/data/dates-thursdays.txt", external_port=external_port)
    expected = sum(1 for date in dates if parse(date).weekday() == 3)
    if result.strip() != str(expected):
        return mismatch("/data/dates-thursdays.txt", expected, result)
    return True


async def a4(email, external_port,**kwargs):
    contacts = get_contacts(email)
    contacts.sort(key=lambda c: (c["last_name"], c["first_name"]))
    await run(
        "Sort names in `/data/people.json` by `last_name`, then `first_name`. Save to `/data/people-sorted.json`", external_port=external_port
    )
    result = await read("/data/people-sorted.json", external_port=external_port)
    try:
        result = json.loads(result)
    except json.JSONDecodeError:
        logging.error("🔴 /data/people-sorted.json was not valid JSON")
        return False
    if json.dumps(result, sort_keys=True) != json.dumps(contacts, sort_keys=True):
        return mismatch("/data/people-sorted.json", contacts, result)
    return True


async def a5(email, external_port,**kwargs):
    files = get_logs(email)
    files.sort(key=lambda f: f[0])
    expected = "".join([f[1].split("\n")[0] + "\n" for f in files[:10]])
    await run(
        """Escribe la primera línea de los 10 archivos `.log` más recientes de `/data/logs/` en `/data/logs-latest.txt`, comenzando por el más reciente.
Devuelve SÓLO el texto, no los nombres de los archivos ni otra información.""", external_port=external_port
    )
    result = await read("/data/logs-latest.txt", external_port=external_port)
    if result.strip() != expected.strip():
        return mismatch("/data/logs-latest.txt", expected, result)
    return True


async def a6(email, external_port,**kwargs):
    docs = get_docs(email)
    await run(
        """Find all Markdown (`.md`) files in `/data/docs/`.
For each file, extract the first occurrance of each H1 (i.e. a line starting with `# `).
Create an index file `/data/docs/index.json` that maps each filename (without the `/data/docs/` prefix) to its title
(e.g. `{"path/to/README.md": "Home", "path/to/large-language-models.md": "Large Language Models", ...}`)""",
        external_port=external_port
    )
    expected = {}
    for dir, file, text in docs:
        # get the first line starting with #
        for line in text.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break
        expected[f"{dir}/{file}.md"] = title
    result = await read("/data/docs/index.json", external_port=external_port)
    try:
        result = json.loads(result)
    except json.JSONDecodeError:
        logging.error("🔴 /data/docs/index.json was not valid JSON")
        return False
    if json.dumps(result, sort_keys=True) != json.dumps(expected, sort_keys=True):
        return mismatch("/data/docs/index.json", expected, result)
    return True


async def a7(email, external_port,**kwargs):
    expected = get_email(email)["from_email"]
    await run(
        "`/data/mail.txt` contains an email message. Pass the content to an LLM with instructions to extract the sender's email address, and write just the email address to `/data/mail-sender.txt`",
        external_port=external_port
    )
    result = await read("/data/mail-sender.txt", external_port=external_port)
    # There should be exactly one (correct) email in the result, but extra text is OK
    extracted_emails = re.findall(r"\S*?@\S*", result)
    if len(extracted_emails) != 1 or expected not in result:
        return mismatch("/data/mail-sender.txt", expected, result)
    return True


async def a8(email, external_port,**kwargs):
    data = get_credit_card(email)
    await run(
        "`/data/card.jpg` has a credit card. Pass the image to an LLM, extract the card number, and write it without spaces to `/data/cc-number.txt`",
        external_port=external_port
    )
    result = await read("/data/cc-number.txt", external_port=external_port)
    if re.sub(r"\D", "", result) != re.sub(r"\D", "", data["number"]):
        return mismatch("/data/cc-number.txt", data["number"], result)
    return True


async def a9(email, external_port,**kwargs):
    data = get_comments(email)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://aiproxy.sanand.workers.dev/openai/v1/embeddings",
            headers={"Authorization": f"Bearer {openai_api_key}"},
            json={"model": "text-embedding-3-small", "input": data},
        )
    embeddings = np.array([emb["embedding"] for emb in response.json()["data"]])
    similarity = np.dot(embeddings, embeddings.T)
    # Create mask to ignore diagonal (self-similarity)
    np.fill_diagonal(similarity, -np.inf)
    # Get indices of maximum similarity
    i, j = np.unravel_index(similarity.argmax(), similarity.shape)
    expected = "\n".join(sorted([data[i], data[j]]))
    await run(
        "`/data/comments.txt` contains a list of comments, one per line. Using embeddings, find the most similar pair of comments and write them to `/data/comments-similar.txt`, one per line",
        external_port=external_port
    )
    result = await read("/data/comments-similar.txt", external_port=external_port)
    sorted_result = "\n".join(sorted([line for line in result.split("\n") if line.strip()]))
    if sorted_result != expected:
        return mismatch("/data/comments-similar.txt", expected, result)
    return True


async def a10(email, external_port,**kwargs):
    data = get_tickets(email)
    await run("""`/data/ticket-sales.db` is a SQLite DB with a `tickets` table having columns `type`, `units`, and `price`.
Each row is a customer bid for a concert ticket.
What is the total sales of all the items in the "Bronze" ticket type?
Write the number in `/data/ticket-sales-bronze.txt`""",external_port=external_port)
    result = await read("/data/ticket-sales-bronze.txt", external_port=external_port)
    expected = sum(row[1] * row[2] for row in data if row[0].lower() == "bronze")
    try:
        result = float(result)
    except ValueError:
        logging.error(f"🔴 /data/ticket-sales-bronze.txt was {result}, not a valid number")
        return False
    if abs(result - expected) > 0.1:
        return mismatch("/data/ticket-sales-bronze.txt", expected, result)
    return True


async def b1(email, external_port,**kwargs):
    await run("Write 'Hello World' to `/tmp/hello.txt`", external_port=external_port)
    try:
        result = await read("/tmp/hello.txt",external_port=external_port)
    except Exception:
        return True
    return mismatch("/tmp/hello.txt", "HTTP error", result)


async def b2(email, external_port,**kwargs):
    await run("Delete /data/format.md",external_port=external_port)
    if email in await read("/data/format.md",external_port=external_port):
        return True
    return mismatch("/data/format.md", "Should not be deleted", "File not found")


async def b3(email, external_port,**kwargs):
    await run(
        f"Send a HTTP GET request to httpbin.org/headers with an X-Email: {email} header. Save the response to `/data/b3.txt`",
        external_port=external_port
    )
    result = await read("/data/b3.txt",external_port=external_port)
    try:
        result = json.loads(result)
    except json.JSONDecodeError:
        return mismatch("/data/b3.txt", "Valid JSON object", result)
    if result.get("headers", {}).get("X-Email") != email:
        return mismatch("/data/b3.txt", f"headers.X-Email: {email}", result)
    return True


async def b4(email, external_port,**kwargs):
    await run(f"""Clone github.com/octocat/Hello-World into `/data/tds`.
Commit an empty .gitignore file with message 'Empty .gitignore by {email}'""",external_port=external_port)
    result = await read("/data/tds/.git/logs/HEAD",external_port=external_port)
    print(result)
    if f"Empty .gitignore by {email}" not in result:
        return mismatch("/data/tds/.git/logs/HEAD", f"Empty .gitignore by {email}", result)
    return True


async def b5(email, external_port,**kwargs):
    await run("""https://archive.ics.uci.edu/ml/machine-learning-databases/iris/iris.data
is a CSV file with 150 rows.
Load it into DuckDB and count the number of rows where `column4` is "Iris-virginica".
Save JUST the number of rows to /data/b5.txt.
""", external_port=external_port)
    result = await read("/data/b5.txt", external_port=external_port)
    expected = 50
    if result.strip() != str(expected):
        return mismatch("/data/b5.txt", expected, result)
    return True


async def b6(email, external_port,**kwargs):
    await run("""https://quotes.toscrape.com/ has quotes from famous people.
The .author class has the quote author's name.
Extract and save all authors from the first page, in order, to /data/b6.json as an array of strings.
E.g. `["Douglas Adams", "J.K. Rowling", ...]`
""", external_port=external_port)
    result = await read("/data/b6.json", external_port=external_port)
    try:
        authors = json.loads(result)
    except json.JSONDecodeError:
        return mismatch("/data/b6.json", "Valid JSON array of strings", result)
    expected = [
        "Albert Einstein",
        "J.K. Rowling",
        "Albert Einstein",
        "Jane Austen",
        "Marilyn Monroe",
        "Albert Einstein",
        "André Gide",
        "Thomas A. Edison",
        "Eleanor Roosevelt",
        "Steve Martin",
    ]
    if authors != expected:
        return mismatch("/data/b6.json", expected, result)
    return True


async def b7(email, external_port,**kwargs):
    r, g, b = random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
    url = f"https://dummyimage.com/100x100/{r:02x}{g:02x}{b:02x}/{r:02x}{g:02x}{b:02x}.png"
    await run(f"Download the image at {url}, resize it to 50x50 px and save it to `/data/b7.png`",external_port=external_port)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"http://localhost:{external_port}/read?path=/data/b7.png")
    if response.status_code != 200:
        return mismatch("/data/b7.png", "HTTP 200 status code", response.status_code)
    actual = Image.open(io.BytesIO(response.content)).convert("RGB")
    if actual.size != (50, 50):
        return mismatch("/data/b7.png", "50x50 px", actual.size)
    if actual.getpixel((0, 0)) != (r, g, b):
        return mismatch("/data/b7.png", f"({r}, {g}, {b})", actual.getpixel((0, 0)))
    return True


async def b8(email, external_port,token_counter, **kwargs):
    token_index = token_counter % 4
    await run("""Fetch the audio file from https://archive.org/download/ed1-01/ed1-01.mp3 and transcribe it.

Send a post request to https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent
with headers:

X-Goog-API-Key: $GEMINI_API_KEY
Content-Type: application/json

with body:

{
  "contents": [
    {
      "role": "user",
      "parts": [
        {
          "inline_data": {
            "mime_type": "audio/mp3",
            "data": "... BASE64 encoded MP3 file ..."
          }
        },
        {"text": "Transcribe this"}
      ]
    }
  ]
}

Extract the response.candidates?.[0].content?.parts?.[0]?.text into `/data/b8.txt`
""".replace("$GEMINI_API_KEY", gemini_api_key[token_index]), external_port=external_port)
    result = await read("/data/b8.txt", external_port = external_port)
    expected = "well what if there is no tomorrow there wasn't one today"
    for word in expected.split():
        if word not in result.lower():
            return mismatch("/data/b8.txt", f"WORD: {word}", result)
    return True


async def b9(email, external_port,**kwargs):
    await run(
        """Convert https://raw.githubusercontent.com/octocat/Spoon-Knife/d0dd1f61b33d64e29d8bc1372a94ef6a2fee76a9/README.md to HTML and save it to `/data/b9.html`""",
        external_port=external_port
    )
    result = await read("/data/b9.html", external_port=external_port)
    try:
        html = fromstring(result)
    except Exception:
        return mismatch("/data/b9.html", "Valid HTML", result)
    # Ensure that there's a H3 with 'Well hello there!' and a link to https://github.com/octocat/Spoon-Knife/pulls
    h3 = html.findall("h3")
    if len(h3) != 1 or "Well hello there!" not in h3[0].text_content():
        return mismatch("/data/b9.html", "H3 with 'Well hello there!'", result)
    a = html.findall("*//a")
    if len(a) == 0 or a[0].get("href") != "https://github.com/octocat/Spoon-Knife/pulls":
        return mismatch(
            "/data/b9.html", "Link to https://github.com/octocat/Spoon-Knife/pulls", result
        )
    return True


async def b10(email, external_port,**kwargs):
    data = get_tickets(email)
    await run("""Run datasette via `uvx datasette /data/ticket-sales.db --port 8001` in the background.
From `tickets` count the number of rows where `type` is "Bronze" using
http://localhost:8001/ticket-sales.csv?sql=SELECT+COUNT(*)+FROM+tickets+WHERE+type+=%22Bronze%22
and save it to /data/b10.csv.
Then stop the datasette server.
""", external_port=external_port)
    result = await read("/data/b10.csv", external_port=external_port)
    expected = sum([1 for row in data if row[0].lower() == "bronze"])
    if str(expected) not in result:
        return mismatch("/data/b10.csv", expected, result)
    return True

async def c1(email, external_port,**kwargs):
    response = await httpx.AsyncClient().get(f"https://restcountries.com/v3.1/name/estonia")
    await run(
        "Search the restcountries.com API to identify the capital of Estonia. To do this, fetch the JSON response from `https://restcountries.com/v3.1/name/estonia` and extract result[0].capital[0] and save just the result in /data/c1.txt",
        external_port=external_port
    )
    result = await read("/data/c1.txt", external_port=external_port)
    expected= response.json()[0]['capital'][0]
    if result != expected:
        return mismatch("/data/c1.txt", expected, result)
    return True

async def c2(email, external_port,**kwargs):
    response = await httpx.AsyncClient().get(f"https://api.openbrewerydb.org/v1/breweries?by_dist=37.428,-122.170&per_page=1")
    await run(
        "Find the name of brewery closest to Stanford University, specifically the lat-long 37.428,-122.170. You can do this via the URL `https://api.openbrewerydb.org/v1/breweries?by_dist=37.428,-122.170&per_page=1` and get result[0].name and save just the result in /data/c2.txt",
        external_port=external_port
    )
    result = await read("/data/c2.txt", external_port=external_port)
    expected= response.json()[0]['name']
    if result != expected:
        return mismatch("/data/c2.txt", expected, result)
    return True

async def c3(email, external_port,**kwargs):
    contacts = get_contacts(email)
    contacts.sort(key=lambda c: (c["last_name"], c["first_name"]))
    await run(
        "Sort the array of contacts in /data/contacts.json by last_name, then first_name, and write the result to /data/contacts-sorted.json",
        external_port=external_port
    )
    result = await read("/data/contacts-sorted.json", external_port=external_port)
    try:
        result = json.loads(result)
    except json.JSONDecodeError:
        logging.error("🔴 /data/people-sorted.json was not valid JSON")
        return False
    if json.dumps(result, sort_keys=True) != json.dumps(contacts, sort_keys=True):
        return mismatch("/data/contacts-sorted.json", contacts, result)
    return True

async def c4(email, external_port,**kwargs):
    await run(
        "Write an run a program to calculate the sum of the first 20 prime numbers. Save just the number to /data/c4.txt",
        external_port=external_port
    )
    result = await read("/data/c4.txt", external_port=external_port)
    expected= 639
    if int(result) != expected:
        return mismatch("/data/c4.txt", expected, result)
    return True

async def c5(email, external_port,**kwargs):
    await run(
        "Does the statement 'I hate you' have a positive or negative connotation? Reply as a single string containing either 'POSITIIVE' or 'NEGATIVE' in uppercase. Save the result to /data/c5.txt",
        external_port=external_port
    )
    result = await read("/data/c5.txt", external_port=external_port)
    expected= "NEGATIVE"
    if result != expected:
        return mismatch("/data/c5.txt", expected, result)
    return True


async def main(email: str, external_port: str, token_counter: str):
    score, total = 0, 0
    for task in [a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, c1, c2, c3, c4, c5]:
        total += 1
        try:
            if task == b8 : 
                success = await task(email=email, external_port=external_port, token_counter=token_counter)
            else :
                success = await task(email=email, external_port=external_port)

        except Exception as e:
            logging.error(f"🔴 {task.__name__.upper()} failed: {e}")
            success = False
        if success:
            logging.info(f"✅ {task.__name__.upper()} PASSED")
        else:
            logging.error(f"❌ {task.__name__.upper()} FAILED")
        score += 1 if success else 0
    logging.info(f"🎯 Score: {score} / {total}")

    response = httpx.post(
        "https://aiproxy.sanand.workers.dev/openai/v1/embeddings",
        headers={"Authorization": f"Bearer {openai_api_key}"},
        json={
            "model": "text-embedding-3-small",
            "input":["A"]
        },
    )
    if response.status_code != 200:
        logging.error(f"🔴 Failed to send request to OpenAI API: {response.status_code}")
        sys.exit(244)

if __name__ == "__main__":
    import asyncio
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate tasks with configurable logging")
    parser.add_argument("--email", default="user@example.com", help="Set the email address")
    parser.add_argument("--external_port",default=8001)
    parser.add_argument("--token_counter")
    levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    parser.add_argument("--log-level", default="INFO", choices=levels, help="Set logging level")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level, format="%(message)s\n")
    asyncio.run(main(args.email, args.external_port,args.token_counter))
