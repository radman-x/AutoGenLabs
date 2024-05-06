# !!rm -- Experiment to use StateFlow to control StateMachine orchestrator.
# ruff: noqa: E722
from string import Template
from typing import Dict, List, Optional, TypedDict
# import logging


class OrchestratorPromptTemplates(TypedDict):
    closed_book_prompt: Template
    plan_prompt: Template
    step_prompt: Template
    team_update: Template
    rethink_facts: Template
    new_plan: Template
    quantifier_sys_message: Template


defaultPromptTemplates: OrchestratorPromptTemplates = {
    "closed_book_prompt": Template(
        """Below I will present you a request. Before we begin addressing the request, please answer the following pre-survey to the best of your ability. Keep in mind that you are Ken Jennings-level with trivia, and Mensa-level with puzzles, so there should be a deep well to draw from.

Here is the request:

$task

Here is the pre-survey:

    1. Please list any specific facts or figures that are GIVEN in the request itself. It is possible that there are none.
    2. Please list any facts that may need to be looked up, and WHERE SPECIFICALLY they might be found. In some cases, authoritative sources are mentioned in the request itself.
    3. Please list any facts that may need to be derived (e.g., via logical deduction, simulation, or computation)
    4. Please list any facts that are recalled from memory, hunches, well-reasoned guesses, etc.

When answering this survey, keep in mind that "facts" will typically be specific names, dates, statistics, etc. Your answer should use headings:

    1. GIVEN OR VERIFIED FACTS
    2. FACTS TO LOOK UP
    3. FACTS TO DERIVE
    4. EDUCATED GUESSES
"""
    ),
    "plan_prompt": Template(
        """Fantastic. To address this request we have assembled the following team:

$team

Based on the team composition, and known and unknown facts, please devise a short bullet-point plan for addressing the original request. Remember, there is no requirement to involve all team members -- a team member's particular expertise may not be needed for this task."""
    ),
    "step_prompt": Template(
        """
Recall we are working on the following request:

$task

And we have assembled the following team:

$team

To make progress on the request, please answer the following questions, including necessary reasoning:

$bullet_points

Please output an answer in pure JSON format according to the following schema. The JSON object must be parsable as-is. DO NOT OUTPUT ANYTHING OTHER THAN JSON, AND DO NOT DEVIATE FROM THIS SCHEMA:

$json_schema
"""
    ),
    "team_update": Template(
        """
We are working to address the following user request:

$task


To answer this request we have assembled the following team:

$team
"""
    ),
    #     "team_update": Template(
    #         """
    # We are working to address the following user request:
    # $task
    # To answer this request we have assembled the following team:
    # $team
    # Some additional points to consider:
    # $facts
    # $plan
    # """
    #     ),
    "rethink_facts": Template(
        """It's clear we aren't making as much progress as we would like, but we may have learned something new. Please rewrite the following fact sheet, updating it to include anything new we have learned. This is also a good time to update educated guesses (please add or update at least one educated guess or hunch, and explain your reasoning). 

$prev_facts
"""
    ),
    "new_plan": Template(
        """Please come up with a new plan expressed in bullet points. Keep in mind the following team composition, and do not involve any other outside people in the plan -- we cannot contact anyone else.

Team membership:
$team
"""
    ),
    "quantifier_sys_message": Template(
        """You are a helpful assistant. You quantify the output of different tasks based on the given criteria. 
        The criterion is given in a dictionary format where each key is a distinct criteria. 
        The value of each key is a dictionary as follows {"description": criteria description , "accepted_values": possible accepted inputs for this key} 
        You are going to quantify each of the criteria for a given task based on the task description. 
        Return a dictionary where the keys are the criteria and the values are the assessed performance based on accepted values for each criteria. 
        Return only the dictionary.
"""
    ),
}
