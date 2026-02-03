"""Custom planning agent aligned with OpenRCA benchmark output."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from rca.api_router import get_chat_completion
from rca.custom_agent.tools import TOOLS


SYSTEM_PROMPT = """You are a senior SRE investigating incidents in the OpenRCA dataset.

## Goals
- Use the provided telemetry schema to guide data retrieval.
- Use tools to inspect logs or files when needed.
- Produce the final answer in the OpenRCA JSON format.

## Available tools
- list_files(directory): list files in a directory
- read_file(file_path): read a file's content
- grep_log(log_file, keyword, context_lines=2): search keyword in logs

## Tool call format (JSON only)
{{"action": "tool", "tool_name": "...", "tool_args": {{"key": "value"}}}}

## Final answer format (JSON only)
{{"action": "final", "answer": "<OpenRCA JSON answer>"}}

## OpenRCA JSON answer format
```json
{{
  "1": {{
    "root cause occurrence datetime": "YYYY-MM-DD HH:MM:SS",
    "root cause component": "<component from candidates>",
    "root cause reason": "<reason from candidates>"
  }}
}}
```
If the issue requires multiple failures, use "2", "3", etc.
Only include fields requested by the issue.
"""


@dataclass
class AgentResponse:
    prediction: str
    trajectory: List[Dict[str, str]]
    prompt: List[Dict[str, str]]


class CustomAgent:
    def __init__(self, basic_prompt) -> None:
        self.basic_prompt = basic_prompt

    def _build_system_prompt(self) -> str:
        return f"{SYSTEM_PROMPT}\n\n## Telemetry schema\n{self.basic_prompt.schema}\n\n## Candidates\n{self.basic_prompt.cand}\n"

    def _extract_json(self, text: str) -> Tuple[Dict[str, str] | None, str]:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None, text
        raw = match.group(0)
        try:
            return json.loads(raw), raw
        except json.JSONDecodeError:
            return None, text

    def run(self, instruction: str, logger, max_step: int = 10) -> AgentResponse:
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": instruction},
        ]
        trajectory: List[Dict[str, str]] = []

        for step in range(max_step):
            response = get_chat_completion(messages=messages)
            logger.info(f"Agent response (step {step + 1}): {response}")
            payload, raw = self._extract_json(response)
            if not payload:
                messages.append(
                    {
                        "role": "user",
                        "content": "Your response must be JSON with action=tool or action=final.",
                    }
                )
                trajectory.append({"step": str(step + 1), "raw": raw})
                continue

            action = payload.get("action")
            if action == "tool":
                tool_name = payload.get("tool_name")
                tool_args = payload.get("tool_args", {})
                tool = TOOLS.get(tool_name)
                if not tool:
                    tool_result = json.dumps({"error": f"Unknown tool: {tool_name}"})
                else:
                    tool_result = tool(**tool_args)
                messages.append({"role": "assistant", "content": raw})
                messages.append(
                    {
                        "role": "user",
                        "content": f"Tool result for {tool_name}: {tool_result}",
                    }
                )
                trajectory.append(
                    {
                        "step": str(step + 1),
                        "tool": tool_name or "unknown",
                        "tool_args": json.dumps(tool_args),
                        "result": tool_result,
                    }
                )
                continue
            if action == "final":
                answer = payload.get("answer", "")
                return AgentResponse(
                    prediction=answer,
                    trajectory=trajectory,
                    prompt=messages,
                )

            messages.append(
                {
                    "role": "user",
                    "content": "Invalid action. Use action=tool or action=final only.",
                }
            )
            trajectory.append({"step": str(step + 1), "raw": raw})

        fallback = '{"1": {"root cause component": "UNKNOWN", "root cause reason": "UNKNOWN"}}'
        return AgentResponse(
            prediction=fallback,
            trajectory=trajectory,
            prompt=messages,
        )
