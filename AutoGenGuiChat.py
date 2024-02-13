# AutoGenGuiChat.py: Simple Pythonic AutoGen Chat with Graphical User Interface.
#   This is a sample app to show how to use AutoGenChatView.
#
import autogen

from autogen import (
    GroupChat,
    GroupChatManager,
)
from AutoGenChatView import AutoGenChatView

from typing import Tuple, Dict

import asyncio
import logging

logging.basicConfig()
LOGGING_LEVEL = logging.DEBUG  # options: logging.INFO, logging.DEBUG
log = logging.getLogger(__name__)
log.setLevel(LOGGING_LEVEL)

config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={
        "model": ["gpt-4-turbo-preview"],   # Change to your desired model.
    },
)

gpt4_config = {"config_list": config_list, "temperature": 0, "cache_seed": None}

user_proxy = None
manager = None
avatar = None

class MyConversableAgent(autogen.ConversableAgent):
    async def a_get_human_input(self, prompt: str) -> str:
        return await autogen_chat_view.a_get_human_input(prompt)

def print_messages(recipient, messages, sender, config):
    return autogen_chat_view.print_messages(recipient, messages, sender,
        avatar, total_usage=manager.get_total_usage())


async def delayed_initiate_chat(message):
    global user_proxy, manager
    await asyncio.sleep(2)  # Wait for 2 seconds
    await user_proxy.a_initiate_chat(manager, message=message)  # Now initiate the chat

autogen_chat_view = AutoGenChatView(initiate_chat_fn=delayed_initiate_chat)


def build_autogen_flow() -> (Tuple[autogen.ConversableAgent, autogen.ConversableAgent, Dict]):
    agents = []
    av = {}

    # Admin (human):
    user_proxy = MyConversableAgent(
        name="Admin",
        # is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
        is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("exit"),
        system_message="""A human admin. Collaborate with others. Provide approvals, when needed.""",
        code_execution_config=False,
        human_input_mode="ALWAYS",
        llm_config=gpt4_config,
    )
    agents.append(user_proxy)
    av.update({user_proxy.name: "👨‍💼"})

    # AI Assistant:
    assistant = autogen.AssistantAgent(
        name="Assistant",
        human_input_mode="NEVER",
        description="""A helpful AI assistant.""",
        llm_config=gpt4_config,
    )
    agents.append(assistant)
    av.update({assistant.name: "💁"})

    avatar = av

    groupchat = GroupChat(
        agents=agents,
        messages=[],
        max_round=20,
    )
    manager = GroupChatManager(
        groupchat=groupchat,
        llm_config=gpt4_config,
        code_execution_config=False,
    )

    # register replies callback:
    for agent in agents:
        agent.register_reply(
            [autogen.Agent, None],
            reply_func=print_messages,
            config={"callback": None},
        )

    return user_proxy, manager, avatar


user_proxy, manager, avatar = build_autogen_flow()
