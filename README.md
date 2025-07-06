# Chatbot for Gramps

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

## Running the code

```bash
./chatbot.sh
```

The bash script will run the python code in a virtual environment, where it will download and install all necesary dependencies, like litellm and some Gramps libraries.
