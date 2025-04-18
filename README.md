# TDS Project 1 - LLM-based Automation Agent-2

🧠 Description
This agent is entirely driven by a Large Language Model (LLM) that autonomously generates Python functions based on plain-English task descriptions received via API. Instead of matching to pre-written functions, the LLM interprets, writes, and executes code on-the-fly to fulfill the task requirements—making the system flexible, creative, and capable of handling previously unseen instructions.

---

## 🌐 API Endpoints

### 🔹 POST `/run?task=<task description>`

Executes a plain-English task using the agent's internal logic and LLM parsing.

- **200 OK** – Task successfully completed
- **400 Bad Request** – Malformed or unrecognized task
- **500 Internal Server Error** – Agent failed to complete the task due to internal error
- **Response Body** – May include additional info depending on outcome

### 🔹 GET `/read?path=<file path>`

Reads and returns the contents of the specified file.

- **200 OK** – Returns the file contents as plain text
- **404 Not Found** – File not found

---

## 🧪 Phase A Tasks

| Task          | Description                                                                                                     |
| ------------- | --------------------------------------------------------------------------------------------------------------- |
| **A1**  | Install `uv` and run `datagen.py` with `21f3001076@ds.study.iitm.ac.in`                                   |
| **A2**  | Format `/data/format.md` using `prettier@3.4.2`                                                             |
| **A3**  | Count Wednesdays in `/data/dates.txt` and write to `/data/dates-wednesdays.txt`                             |
| **A4**  | Sort contacts in `/data/contacts.json` and save to `/data/contacts-sorted.json`                             |
| **A5**  | Write the first line of 10 most recent `.log` files in `/data/logs/` to `/data/logs-recent.txt`           |
| **A6**  | Create `/data/docs/index.json` mapping filenames to H1 titles from Markdown files                             |
| **A7**  | Extract sender’s email from `/data/email.txt` and save to `/data/email-sender.txt`                         |
| **A8**  | Extract credit card number from `/data/credit-card.png` and save to `/data/credit-card.txt`                 |
| **A9**  | Find most similar comment pair from `/data/comments.txt` and write to `/data/comments-similar.txt`          |
| **A10** | Calculate total "Gold" ticket sales from `/data/ticket-sales.db` and write to `/data/ticket-sales-gold.txt` |

---

## 🛡️ Phase B - Security Constraints

The agent must enforce the following **non-negotiable constraints** for data safety:

- **B1.** Access only data within `/data` directory
- **B2.** Never delete any file under any condition

---

## 🚀 Phase B - Additional Functionalities

Support the following higher-level automation tasks:

| Task          | Description                                 |
| ------------- | ------------------------------------------- |
| **B3**  | Fetch data from an API and save it          |
| **B4**  | Clone a git repo and make a commit          |
| **B5**  | Run SQL queries on SQLite or DuckDB         |
| **B6**  | Scrape data from a website                  |
| **B7**  | Compress or resize an image                 |
| **B8**  | Transcribe audio from an MP3 file           |
| **B9**  | Convert Markdown to HTML                    |
| **B10** | Create an API to filter CSV and return JSON |

> 💡 **Bonus:** The agent may receive tasks beyond this list. Successfully executing them earns bonus points!

---

## 🧠 Agent Intelligence

The agent uses an LLM to:

- Parse multilingual and loosely structured instructions
- Infer context and task requirements
- Invoke relevant tools dynamically (e.g., `prettier`, OCR, SQL, git, etc.)
- Ensure safety and correctness of actions

Examples of supported task variations:

- English: "Write the number of Wednesdays in `/data/dates.txt` to `/data/dates-wednesdays.txt`"
- Hindi: "`/data/contents.log` में कितने रविवार हैं? गिनो और `/data/contents.dates` में लिखो"
- Tamil: "`/data/contents.log`ல எத்தனை ஞாயிறு இருக்குனு கணக்கு போட்டு, அதை `/data/contents.dates`ல எழுது"

---

## 🧱 Technologies Used

- **Python**
- **FastAPI**
- **OpenAI or similar LLM APIs**
- **Prettier (via subprocess)**
- **OCR / Embedding Libraries**
- **SQL (SQLite / DuckDB)**
- **Docker**

---


## 🚀 Running the Project

### 🔧 Run Locally

1. **Create a virtual environment**

   ```bash
   python -m venv venv
   ```
2. **Activate the virtual environment & install dependencies**

   ```
   venv\Scripts\Activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt

   ```
3. **Set API token as environment variable (PowerShell)**

   ```
   $env:AIPROXY_TOKEN="YOUR_TOKEN"

   ```
4. **Run the FastAPI application**

   ```
   python -m uvicorn app:app --host 0.0.0.0 --port 8001 --reload
   ```
5. **Data Generation for various Tasks**

   ```
   python datagen.py `<your-email>` --root /data
   ```
6. **Run evaluation script**

   ```
   python -m uv run evaluate.py --email <your-email>
   ```

### 🐳 Run with Docker

#### 📦 Build the Docker image locally

```
docker build --no-cache -t your-username/automation-agent .
```

#### 🔐 Push to Docker Hub

```
docker login
docker tag your-username/automation-agent your-username/automation-agent:latest
docker push your-username/automation-agent:latest
```

#### 🚀 Run the Container and Evaluate

```
docker run -p 8000:8000 -e AIPROXY_TOKEN=$AIPROXY_TOKEN your-username/automation-agent
```

* **Data Generation for various Tasks**
  ```
  python datagen.py `<your-email>` --root /data
  ```
* **Run evaluation script**
  ```
  python -m uv run evaluate.py --email <your-email>

  ```

## ✅ Project Status & Evaluation
* 🧠 The agent uses LLM-generated code to dynamically handle a wide range of tasks from plain-English instructions.

* 🛠️ No predefined task-specific Python functions are stored—the LLM writes them at runtime.

* 📈 Achieved 17 out of 25 successful task completions, indicating promising generalization and reasoning capabilities.

* 📌 Demonstrated strength in:

  * Text and file processing

  * Basic data transformations

  * Command-line tool usage via subprocess

* ⚠️ Still improving on:

  * Tasks requiring multi-step logic

  * External APIs or structured queries (e.g., SQL, OCR, git)

*  🔄 Ongoing enhancements aim to improve reliability, error handling, and security for dynamically executed code.
