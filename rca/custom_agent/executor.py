import json
import re

from rca.api_router import get_chat_completion
from rca.custom_agent.tools import TOOLS

system = """You are a DevOps assistant for failure diagnosis. You can only use the provided tools to inspect telemetry files and logs.

{rule}

There is some domain knowledge for you:

{background}

Your response should follow the tool call format below:

{format}"""

format = """{
    "tool_name": "list_files | read_file | grep_log",
    "tool_args": { "key": "value" }
}
(DO NOT contain "```json" and "```" tags. DO contain the JSON object with the brackets "{}" only. Use '\\n' instead of an actual newline character to ensure JSON compatibility when you want to insert a line break within a string.)"""

rule = """## RULES OF TOOL USAGE:

1. Only call the tools that are explicitly listed in the format.
2. Keep each tool call atomic. Request only one tool per step.
3. Use the telemetry schema to decide which files or logs to inspect.
4. Never fabricate file contents. Always rely on tool outputs."""


def _extract_json(text: str) -> tuple[dict | None, str]:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None, text
    raw = match.group(0)
    try:
        return json.loads(raw), raw
    except json.JSONDecodeError:
        return None, text


def execute_act(instruction: str, background: str, history, attempt, logger):
    logger.debug("Start execution")
    if history == []:
        history = [
            {
                "role": "system",
                "content": system.format(rule=rule, background=background, format=format),
            },
        ]

    prompt = history + [{"role": "user", "content": instruction}]
    note = [
        {
            "role": "user",
            "content": f"Continue your tool-usage process following the rules:\n\n{rule}\n\nResponse format:\n\n{format}",
        }
    ]

    for _ in range(2):
        response = get_chat_completion(
            messages=prompt + note,
        )
        logger.debug(f"Raw Tool Response:\n{response}")
        payload, raw = _extract_json(response)
        if not payload:
            prompt.append({"role": "assistant", "content": response})
            prompt.append(
                {
                    "role": "user",
                    "content": "Invalid tool JSON. Please respond with the required JSON object.",
                }
            )
            continue

        tool_name = payload.get("tool_name")
        tool_args = payload.get("tool_args", {})
        tool = TOOLS.get(tool_name)
        if not tool:
            result = json.dumps({"error": f"Unknown tool: {tool_name}"})
            history.extend(
                [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": result},
                ]
            )
            return raw, result, True, history

        try:
            result = tool(**tool_args)
        except TypeError as exc:
            result = json.dumps({"error": f"Tool args invalid: {exc}"})

        history.extend(
            [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": result},
            ]
        )
        return raw, result, True, history

    err = "The Executor failed to complete the instruction, please re-write a new instruction for Executor."
    history.extend([{"role": "assistant", "content": err}])
    return err, err, True, history
