# AutoGenChatView.py: Interactive chat view for AutoGen. Lightweight, pure Python (Panel), hackable, AutoGen
#       graphical user interface (GUI) view.
#   This class is strictly a view and has no direct knowledge of AutoGen.
#
# By: radman-x
# Github: https://github.com/radman-x/AutoGenLabs
#
# Adapted from: https://raw.githubusercontent.com/yeyu2/Youtube_demos/main/panel_autogen2.py
#
from dataclasses import dataclass

import panel as pn
import asyncio
import json
import logging

# >>>>>> Constants <<<<<<<
OPENING_PROMPT = "Send a message!"  # Set to your desired opening prompt.
LOGGING_LEVEL = logging.DEBUG  # options: logging.DEBUG, logging.INFO

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(LOGGING_LEVEL)

input_future = None
initiate_chat_task_created = False


@dataclass
class AutoGenChatView:
    """An interactive, multi-turn chat view for AutoGen: Lightweight, pure Python, hackable, AutoGen GUI view.
    Based on Panel. Contains following data fields/args:
    - initiate_chat_fn: callback function to start a chat.
    """

    initiate_chat_fn: callable = None

    def __post_init__(self):
        pn.extension(design="material")
        self.chat_interface = pn.chat.ChatInterface(callback=self.callback)
        self.chat_interface.send(OPENING_PROMPT, user="System", respond=False)
        self.chat_interface.servable()

    async def a_get_human_input(self, prompt: str) -> str:
        global input_future
        print("\n>>>>>>>> Awaiting human input <<<<<<<<")
        self.chat_interface.send(prompt, user="System", respond=False)
        # Create a new Future object for this input operation if none exists
        if input_future is None or input_future.done():
            input_future = asyncio.Future()

        # Wait for the callback to set a result on the future
        await input_future

        # Once the result is set, extract the value and reset the future for the next input operation
        input_value = input_future.result()
        input_future = None
        log.debug(f"MyConversableAgent.a_get_human_input returning: '{input_value}'")
        return input_value

    async def callback(self, contents: str, user: str, instance: pn.chat.ChatInterface):
        global initiate_chat_task_created
        global input_future

        if not initiate_chat_task_created:
            asyncio.create_task(self.initiate_chat_fn(contents))
            initiate_chat_task_created = True
        else:
            if input_future and not input_future.done():
                input_future.set_result(contents)
            else:
                print("There is currently no input being awaited.")

    def print_messages(self, recipient, messages, sender, avatar, total_usage:str=None):
        if LOGGING_LEVEL == logging.DEBUG:
            print(f"Messages from: {sender.name} sent to: {recipient.name} | num messages: {len(messages)} | message: {json.dumps(messages[-1], indent=4)}")
        else:
            print(f"Messages from: {sender.name} sent to: {recipient.name} | num messages: {len(messages)} | message: {messages[-1]}")

        if all(key in messages[-1] for key in ["name"]):
            _name = messages[-1]["name"]
            _avatar = avatar.get(_name)  # Needed esp. for function call replies
            if _avatar is not None:
                self.chat_interface.send(messages[-1]["content"], user=_name, avatar=_avatar, respond=False)
            else:
                print(f"Skipping message printing for {_name} (no avatar)")
        else:
            _avatar = "🥷"
            self.chat_interface.send(messages[-1]["content"], user="SecretGuy", avatar=_avatar, respond=False)

        if LOGGING_LEVEL == logging.DEBUG and total_usage is not None:
            print(f"Total usage stats: {json.dumps(total_usage, indent=4)}")

        return False, None  # required to ensure the agent communication flow continues
