# Chatbot for Gramps

First of all: this code is a fork from the following origin:

[GrampsChat](https://github.com/gramps-project/addons-source/blob/maintenance/gramps60/GrampsChat/chatbot.py)

The original was setup to interact with OpenAI and kept a history of the chat via OPIK, and ran on host.

The goal for this fork was to:

- Remove OPIK from the source
- Run Gemini by default instead of OpenAI
- Run the python code via a bash script to run it in a python virtual environment

Chatbot for Gramps interacts with a Gramps genealogy database and a set of tools to query this Gramps database. This way, the contents of the gramps database can be asked questions about the genealogy information that is in the database.

## setting up your config.env

To be able to interact with a remote AI tool you have to have an API key, either for Gemini or OpenAI, or else configure the litellm to chat with a local running AI that you might run using Ollama

You also have to specify the public name of the database you want to interact with - within Gramps there can be multiple database defined, and you have to configure one of these as the source for the genealogy information

An example contents of config.env:

```bash
export GEMINI_API_KEY="geminiapikey..."]
export OPENAI_API_KEY="sk-..."
export GRAMPS_DB_NAME=chatty
```

## Running the code on linux

Code is only tested on linux. The assumption is that it can also run on Mac and Windows by alternting the bash script slightly.

```bash
./chatbot.sh
```

The bash script will run the python code in a virtual environment, where it will download and install all necesary dependencies, like litellm and some Gramps libraries.
