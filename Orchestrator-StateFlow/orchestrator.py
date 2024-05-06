# !!rm -- Experiment to use StateFlow to control StateMachine orchestrator.
#
# Design Issues:
#
# * Alternatives for Orchestrator-StateFlow class design:
#   1. Orchestrator <>---1:N--- StateFlow. Implement DefaultOrchestratorStateFlow and other specialized XxxxStateFlows.
#       Define states/transitions either in StateFlow sub-class constructor (typically) or calling client that
#           instantiates a StateFlow.
#       PROS & CONS:
#       + Makes it easy to define and visualize many different XxxxStateFlow strategies.
#   2. XxxOrchestrator <>---1:1--- XxxStateFlow
#      DefaultOrchestrator <>---0:N--- XxxOrchestrator. Orchestrator is a "composite" that can run other Orchestrators.
#       Implement other specialized XxxxOrchestrators.
#       Pass in states/transitions to Orchestrator, defined either in sub-class (typically) or calling client (not typical).
#       PROS & CONS:
#       + Makes it easy to define and visualize many different XxxxStateFlow strategies.
#   3. Eliminate Orchestrator -- just have composite XxxStateFlow that fully implement Orchestrator logic.
#       PROS & CONS:
#       + Makes it easy to define and visualize many different XxxxStateFlow strategies.
#       + Simplified design -- no real need for Orchestrator.
#
# * What is Orchestrator vs. StateFlow?
#       Alt. 1 - Orchestrator: determines next step/state, runs it, including broadcasting to all agents.
#            StateFlow: manages prompts, runs individual states and transitions, determines next step/state?!?
#
# TODO:
#   o [DONE] Refactor:
#       - Research multiple inheritance -- will Orchestrator with multiple inheritances work in Python?
#       - Create AbstractOrchestrator to eliminate circ. depend.
#       - Create separate StateFlow class/file
#       - Create DefaultOrchestratorStateFlow
#   o Create WebResearcherStateFlow:
#       - Core work
#       - Integrate into Orchestrator
#   o Phases:
#       1. Just re-used much of the "large" functions
#       2. Reduce size of functions, try as "semi-declarative" as possible
#   o Try to directly call Orchestrator's generate_reply() instead of using OpenAIWrapper.
#   o See various TODOs throughout code
#   o Re-evaluate using separate StateFlow and XxxStateFlow.
#
#   STATUS: Working

# ruff: noqa: E722
from datetime import datetime
import json
import copy
from string import Template
from dataclasses import dataclass
from typing import Dict, List, Optional, Type, TypeVar, Union, Callable, Literal, Tuple, TypedDict
from autogen import Agent, ConversableAgent, OpenAIWrapper, AssistantAgent
from prompt_templates import OrchestratorPromptTemplates, defaultPromptTemplates
from stateflow import StateFlow
from default_orchestrator_stateflow import DefaultOrchestratorStateFlow
from abstract_orchestrator import AbstractOrchestrator, NextStepCriteria, TemplateUtils
import logging
try:
    from termcolor import colored
except ImportError:
    def colored(x, *args, **kwargs):
        return x


class Quantifier(AssistantAgent):
    def __init__(
        self, name: str, llm_config: Optional[Union[Dict, Literal[False]]], system_message: str = None, **kwargs
    ):
        llm_config = copy.deepcopy(llm_config)
        llm_config["max_retries"] = 10
        if system_message is None:
            system_message = defaultPromptTemplates["quantifier_sys_message"]
        super().__init__(name=name, llm_config=llm_config, system_message=system_message, **kwargs)

    def quantify(self) -> str:
        criterion = {
            "TERMINATE": {
                "description": "If we have a correct answer - is it ok to terminate?",
                "accepted_values": ["Appropriate", "Inappropriate"],
            }
        }
        task = {"question:": "2+2", "answer": "4"}

        quantifyTemplate = Template(
            f"""criterion = $criterion_json
task = $task_json\n"""
        )

        message = {
            "role": "user",
            "content": quantifyTemplate.substitute(criterion_json=json.dumps(criterion), task_json=json.dumps(task)),
            "name": "user",
        }
        reply = self.generate_reply(messages=[message])
        return reply


class DefaultStateMachineTransitions:
    # proc_next_step -> decision_to_terminate -> move to state of termination
    @staticmethod
    def decision_to_terminate(CURRENT_STATE: str, context: Dict):
        next_step = context["next_step"]
        if next_step["is_request_satisfied"]["answer"]:
            # return True, "TERMINATE"
            CURRENT_STATE = "TERMINATE_TRUE"
        return CURRENT_STATE

    # proc_next_step -> update_local_state -> continue/reset_current_run_with_introspect
    @staticmethod
    def stall_update_and_check(CURRENT_STATE: str, context: Dict):
        next_step = context["next_step"]
        if "stalled_count" not in context:
            context["stalled_count"] = 0

        if next_step["is_progress_being_made"]["answer"]:
            context["stalled_count"] -= 1
            context["stalled_count"] = max(context["stalled_count"], 0)
        else:
            context["stalled_count"] += 1

        if context["stalled_count"] >= 3:
            # facts, plan = self._prepare_new_facts_and_plan(facts=facts, sender=sender, team=team)
            # break
            CURRENT_STATE = "INTROSPECT_AND_RESET"
        return CURRENT_STATE


class Orchestrator(ConversableAgent, AbstractOrchestrator):
    active_fsms: List[StateFlow] = []   # TODO: make active_orchestrators?!?
    # state_history: List[str] = []

    def __init__(
        self,
        name: str,
        agents: List[ConversableAgent] = [],
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "TERMINATE",
        function_map: Optional[Dict[str, Callable]] = None,
        code_execution_config: Union[Dict, Literal[False]] = False,
        llm_config: Optional[Union[Dict, Literal[False]]] = False,
        default_auto_reply: Optional[Union[str, Dict, None]] = "",
        prompt_templates: OrchestratorPromptTemplates = defaultPromptTemplates,
        quantifier: Quantifier = None,
        max_turns: int = 10,   # 30?,
        state_flow_cls = None
    ):
        super().__init__(
            name=name,
            system_message="",
            is_termination_msg=is_termination_msg,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            function_map=function_map,
            code_execution_config=code_execution_config,
            llm_config=llm_config,
            default_auto_reply=default_auto_reply,
        )

        self._agents = agents
        self.orchestrated_messages = []

        # NOTE: Async reply functions are not yet supported with this contrib agent
        self._reply_func_list = []
        self.register_reply([Agent, None], Orchestrator.run_chat)
        self.register_reply([Agent, None], ConversableAgent.generate_code_execution_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_function_call_reply)
        self.register_reply([Agent, None], ConversableAgent.check_termination_and_human_reply)

        self._prompt_templates = prompt_templates

        self._quantifier: Quantifier = quantifier
        self.max_turns= max_turns
        
        if state_flow_cls:
            self.active_fsms.append(state_flow_cls(self))
        else:
            self.active_fsms.append(DefaultOrchestratorStateFlow(self))

    def _print_thought(self, message):
        print(self.name + " (thought)\n")
        print(message.strip() + "\n")
        print("\n", "-" * 80, flush=True, sep="")

    def _broadcast(self, message, out_loud=[], exclude=[]):
        m = copy.deepcopy(message)
        m["role"] = "user"
        for a in self._agents:
            if a in exclude or a.name in exclude:
                continue
            if a in out_loud or a.name in out_loud:
                self.send(message, a, request_reply=False, silent=False)
            else:
                self.send(message, a, request_reply=False, silent=True)

    def _think_and_respond(self, messages: List[dict], message: str, sender: Optional[Agent]):
        # TODO: Can't we just use ConversableAgent's generate_reply() like _enter_state() does here?
        messages.append({"role": "user", "content": message, "name": sender.name})

        response = self.client.create(
            messages=messages,
            cache=self.client_cache,
        )
        extracted_response = self.client.extract_text_or_completion_object(response)[0]
        messages.append({"role": "assistant", "content": extracted_response, "name": self.name})
        return extracted_response

    def _think_next_step(self, step_prompt: str, sender: Optional[Agent]):
        # This is a temporary message we will immediately pop
        self.orchestrated_messages.append({"role": "user", "content": step_prompt, "name": sender.name})
        response = self.client.create(
            messages=self.orchestrated_messages,
            cache=self.client_cache,
            response_format={"type": "json_object"},
        )
        self.orchestrated_messages.pop()

        extracted_response = self.client.extract_text_or_completion_object(response)[0]
        next_step = json.loads(extracted_response)
        self._print_thought(json.dumps(next_step, indent=4))
        return next_step

    def _prepare_new_facts_and_plan(self, facts, sender: Optional[Agent], team):
        self._print_thought("We aren't making progress. Let's reset.")
        new_facts_prompt = self._prompt_templates["rethink_facts"].substitute(prev_facts=facts).strip()
        facts = self._think_and_respond(self.orchestrated_messages, new_facts_prompt, sender)

        new_plan_prompt = self._prompt_templates["new_plan"].substitute(team=team).strip()
        self.orchestrated_messages.append({"role": "user", "content": new_plan_prompt, "name": sender.name})
        response = self.client.create(
            messages=self.orchestrated_messages,
            cache=self.client_cache,
        )

        # plan is an exception - we dont log it as a message
        plan = self.client.extract_text_or_completion_object(response)[0]

        return facts, plan

    def _broadcast_next_step_and_request_reply(self, next_prompt, next_speaker):
        # Broadcast the message to all agents
        m = {"role": "user", "content": next_prompt, "name": self.name}
        if m["content"] is None:
            m["content"] = ""
        self._broadcast(m, out_loud=[next_speaker])

        # Keep a copy
        m["role"] = "assistant"
        self.orchestrated_messages.append(m)

        # Request a reply
        for a in self._agents:
            if a.name == next_speaker:
                reply = {"role": "user", "name": a.name, "content": a.generate_reply(sender=self)}
                self.orchestrated_messages.append(reply)
                a.send(reply, self, request_reply=False)
                self._broadcast(reply, exclude=[a])
                break

    def _update_team_with_facts_and_plan(self, team_update_prompt: str):
        self.orchestrated_messages.append({"role": "assistant", "content": team_update_prompt, "name": self.name})
        self._broadcast(self.orchestrated_messages[-1])
        self._print_thought(self.orchestrated_messages[-1]["content"])

    def run_chat(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[OpenAIWrapper] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        # We should probably raise an error in this case.
        if self.client is None:
            return False, None

        if messages is None:
            messages = self._oai_messages[sender]

        # Work with a copy of the messages
        _messages = copy.deepcopy(messages)

        ##### Memory ####

        METADATA = {}

        # Pop the last message, which is the task
        METADATA["task"] = _messages.pop()["content"]

        # A reusable description of the team
        METADATA["team"] = "\n".join([a.name + ": " + a.description for a in self._agents])
        METADATA["names"] = ", ".join([a.name for a in self._agents])

        # TODO: These next two should be moved into DefaultOrchestratorStateFlow.
        # A place to store relevant facts
        METADATA["facts"] = ""

        # A place to store the plan
        METADATA["plan"] = ""

        # Main loop
        state_flow= self.active_fsms.pop()
        state_flow.check_states()
        verbose= True   # @@ TODO: Make class mem?

        # Setup function context
        context = {}
        # Future TODO: move these prompts to prompt_templates?
        criteria_list = [
            NextStepCriteria(
                name="is_request_satisfied",
                prompt_msg="Is the request fully satisfied? (True if complete, or False if the original request has yet to be SUCCESSFULLY addressed)",
                answer_spec="boolean",
                pre_execute_hook=DefaultStateMachineTransitions.decision_to_terminate,
            ),
            NextStepCriteria(
                name="is_progress_being_made",
                prompt_msg="Are we making forward progress? (True if just starting, or recent messages are adding value. False if recent messages show evidence of being stuck in a reasoning or action loop, or there is evidence of significant barriers to success such as the inability to read from a required file)",
                answer_spec="boolean",
                pre_execute_hook=DefaultStateMachineTransitions.stall_update_and_check,
            ),
            NextStepCriteria(
                name="next_speaker",
                prompt_msg=f"Who should speak next? (select from: {METADATA['names']})",
                answer_spec=f"string (select from: {METADATA['names']})",
            ),
            NextStepCriteria(
                name="instruction_or_question",
                prompt_msg="What instruction or question would you give this team member? (Phrase as if speaking directly to them, and include any specific information they may need)",
                answer_spec="string",
            ),
        ]
        context["criteria_list"] = criteria_list
        context["sender"] = sender
        context["METADATA"] = METADATA

        total_turns = 0
        while total_turns < self.max_turns:  # ?!? TODO: Should this be moved into DefaultOrchestratorStateFlow? Probably...

            # Populate the message histories
            self.orchestrated_messages = []
            for a in self._agents:
                a.reset()

            # Equivalent of team "intro" (but need to break out "facts" and "plan"?!?):
            team_update_prompt = TemplateUtils.generate_team_update_prompt(
                prompt_template=self._prompt_templates["team_update"], **METADATA
            )
            # @@ self.send_intro(team_update_prompt)
            self._update_team_with_facts_and_plan(team_update_prompt=team_update_prompt)    # @@

            current_state= state_flow.initial_state
            while current_state not in state_flow.final_states:
                if verbose:
                    print(colored(f"********* Running state \"{current_state}\" (turn={total_turns}) *********", "blue"), flush=True)

                context["total_turns"]= total_turns

                previous_state= current_state
                current_state= state_flow.run_state(current_state, _messages, context, total_turns, self.orchestrated_messages)

                logging.info(f"Moved from {previous_state} to {current_state}")
                print(
                    f"%%% {datetime.now()} Orchestrator [state flow] from {previous_state} to {current_state}. Current turn: {total_turns}"
                )

                if current_state == "TERMINATE_TRUE":
                    return True, "TERMINATE"

                total_turns= context["total_turns"]
                if total_turns >= self.max_turns:
                    break

            # TODO: What to do with this?
            # @@ ?!? return state_flow.output_extraction(self.messages)
            # turn_final_result= state_flow.output_extraction(self.orchestrated_messages)

        return True, "TERMINATE"
