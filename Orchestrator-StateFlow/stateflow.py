# !!rm -- taken from: https://github.com/microsoft/autogen/blob/289cb60db07106a0ba0f78c6bb5d77e5eb027c0a/autogen/agentchat/contrib/stateflow.py
#   This was also radman modified (see "!!rm" tags, mostly) to improve it and use it with Orchestrator.

import logging
import sys
import types
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any
import re
from autogen import ConversableAgent
from abc import abstractmethod
logger = logging.getLogger(__name__)

try:
    from termcolor import colored
except ImportError:
    def colored(x, *args, **kwargs):
        return x


from autogen.code_utils import (
    UNKNOWN,
    content_str,
)
from autogen.oai.client import OpenAIWrapper


# !!rm def in_n_th_msg(messages: List[Dict[str, str]], pattern: str, n: int = -1) -> bool:
#     """Check if the pattern is in the n-th messages.
#     Args:
#         messages (list[dict]): a list of messages received from other agents.
#             The messages are dictionaries that are JSON-serializable and
#             follows the OpenAI's ChatCompletion schema.
#         pattern (str): the pattern to search for
#         n (int): the n-th message to search for. Default is the last message.
#     """
#     return pattern in messages[n]["content"]


# !!rm def in_last_msg(messages: List[Dict[str, str]], pattern: str) -> bool:
#     """Check if the pattern is in the last message.
#     Args:
#         messages (list[dict]): a list of messages received from other agents.
#             The messages are dictionaries that are JSON-serializable and
#             follows the OpenAI's ChatCompletion schema.
#         pattern (str): the pattern to search for
#     """
#     return in_n_th_msg(messages, pattern, -1)


class StateFlow:
    """Controlled, deterministic chat flow via finite state machine. Args:
    - states: A Dict of state name and a List sequence of actions to be executed in that state.
        An action can be:
            - An function that takes in a list of messages and returns a string or Dict.
            - A ConversableAgent object that has generate_reply and reset method.
                reset will be called in StateFlow.run().
            - A string that will be converted to a dict {'content': str, 'role': 'user'} to be
                appended to context history.
            - A Dict in the form of message with key "content" and "role" (ie, in OpenAI message
                format) that will be appended to context history.
    - transitions: A Dict of a state name and a transition function to determine the next state.
        There are several types of transitions:
            - A static string of the next state
            - A function that takes in a list of messages and returns the next state
            - (Future TODO) Use an LLM to determine the next state: Instruct an LLM to determine
                the current state. For example, whether the problem is solved based on the history
                (or last message). You still need to instruct the LM to generate responses like "Yes"
                or "No" and match the response.
    - initial_state: initial state name (str)
    - final_states: list of final state names (str)
    - max_transitions: the maximum number of transitions allowed (int)
    """
    states: Dict[str, List]
    transitions: Dict[str, Union[str, callable]] = {}
    initial_state: str = None
    final_states: List[str] = []
    max_transitions: int = 10

    # messages: List[Dict[str, str]]
    # current_state: str
    state_history: List[str] = []
    # turn_count: int = 0
    verbose: bool = True
    use_name: bool = False # append name to a message if True

    def __init__(self, states, transitions, initial_state=None, final_states=[], max_transitions=10):
        self.states= states
        self.initial_state= initial_state if initial_state else list(states)[0]
        self.final_states= final_states if final_states else [list(states)[-1]]
        self.transitions= transitions
        self.max_transitions= max_transitions

        # self.current_state = self.initial_state

    # @abstractmethod
    def output_extraction(self, messages: List[Dict[str, str]]) -> str:
        """Extract the output from the messages."""
        # Post processing method: called after the state machine finishes to generate the final output
        # Future TODO: add self.extraction_method= "last_message"|"all_messages"|"llm_summary".
        #   Similar to nested_chats summary method.
        final_output= messages[-1]["content"]
        # if self.verbose:
        #     print(colored(f"********* StateFlow output= = \"{final_output}\" *********", "blue"), flush=True)
        return final_output
        # return messages

    def check_states(self):
        """Check that the states are well defined."""
        assert self.initial_state is not None, "Initial state not defined"
        assert len(self.final_states) > 0, "No final states defined"
        assert self.initial_state in self.states, f"Initial state {self.initial_state} not defined in states"
        for state in self.final_states:
            assert state in self.states, f"Final state {state} not defined in states"

        for state in self.states:
            assert state in self.transitions, f"Transition for state {state} not defined"

    def reset(self):
        """Reset the state machine.
        Set state to initial state and clear the messages.
        Reset all agents or other stateful actions.
        """
        # self.turn_count = 0
        # self.current_state = self.initial_state
        # self.messages = []
        self.state_history = []
        for s in self.states:
            for output_func in self.states[s]:
                if isinstance(output_func, ConversableAgent):
                    output_func.reset()

    # !!rm def run(self, task: str, verbose: bool = True):
    #     self.reset()
    #     self.check_states()
    #     self.verbose = verbose

    #     self.messages.append({"content": task, "role": "user"})
    #     while self.current_state not in self.final_states:
    #         if self.verbose:
    #             print(colored(f"********* Running state, current = \"{self.current_state}\" (turn={self.turn_count}) *********", "blue"), flush=True)
    #         # if self.verbose:
    #         #     print(colored(f"*********State {self.current_state}*********", "blue"), flush=True)

    #         # Run the output functions for the current state
    #         for output_func in self.states[self.current_state]:
    #             self.enter(output_func)

    #         # Transition to the next state
    #         transition= self.transitions[self.current_state]
    #         if type(transition) is str:
    #             self.current_state = transition
    #         else:
    #             assert type(transition) is types.FunctionType or type(transition) is types.MethodType
    #             self.current_state = transition(self.messages)
    #         # if type(self.transitions[self.current_state]) is str:
    #         #     self.current_state = self.transitions[self.current_state]
    #         # else:
    #         #     self.current_state = self.transitions[self.current_state](self.messages)

    #         self.state_history.append(self.current_state)
    #         self.turn_count += 1
    #         if self.turn_count >= self.max_transitions:
    #             break
    #     return self.output_extraction(self.messages)

    # !!rm -- added fn:
    def run_state(self, state:str, _messages: List[Dict[str, str]], context: Dict, turn_count: int, orchestrated_messages:List,
                verbose: bool = True) -> str:
        """Runs the given state. Returns next state."""
        # Returns True if continuing.
        if verbose:
            print(colored(f"********* Running state \"{state}\" (turn={turn_count}) *********", "blue"), flush=True)

        # Run the output functions for the current state
        for output_func in self.states[state]:
            self.enter(output_func, _messages, context, orchestrated_messages)

        # Transition to the next state
        transition= self.transitions[state]
        next_state= ''
        if type(transition) is str:
            next_state = transition
        else:
            assert type(transition) is types.FunctionType or type(transition) is types.MethodType
            next_state = transition(_messages, context)

        self.state_history.append(state)
        return next_state

    # @@ !!rm s/b _process_output_func()
    def enter(self, output_func: Union[str, callable, dict], _messages: List[Dict[str, str]], context:Any, orchestrated_messages:List):
        output_name = ""
        output_role = "user"  # TODO: s/b "assistant"?!?
        result= None
        if type(output_func) is types.FunctionType or type(output_func) is types.MethodType:
            result = output_func(_messages, context)
            #result = output_func(self.messages)
        elif isinstance(output_func, ConversableAgent):
            result = output_func.generate_reply(_messages)
            # result = output_func.generate_reply(self.messages)
            # output_role = output_func._role # Agents no longer have _role.
            output_name = output_func.name
        elif type(output_func) is dict:
            result = output_func
        elif type(output_func) is str:
            pass
        else: 
            raise ValueError(f"Invalid output function type: {type(output_func)}")

        if result and isinstance(result, str):
            result = {"content": result, "role": output_role}
        if self.use_name and output_name != "":
            result['name'] = output_name

        if isinstance(result, types.GeneratorType):
            # TODO: stream function_call / function_calls: update result
            pass
        else: 
            if self.verbose and result:
                self._print_received_message(result, len(_messages), name=output_name)
        if result:
            self.messages.append(result)
            if orchestrated_messages:
                orchestrated_messages.append(result)
        
        return result

    def _print_received_message(
        self, message: Union[Dict, str], message_num: int, name: str = "", inloop: bool = False
    ):
        """Adapted from [`_print_received_message`](ConversableAgent#_print_received_message)"""
        if not inloop:
            if name == "":
                print(colored(f"Output {message_num}:", "yellow"), flush=True)
                # print(colored(f"Output {len(self.messages)}:", "yellow"), flush=True)
            else:
                print(colored(f"Output {message_num} ({name}):", "yellow"), flush=True) 
                # print(colored(f"Output {len(self.messages)} ({name}):", "yellow"), flush=True)

        if message.get("tool_responses"):  # Handle tool multi-call responses
            for tool_response in message["tool_responses"]:
                self._print_received_message(tool_response, inloop=True)
            if message.get("role") == "tool":
                return  # If role is tool, then content is just a concatenation of all tool_responses

        if message.get("role") in ["function", "tool"]:
            if message["role"] == "function":
                id_key = "name"
            else:
                id_key = "tool_call_id"

            func_print = f"***** Response from calling {message['role']} \"{message[id_key]}\" *****"
            print(colored(func_print, "green"), flush=True)
            print(message["content"], flush=True)
            print(colored("*" * len(func_print), "green"), flush=True)
        else:
            content = message.get("content")
            if content is not None:
                if "context" in message:
                    content = OpenAIWrapper.instantiate(
                        content,
                        message["context"],
                        self.llm_config and self.llm_config.get("allow_format_str_template", False),
                    )
                print(content_str(content), flush=True)
            if "function_call" in message and message["function_call"]:
                function_call = dict(message["function_call"])
                func_print = (
                    f"***** Suggested function Call: {function_call.get('name', '(No function name found)')} *****"
                )
                print(colored(func_print, "green"), flush=True)
                print(
                    "Arguments: \n",
                    function_call.get("arguments", "(No arguments found)"),
                    flush=True,
                    sep="",
                )
                print(colored("*" * len(func_print), "green"), flush=True)
            if "tool_calls" in message and message["tool_calls"]:
                for tool_call in message["tool_calls"]:
                    id = tool_call.get("id", "(No id found)")
                    function_call = dict(tool_call.get("function", {}))
                    func_print = f"***** Suggested tool Call ({id}): {function_call.get('name', '(No function name found)')} *****"
                    print(colored(func_print, "green"), flush=True)
                    print(
                        "Arguments: \n",
                        function_call.get("arguments", "(No arguments found)"),
                        flush=True,
                        sep="",
                    )
                    print(colored("*" * len(func_print), "green"), flush=True)

        print("\n", "-" * 80, flush=True, sep="")
