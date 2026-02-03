"""Custom planning agent aligned with OpenRCA benchmark output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from rca.custom_agent.controller import control_loop


@dataclass
class AgentResponse:
    prediction: str
    trajectory: List[Dict[str, str]]
    prompt: List[Dict[str, str]]


class CustomAgent:
    def __init__(self, agent_prompt, basic_prompt) -> None:
        self.ap = agent_prompt
        self.bp = basic_prompt

    def run(
        self,
        instruction: str,
        logger,
        max_step: int = 25,
        max_turn: int = 5,
    ) -> AgentResponse:
        prediction, trajectory, prompt = control_loop(
            instruction,
            "",
            self.ap,
            self.bp,
            logger=logger,
            max_step=max_step,
            max_turn=max_turn,
        )

        return AgentResponse(
            prediction=prediction,
            trajectory=trajectory,
            prompt=prompt,
        )
