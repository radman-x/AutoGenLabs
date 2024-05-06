# orchestrator_stateflow.py -- Default StateFlow for Orchestrator
from datetime import datetime
from stateflow import StateFlow
from prompt_templates import OrchestratorPromptTemplates, defaultPromptTemplates
from abstract_orchestrator import AbstractOrchestrator, TemplateUtils
from typing import Dict, List, Optional, Union, Callable
import json
import logging


class DefaultOrchestratorStateFlow(StateFlow):
    """Default StateFlow for Orchestrator. Handles prompts. Also handles anything specific to the style of
        orchestration flow, eg. "facts", "plan-and-solve", etc.
    """
    states: Dict[str, List]
    transitions: Dict[str, Union[str, callable]] = {}
    initial_state: str = None
    final_states: List[str] = []
    max_transitions: int = 10

    orchestrator:AbstractOrchestrator= None
    _prompt_templates: OrchestratorPromptTemplates

    def __init__(self, orchestrator:AbstractOrchestrator):
        self.orchestrator = orchestrator
        self._prompt_templates = defaultPromptTemplates

        # Define states and transitions:
        states= {}
        transitions= {}

        #######################
        ####  State: INIT  ####
        def _analyze_facts(messages, context):
            # Start by writing what we know
            METADATA= context["METADATA"]
            sender= context["sender"]
            closed_book_prompt = self._prompt_templates["closed_book_prompt"].substitute(task=METADATA["task"]).strip()
            METADATA["facts"] = self.orchestrator._think_and_respond(messages, closed_book_prompt, sender)

        def _make_initial_plan(messages, context):
            # Make an initial plan
            METADATA = context["METADATA"]
            sender = context["sender"]
            plan_prompt = self._prompt_templates["plan_prompt"].substitute(team=METADATA["plan"]).strip()
            METADATA["plan"] = self.orchestrator._think_and_respond(messages, plan_prompt, sender)

        states.update({"INIT": [_analyze_facts, _make_initial_plan]})
        transitions.update({"INIT": "OBTAIN_NEXTSTEP"})

        ##################################
        ####  State: OBTAIN_NEXTSTEP  ####
        states.update({"OBTAIN_NEXTSTEP": []})

        def _generate_next_step(messages, context):
            # This is a transition.
            context["total_turns"] = (
                context["total_turns"] + 1
            )  # TODO: even though original implementation did this here, seems it would be better at the end of the "inner loop" in run_chat()?!?
            METADATA = context["METADATA"]
            sender = context["sender"]
            CURRENT_STATE = ""
            try:
                step_prompt = TemplateUtils.generate_next_step_prompt(
                    prompt_template=self._prompt_templates["step_prompt"],
                    criteria_list=context["criteria_list"],
                    task=METADATA["task"],
                    team=METADATA["team"],
                )
                context["next_step"] = self.orchestrator._think_next_step(
                    step_prompt=step_prompt,
                    sender=sender,
                )
                CURRENT_STATE = "PRE_EXECUTION_NEXTSTEP"
            except json.decoder.JSONDecodeError as e:
                # Something went wrong. Restart this loop.
                self.orchestrator._print_thought(str(e))
                CURRENT_STATE = "RESET"
            return CURRENT_STATE

        transitions.update({"OBTAIN_NEXTSTEP": _generate_next_step})

        #########################################
        ####  State: PRE_EXECUTION_NEXTSTEP  ####
        states.update({"PRE_EXECUTION_NEXTSTEP": []})

        def _pre_execution_step(messages, context):
            # This is a transition.
            CURRENT_STATE = "PRE_EXECUTION_NEXTSTEP"
            criteria_list = context["criteria_list"]
            for criteria in criteria_list:
                func = criteria.pre_execute_hook
                if func is None:
                    continue
                logging.info(
                    f"{CURRENT_STATE}: Running {func.__module__}:{func.__name__}"
                )
                print(
                    f"%%% {datetime.now()} orchestrator [state machine] {CURRENT_STATE}: Running {func.__module__}:{func.__name__}"
                )
                CURRENT_STATE = func(CURRENT_STATE, context)

                # hooks are able to early exit, or 'fail' and ask for a reset
                if CURRENT_STATE in ("TERMINATE_TRUE", "RESET", "INTROSPECT_AND_RESET"):
                    logging.info(
                        f"{CURRENT_STATE}: Breaking out of loop; hook caused early exit."
                    )
                    break

            if CURRENT_STATE == "PRE_EXECUTION_NEXTSTEP":
                CURRENT_STATE = "EXECUTE_NEXTSTEP"
            return CURRENT_STATE

        transitions.update({"PRE_EXECUTION_NEXTSTEP": _pre_execution_step})

        ###################################
        ####  State: EXECUTE_NEXTSTEP  ####

        def _execute_step(messages, context):
            # we actually 'execute' the next step
            self.orchestrator._broadcast_next_step_and_request_reply(
                next_prompt=context["next_step"]["instruction_or_question"]["answer"],
                next_speaker=context["next_step"]["next_speaker"]["answer"],
            )

        states.update({"EXECUTE_NEXTSTEP": [_execute_step]})
        transitions.update({"EXECUTE_NEXTSTEP": "POST_EXECUTION_NEXTSTEP"})

        ##########################################
        ####  State: POST_EXECUTION_NEXTSTEP  ####
        states.update({"POST_EXECUTION_NEXTSTEP": []})
        transitions.update({"POST_EXECUTION_NEXTSTEP": "OBTAIN_NEXTSTEP"})

        #######################################
        ####  State: INTROSPECT_AND_RESET  ####

        def _introspect_and_reset(messages, context):
            METADATA = context["METADATA"]
            sender = context["sender"]
            METADATA["facts"], METADATA["plan"] = (
                self.orchestrator._prepare_new_facts_and_plan(
                    facts=METADATA["facts"], sender=sender, team=METADATA["team"]
                )
            )

        states.update({"INTROSPECT_AND_RESET": [_introspect_and_reset]})
        transitions.update({"INTROSPECT_AND_RESET": "RESET"})

        ########################
        ####  State: RESET  ####
        states.update({"RESET": []})
        transitions.update({"RESET": "end"})

        #################################
        ####  State: TERMINATE_TRUE  ####

        def _terminate_true(messages, context):
            print("******* in _terminate_true")  # @@
            pass  # @@
            # @@ ?!? reply = self._quantifier.quantify()
            # @@ ?!? print("*******")
            # @@ ?!? print(reply)

        states.update({"TERMINATE_TRUE": [_terminate_true]})
        transitions.update({"TERMINATE_TRUE": ""})

        ######################
        ####  State: end  ####
        states.update({"end": []})
        transitions.update({"end": ""})

        super().__init__(states, transitions, initial_state="INIT", final_states=["end"], 
                         max_transitions= self.max_transitions)
