import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ALLOWED_CATEGORIES = [
    "Finance", "Marketing", "Technical", "HR", "Legal", "Operations"
]

CLASSIFICATION_SYSTEM = """\
You are the Classification Agent. Read the document and choose EXACTLY ONE category
from the provided list. Respond ONLY in valid JSON format:
{"category": "<chosen_category>"}.
Do not include any explanations.
"""

def classification_user_prompt(document: str) -> str:
    return f"""\
Allowed categories: {ALLOWED_CATEGORIES}

Document:
\"\"\"{document.strip()[:20000]}\"\"\"
"""

TAGGING_SYSTEM = """\
You are the Tagging Agent. You will receive a document and the category chosen by
the Classification Agent. Generate 3–5 concise, specific tags capturing the main ideas.
Respond ONLY in valid JSON format:
{"tags": ["tag1", "tag2", "tag3", ...]}.
No commentary, only JSON.
"""

def tagging_user_prompt(document: str, category: str) -> str:
    return f"""\
Category: {category}

Document:
\"\"\"{document.strip()[:20000]}\"\"\"
"""

def ask_gpt(system_prompt: str, user_prompt: str) -> dict:
    """Send a prompt pair to GPT and return parsed JSON."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        content = response.choices[0].message.content
        start, end = content.find("{"), content.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON found in response")
        json_block = content[start:end+1]
        return json.loads(json_block)
    except Exception as e:
        print(f"❌ Error communicating with GPT: {e}")
        return {}

def classification_agent(document: str) -> str:
    result = ask_gpt(CLASSIFICATION_SYSTEM, classification_user_prompt(document))
    category = result.get("category", "").strip()
    if category not in ALLOWED_CATEGORIES:
        raise ValueError(f"Invalid category returned: {category}")
    return category

def tagging_agent(document: str, category: str) -> list:
    result = ask_gpt(TAGGING_SYSTEM, tagging_user_prompt(document, category))
    tags = result.get("tags", [])
    return [t.lower().strip() for t in tags if t]

def main():
    file_name = input("Enter the file name (must exist in the same directory): ").strip()

    if not os.path.isfile(file_name):
        print(f"❌ File '{file_name}' not found in current directory.")
        return

    with open(file_name, "r", encoding="utf-8") as f:
        document = f.read()

    print("\n🔍 Running Classification Agent...")
    category = classification_agent(document)
    print(f"✅ Category: {category}")

    print("\n🏷️ Running Tagging Agent...")
    tags = tagging_agent(document, category)
    print(f"✅ Tags: {', '.join(tags)}")

    result = {"category": category, "tags": tags}
    print("\n📦 Structured Output (JSON):")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
