from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
import os
import json
import subprocess
import logging
from pathlib import Path
from openai import OpenAI
from datetime import datetime

app = FastAPI()

# Directory Setup
DATA_DIR = Path("/data")
LOG_DIR = DATA_DIR / "logs"
ERROR_LOG = DATA_DIR / "error.log"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Logging Configuration
logging.basicConfig(
    filename=LOG_DIR / "app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# OpenAI Setup
openai_api_base = os.getenv("OPENAI_API_CHAT", "https://aiproxy.sanand.workers.dev/openai/v1")
openai_api_key = os.getenv("AIPROXY_TOKEN")
if not openai_api_key:
    raise RuntimeError("AIPROXY_TOKEN environment variable not set.")

client = OpenAI(api_key=openai_api_key, base_url=openai_api_base)

# Secure path enforcement
def ensure_local_path(path: str) -> str:
    base = DATA_DIR.resolve()
    target = (base / path).resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(status_code=403, detail="Access denied.")
    return str(target)

# Prompt Template
CODE_GENERATION_PROMPT = """
You are an AI assistant capable of generating Python or Bash code to accomplish user tasks described in natural language (including multilingual and informal expressions). Your role is to understand the task, identify the appropriate type of solution (script or command), and generate secure, efficient code that respects strict file boundaries.

Follow these rules:

1. **Understand the task**: Parse the user input (even if multilingual, informal, or paraphrased) to determine what is required.
2. **Determine the application type**: Choose between "python" or "bash" depending on which is more appropriate.
3. **Generate appropriate code**:
   - Ensure the code is efficient, readable, and follows best practices.
   - Include comments where helpful.
4. **Security Constraints**:
   - **Never access or read files outside the `/data` directory.**
   - **Never delete any file under any circumstances.**
5. **File Handling Rules**:
   - Input and output files must be read from or written to the `/data` directory only.
   - Respect formatting and indentation of file contents when writing output.
   - Handle multilingual content and date formats (e.g., `day-month-year`, ISO, datetime).
6. **Robustness & Error Handling**:
   - Handle errors gracefully using try-except blocks or conditional checks.
   - Log errors to `/data/error.log` if exceptions occur.
7. **Install Dependencies If Needed**:
   - If a package (e.g., `prettier`, `requests`, `openai`, etc.) is required, include installation code or checks.
8. **LLM Usage**:
   - When a task requires content extraction or reasoning (e.g., parsing an email, OCR, embeddings), include a function that calls a generic `call_llm(prompt)` method and handles its output securely.
9. **Examples of Supported Tasks**:
   - **Phase A (Operations)**: Installing packages, formatting markdown, date counting (across languages), sorting JSON, indexing docs, querying SQLite, comparing text similarity, handling images and OCR, extracting metadata using LLMs.
   - **Phase B (Business)**: API requests, git repo manipulation, database queries, scraping, media processing (image/audio), markdown-to-HTML conversion, API route creation.
10. **Example Input Variation Handling**:
   - Detect requests like: "Count Sundays in /data/x.log", or "எத்தனை திங்கள் இருக்குனு கணக்கு போடு", or "how many mercredi are there" and process accordingly using locale-aware date parsing.
11. **ALWAYS output your result in the following JSON format**:

{
    "application_type": "python" or "bash",
    "code": "Generated code here"
}
"""

@app.post("/run")
async def run_task(task: str = Query(...)):
    max_attempts = 2
    attempt = 0

    while attempt < max_attempts:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": CODE_GENERATION_PROMPT},
                    {"role": "user", "content": task}
                ],
                temperature=0.2,
                timeout=20
            )

            generated_content = response.choices[0].message.content.strip()
            if not generated_content:
                raise ValueError("Empty response from OpenAI API")

            generated_json = json.loads(generated_content)
            application_type = generated_json["application_type"]
            code = generated_json["code"]

            if application_type == "python":
                result = subprocess.run(["python", "-c", code], capture_output=True, text=True, check=True)
            elif application_type == "bash":
                bash_check = subprocess.run(["where", "bash"], capture_output=True, text=True)
                if bash_check.returncode != 0:
                    raise HTTPException(status_code=500, detail="Bash is not available. Install Git Bash or WSL.")
                result = subprocess.run(["bash", "-c", code], capture_output=True, text=True, check=True)
            else:
                raise ValueError(f"Unsupported application type: {application_type}")

            output = {
                "status": "success",
                "output": result.stdout.strip(),
                "error": result.stderr.strip()
            }

            with open(LOG_DIR / "last_result.log", "w", encoding="utf-8") as f:
                f.write(json.dumps({
                    "task": task,
                    "application_type": application_type,
                    "code": code,
                    "output": output
                }, indent=2))

            logging.info(f"Task succeeded: {task}")
            return output

        except subprocess.CalledProcessError as e:
            logging.error(f"Subprocess error: {e.stderr}")
            attempt += 1
            if attempt >= max_attempts:
                with open(ERROR_LOG, "a", encoding="utf-8") as ef:
                    ef.write(f"{datetime.now()} - Subprocess error: {e.stderr}\n")
                raise HTTPException(status_code=500, detail=f"Task execution failed: {e.stderr}")
            task = (
                f"The previous attempt failed. Please fix the code and try again.\n"
                f"Task: {task}\nGenerated Code: {code}\nError: {e.stderr}"
            )

        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            with open(ERROR_LOG, "a", encoding="utf-8") as ef:
                ef.write(f"{datetime.now()} - JSON decode error: {e}\n")
            raise HTTPException(status_code=500, detail="Invalid JSON from OpenAI response")

        except Exception as e:
            logging.exception("Unhandled exception occurred")
            with open(ERROR_LOG, "a", encoding="utf-8") as ef:
                ef.write(f"{datetime.now()} - General exception: {str(e)}\n")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/read")
async def read_file(path: str):
    try:
        safe_path = ensure_local_path(path)
        with open(safe_path, "r", encoding="utf-8") as file:
            return PlainTextResponse(file.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logging.error(f"Read error: {e}")
        with open(ERROR_LOG, "a", encoding="utf-8") as ef:
            ef.write(f"{datetime.now()} - Read error: {str(e)}\n")
        raise HTTPException(status_code=500, detail=str(e))
