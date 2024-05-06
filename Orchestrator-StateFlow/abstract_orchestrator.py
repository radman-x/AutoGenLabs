# abstract_orchestrator.py -- Useful to eliminate circular dependency with StateFlow children and Orchestrator.

# TODO:
#   o Must research multiple inheritance and be sure this will work
#   o Some of the methods below should either be removed from here or converted to "public" convention.
#       Also, some can be implemented here instead of in the Orchestrator implementation class.
#   o Some of the methods can be eliminated by moving them into the StateFlow states.

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from autogen import Agent
from string import Template

class AbstractOrchestrator(ABC):
    """
    An abstract class for state flow orchestration.
    """

    # @abstractmethod
    # def __init__(self):
    #     pass

    @abstractmethod
    def _think_and_respond(self, messages: List[dict], message: str, sender: Optional[Agent]):
        pass

    @abstractmethod
    def _print_thought(self, message):
        pass

    @abstractmethod
    def _think_next_step(self, step_prompt: str, sender: Optional[Agent]):
        pass

    @abstractmethod
    def _broadcast_next_step_and_request_reply(self, next_prompt, next_speaker):
        pass

    @abstractmethod
    def _prepare_new_facts_and_plan(self, facts, sender: Optional[Agent], team):
        """Returns tuple as facts, plan"""
        pass

    # @property
    # @abstractmethod
    # def search(self, query) -> str:
    #     pass


# TODO: move NextStepCriteria and TemplateUtils to StateFlow?!?
@dataclass
class NextStepCriteria:
    name: str
    prompt_msg: str
    answer_spec: str
    pre_execute_hook: Optional[Callable] = None
    post_execute_hook: Optional[Callable] = None

    def to_bullet_point(self):
        return f"    - {self.prompt_msg}"

    def to_json_schema_str(self):
        return f"""    "{self.name}": {{
        "reason": string,
        "answer": {self.answer_spec}
    }}"""


class TemplateUtils:
    @staticmethod
    def generate_next_step_prompt(prompt_template: Template, criteria_list: List[NextStepCriteria], task: str, team: str) -> str:
        bullet_points = "\n".join([criteria.to_bullet_point() for criteria in criteria_list])
        inner_json = ",\n".join([criteria.to_json_schema_str() for criteria in criteria_list])
        json_schema = f"{{\n{inner_json}\n}}"

        step_prompt = prompt_template.substitute(
            task=task, team=team, bullet_points=bullet_points, json_schema=json_schema
        ).strip()
        return step_prompt

    @staticmethod
    def generate_team_update_prompt(prompt_template: Template, task: str, team: str, facts: str, plan: str, **kwargs) -> str:
        return prompt_template.substitute(task=task, team=team, facts=facts, plan=plan).strip()
