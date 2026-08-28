import gradio as gr
import json
import os
import re
from src.text_to_json_parser import parse_question_to_json, _call, _txt
from src.utils import find_by_json

USE_LLM_ANSWER = os.getenv("USE_LLM_ANSWER", "false").lower() in {"1", "true", "yes", "on"}


def normalize_results(raw_results, force_depth=1):
    """
    Convert MeTTa raw results into a list of (name, depth) tuples.
    Handles multiple matches per row and can hardcode depth.
    """
    parsed = []
    for row in raw_results:
        if not row:
            continue
        if isinstance(row, tuple) and len(row) == 2:
            name, depth = row
            if force_depth is not None:
                depth = force_depth
            parsed.append((name, depth))
            continue

        for expr in row:  # iterate over all matches in this row
            if isinstance(expr, tuple) and len(expr) == 2:
                name, depth = expr
            else:
                parts = str(expr).strip("()").split()
                if len(parts) >= 1:
                    name = parts[0]
                    depth = parts[1] if len(parts) > 1 else force_depth
                else:
                    continue
            if force_depth is not None:
                depth = force_depth
            parsed.append((name, depth))
    return parsed


def retry_delay_seconds(error_text):
    match = re.search(r"Please retry in ([\d.]+)s", error_text)
    if match:
        return str(round(float(match.group(1))))

    match = re.search(r"retry_delay\s*{\s*seconds:\s*(\d+)", error_text, re.MULTILINE)
    if match:
        return match.group(1)

    return None


def format_llm_error(action, error):
    message = str(error)
    if "429" in message and "quota" in message.lower():
        retry_after = retry_delay_seconds(message)
        wait_text = f" Wait about {retry_after} seconds before trying again." if retry_after else " Wait a bit before trying again."
        return f"{action}: NVIDIA API quota exceeded.{wait_text}"
    return f"{action}: {message}"


def sort_results(results):
    def depth_value(item):
        try:
            return int(item[1])
        except (TypeError, ValueError):
            return 999

    return sorted(results, key=depth_value)


def build_answer(parsed_query, results):
    question_type = parsed_query.get("question_type") or "list"
    subject = parsed_query.get("subject") or "the selected person"
    relation = parsed_query.get("relation") or "any"
    attribute = parsed_query.get("target_attribute") or {}
    attribute_type = str(attribute.get("type") or "attribute").lower()
    attribute_value = attribute.get("value")
    max_depth = parsed_query.get("max_depth")

    attribute_text = f"{attribute_type} {attribute_value}" if attribute_value else f"that {attribute_type}"
    relation_text = "any relationship" if relation == "any" else relation.lower()
    depth_text = f" within {max_depth} hop{'s' if max_depth != 1 else ''}" if max_depth else ""
    network_text = f"in {subject}'s network through {relation_text}{depth_text}"

    if not results:
        if question_type == "exists":
            return f"No, I did not find anyone {network_text} with {attribute_text}."
        return f"I did not find anyone in {subject}'s network with {attribute_text} through {relation_text}{depth_text}."
    if question_type == "exists":
        return (
            f"Yes, I found {len(ordered_results)} match"
            f"{'es' if len(ordered_results) != 1 else ''} "
            f"{network_text} with {attribute_text}: {matches}."
        )
    ordered_results = sort_results(results)
    matches = ", ".join(f"{name} (depth {depth})" for name, depth in ordered_results)
    return f"I found {len(ordered_results)} match{'es' if len(ordered_results) != 1 else ''} in {subject}'s network with {attribute_text}: {matches}."


# --- Chat Function ---
def chat_with_rag(question):
    if not question.strip():
        return "Please enter a question.", ""
    
    # Step 1: Parse into JSON query
    try:
        parsed_query = parse_question_to_json(question, assumed_subject="Alice")
    except Exception as e:
        return format_llm_error("Error parsing question", e), ""
    
    # Step 2: Run search
    raw_results = find_by_json(parsed_query)

    # Step 3: Normalize results and build context
    results = normalize_results(raw_results, force_depth=None)
    if not results:
        context = "No matching people found in the network."
    else:
        context_lines = [f"- {name} (found at depth {depth})" for name, depth in results]
        context = "\n".join(context_lines)

    # Step 4: Generate a friendly answer without spending another Gemini request by default.
    answer_text = build_answer(parsed_query, results)
    if USE_LLM_ANSWER:
        llm_prompt = f"""
You are a helpful assistant.
User asked: "{question}"
Structured query: {json.dumps(parsed_query, indent=2)}

Here is the search result from the database:
{context}

Please provide a concise, user-friendly answer.
If there are multiple people, list them in order of depth (closer first).
Optionally mention the search depth in your answer.
If no results, politely say that none were found.
        """.strip()

        try:
            llm_resp = _call(llm_prompt)
            answer_text = _txt(llm_resp).strip()
        except Exception as e:
            answer_text += "\n\n" + format_llm_error("LLM answer skipped", e)
    
    # Step 5: Sources info
    sources_info = f"Query JSON:\n{json.dumps(parsed_query, indent=2)}"
    if results:
        sources_info += "\n\nMatches:\n" + context

    return answer_text, sources_info

# --- Gradio Interface ---
with gr.Blocks() as demo:
    gr.Markdown("## 🧠 Relationship Network Search")
    gr.Markdown(
        "Ask list or yes/no questions about Alice's network and get answers from the matching search results."
    )

    with gr.Row():
        with gr.Column(scale=3):
            question_input = gr.Textbox(
                label="Enter your question",
                placeholder="e.g., Who in Alice's network is a nurse?",
                lines=2
            )
            submit_btn = gr.Button("Ask")
            clear_btn = gr.Button("Clear")

        with gr.Column(scale=5):
            answer_output = gr.Textbox(label="Answer", lines=6)
            sources_output = gr.Textbox(label="Sources Used", lines=12)

    # Button actions
    submit_btn.click(
        fn=chat_with_rag,
        inputs=question_input,
        outputs=[answer_output, sources_output]
    )

    clear_btn.click(
        fn=lambda: ("", ""),
        inputs=[],
        outputs=[answer_output, sources_output]
    )
    clear_btn.click(
        fn=lambda: "",
        inputs=[],
        outputs=question_input
    )

# --- Launch App ---
if __name__ == "__main__":
    demo.launch()


# "Do I have someone who is a doctor in my network?",
# "Is there a nurse within 2 hops from me?",
# "Who in my connections is a scientist? Max depth 3.",
# "Find classmates who have the hobby 'Chess' up to depth 2."
