# parser.py (compact, attempts only allowed shapes)
import json
import os
import re
from dotenv import load_dotenv
import requests
import inspect

load_dotenv()
KEY = (
    os.getenv("NVIDIA_API_KEY")
    or os.getenv("NEMOTRON_API_KEY")
    or os.getenv("AI_API_KEY")
)
MODEL_NAME = os.getenv("NVIDIA_MODEL", "nvidia/llama-3.3-nemotron-super-49b-v1.5")
API_BASE_URL = os.getenv("NVIDIA_API_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
DATA_FILE = os.path.join(os.path.dirname(__file__), "data.metta")

SCHEMA = ('Reply with ONLY one JSON object like: '
          '{"subject":<string|null>,"relation":"any"|"Friend"|"Colleague"|"Family"|"Neighbor"|"Classmate",'
          '"target_attribute":{"type":"Profession"|"Hobby","value":"<string>"},"max_depth":<int>}')

RELATIONS = ["Friend", "Colleague", "Family", "Neighbor", "Classmate"]
ATTRIBUTE_TYPES = ["Profession", "Hobby"]

EXISTS_PATTERNS = (
    r"\bis there\b",
    r"\bdo i know\b",
    r"\bdo i have\b",
    r"\bare there\b",
)

LIST_PATTERNS = (
    r"\bwho\b",
    r"\bfind\b",
    r"\blist\b",
    r"\bshow\b",
)

def _detect_question_type(text):
    if any(re.search(pattern, text) for pattern in EXISTS_PATTERNS):
        return "exists"
    if any(re.search(pattern, text) for pattern in LIST_PATTERNS):
        return "list"
    return "list"

# {
#     "question_type": question_type,
#     "subject": subject,
#     "relation": relation,
#     "target_attribute": {...},
#     "max_depth": ...
# }

def _load_known_terms():
    known_people = set()
    known_attributes = {attr_type: set() for attr_type in ATTRIBUTE_TYPES}

    if not os.path.exists(DATA_FILE):
        return known_people, known_attributes

    with open(DATA_FILE, "r") as f:
        for raw_line in f:
            match = re.match(r"^\(\s*([A-Za-z_]+)\s+([A-Za-z_]+)\s+([A-Za-z_]+)\s*\)", raw_line.strip())
            if not match:
                continue

            predicate, first, second = match.groups()
            if predicate in RELATIONS:
                known_people.update([first, second])
            elif predicate in ATTRIBUTE_TYPES:
                known_people.add(first)
                known_attributes[predicate].add(second)

    return known_people, known_attributes


KNOWN_PEOPLE, KNOWN_ATTRIBUTES = _load_known_terms()


def _find_known_value(text, values):
    matches = []
    for value in values:
        match = re.search(rf"\b{re.escape(value.lower())}\b", text)
        if match:
            matches.append((match.start(), value))
    if not matches:
        return None
    return sorted(matches)[0][1]


def _extract_max_depth(text):
    match = re.search(r"(?:within|up to|max(?:imum)? depth|depth|hops?)\D*(\d+)", text)
    if match:
        return max(1, min(5, int(match.group(1))))
    if any(word in text for word in ("direct", "close", "immediate")):
        return 1
    return 2


def _parse_question_locally(q, assumed_subject=None):
    text = q.lower()
    question_type = _detect_question_type(text)

    relation = "any"
    for rel in RELATIONS:
        rel_text = rel.lower()
        if re.search(rf"\b{rel_text}s?\b", text):
            relation = rel
            break

    subject = _find_known_value(text, KNOWN_PEOPLE) or assumed_subject

    if not subject:
        return None

    profession = _find_known_value(text, KNOWN_ATTRIBUTES["Profession"])
    hobby = _find_known_value(text, KNOWN_ATTRIBUTES["Hobby"])

    if "hobby" in text or "play" in text or "likes" in text or "like " in text:
        attr_type, attr_value = "Hobby", hobby
    else:
        attr_type, attr_value = "Profession", profession or hobby
        if hobby and not profession:
            attr_type = "Hobby"

    if not attr_value:
        return None

    return {
        "question_type": question_type,
        "subject": subject,
        "relation": relation,
        "target_attribute": {"type": attr_type, "value": attr_value},
        "max_depth": _extract_max_depth(text),
    }

def _call(prompt):
    if not KEY:
        raise RuntimeError("NVIDIA_API_KEY missing and the local parser could not understand this question")

    try:
        response = requests.post(
            f"{API_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL_NAME,
                "messages": [
                    {
                        "role": "system",
                        "content": "You convert natural-language questions into compact JSON for a graph search application.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
                "max_tokens": 300,
                "stream": False,
            },
            timeout=30,
        )
    except requests.RequestException as error:
        raise RuntimeError(f"NVIDIA API request failed: {error}") from error

    if response.status_code >= 400:
        details = response.text.strip()
        raise RuntimeError(
            f"NVIDIA API request failed with status {response.status_code}: {details}"
        )

    return response.json()

def _txt(resp):
    if isinstance(resp, dict):
        choices = resp.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                if text_parts:
                    return "".join(text_parts)
        if "text" in resp:
            return str(resp["text"])
    return str(resp)

def parse_question_to_json(q, assumed_subject):
    if not q or not q.strip():
        raise ValueError("Empty question")
    parsed = _parse_question_locally(q, assumed_subject=assumed_subject)
    if parsed:
        return parsed

    prompt = SCHEMA + "\n\nUser question: " + (f"(Assume subject: {assumed_subject}) " if assumed_subject else "") + q.strip()
    resp = _call(prompt)
    text = _txt(resp).strip()
    i, j = text.find("{"), text.rfind("}")
    if i == -1 or j == -1 or j <= i:
        raise ValueError("No JSON in model output:\n" + text)
    parsed = json.loads(text[i:j+1])
    parsed["subject"] = parsed.get("subject") or assumed_subject
    parsed["question_type"] = parsed.get("question_type") or _detect_question_type(q.lower())
    parsed["max_depth"] = max(1, min(5, int(parsed.get("max_depth", 1))))
    return parsed

if __name__ == "__main__":
    tests = [
        "Do I have Family who is a doctor in my network?",
        "Is there a nurse within 2 hops from me?"
    ]
    for q in tests:
        print("Q:", q)
        try:
            print(json.dumps(parse_question_to_json(q, assumed_subject="Alice"), indent=2))
        except Exception as e:
            print("Error:", e)
