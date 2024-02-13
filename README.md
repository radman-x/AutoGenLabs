# AutoGen Labs

Useful components and experiments to help AutoGen devs.

## TL;DR
To run the sample app AutoGenGuiChat, do the following (ideally, in your Python virtual environment):
1. Install requirements:
    ```
    pip install -r requirements.txt
    git clone https://github.com/radman-x/AutoGenLabs
    ```
2. Copy OAI_CONFIG_LIST_sample to OAI_CONFIG_LIST and add your OpenAI/Azure key(s). Read, then remove comments in that file.
3. Run:
    ```
    panel server AutoGenGuiChat
    ```
4. Point browser at http://localhost:5006/AutoGenGuiChat
5. Enjoy chatting with AutoGen!

## Components
* AutoGenGuiChat -- sample application for using AutoGenChatView as graphical user interface for AutoGen
* AutoGenChatView -- re-usable chat view component

## Features
* "ChatGPT-like" user experience
* Multi-turn, interactive AutoGen graphical user interface (GUI) via AutoGen async.
* Pure Python -- no HTML/Javascript/React/backend-frontend, etc.
* Based on Panel
* Lightweight, easily customizable and hackable for embedding in your own applications
* Displays usage stats with total cost and tokens in console (in DEBUG mode)

## Test Prompts
These prompts are know to work and can be run in the same session:
* "tell a joke"
* "write a very short poem"
* "write a python function to list current directory"
* "tell another joke"
* "write a very short story"
* "summarize conversation so far"

## Customizing
There are various methods to customizing these components including:
* Override AutoGenGuiChat app class and write your own build_autogen_flow() method. This lets you create more advanced AutoGen flow e.g., like adding an engineer, critic, etc..
* Hacking the AutoGenGuiChat app class directly, e.g., to customized the build_autogen_flow() method without overriding the class
* Hacking the AutoGenChatView component class directly
* In the build_autogen_flow() method, you can modify agent system messages, descriptions (ie, used for GroupChat next speaker selection) and avatars. Avatars can use any emoji unicode character such as:
    - Smileys & People : https://emojipedia.org/people/
    - Animals & Nature : https://emojipedia.org/nature/
    - Foor & Drink : https://emojipedia.org/food-drink/
    - Activity : https://emojipedia.org/activity/
    - Travel & Places : https://emojipedia.org/travel-places/
    - Objects : https://emojipedia.org/objects/
    - Symbols : https://emojipedia.org/symbols/
    - Flags : https://emojipedia.org/flags/
* To run/debug in VSCode, create a panel launcher configuration in VSCode's launch.json, eg:
    ```
        {
            "name": "panel serve",
            "type": "python",
            "request": "launch",
            "program": "-m",
            "args": [
                "panel",
                "serve",
                "${relativeFile}",
                // "--show" // This will open in Edge (ie, default OS browser)
            ],
            "console": "integratedTerminal",
            "justMyCode": false
        },
    ```
The, open and select AutoGenGuiChat.py tab and hit F5.

## Know issues
* Bug: function calls not displayed in view
* Numerous standard icons in Panel ChatInterface are not yet implemented: "liking" messages, clear history, etc.
* Add better documentation
