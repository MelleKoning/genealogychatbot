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

It is also a good habit to copy a database, just as a separate entry point for safety.

An example contents of `config.env` is below where we have copied a gramps database to a `.grampsdb/chatty/` subfolder of where the `chatbot.sh` bash script is located:

```bash
export GEMINI_API_KEY="geminiapikey..."
export OPENAI_API_KEY="sk-..."
export GRAMPS_DB_NAME=chatty
# in case you have copied your gramps database
# including the name.txt then point to the
# right folder. The program will expect your database
# files to be -below- the path mentioned below.
# your folder structure will thus look like:
genealogychatbot/
├── chatbot.sh
├── .grampsdb/
│   └── chattydb/
│       ├── name.txt (contains "chatty")
│       └── <sqlite file(s)>
├── chatbot.py
├── config.env
└── README.md
# with the above GRAMPS_DB_NAME. The name in file name.txt
# should match the above GRAMPS_DB_NAME value
export GRAMPS_DB_LOCATION=".grampsdb"
# if you want you can copy multiple databases
# below the .grampsdb folder, and just use the names
# from "name.txt" to switch between talking to those genealogy
# databases
```

If you only use locally running LLMs via ollama, then only the GRAMPS_DB_NAME is needed.

## Running the code on linux

Code is only tested on linux. The assumption is that it can also run on Mac and Windows by altering the bash script slightly.

### prerequesites

A Gramps database is a prerequisite for the source of data. If you do not have a Gramps genealogy database, then this tool will not be very helpful. If you do have gramps, when opening the Gramps program, you will see several of your database names. This tool needs that database name to be able to read data from it, to feed the LLM AI Model with that based on the provided tools that query for that data in your genealogy database.

Also, your system must have certain dependencies already installed. These are a few commands that I personally needed to get python and gramps dependencies installed

```bash
# support for python3 virtual environments
sudo apt install python3-venv
# some hard Gramps dependencies
sudo apt install gir1.2-gexiv2-0.10
sudo apt install gir1.2-osmgpsmap-1.0
```

Then run the program with:

```bash
./chatbot.sh
```

The bash script will run the python code in a virtual environment, where it will download and install all necesary dependencies, like litellm and some Gramps libraries.

### Example chat

Note: all contents is totally made up, these persons did and do not exist. However, this is a chat that is possible with this tool with your database.

```bash
Enter your question: Who is the home person?

>>> The home person is Edward Baker

Enter your question: In what family is Edward Baker a child?

>>> Edward Baker is child in the family of Jim Baker and Maria Grant

Enter your question: Please name all members of this family.

>>> The members of this family are: Jim Baker, Maria Grant, Edward Baker, Georgina Baker and Elly Baker

Enter your question: Can you name all those members of that family and their "role" in that family, that is, if they are father, mother or brother sister etc

>>> Here are the members of the family and their roles:

*   **Jim Baker**: Father
*   **Maria Grant**: Mother
*   **Edward Baker**: Child
*   **Georgina Baker**: Child
*   **Elly Baker**: Child

Enter your question: For the children, can you specify if these are sons or daughters?

>>> Here are the children and their genders:

* **Edward Baker**: Son
* **Georgina Baker**: Daughter
* **Elly Baker**: Daughter

Enter your question: In what family is Edward Baker a parent?

>>> I am sorry, I cannot answer that question. The available tools do not allow me to determine in which family Edward Baker is a parent. I can only find the families where a person is a child.

Enter your question: Can you find the spouse of the home person?

>>> The spouse of the home person, Edward Baker, is Grace Lowbutt


Enter your question: Then given that answer, that is also the family the home person is in, correct? Did they marry?

>>> Yes, the family where Edward Baker is a parent, with Grace Lowbutt as the other parent, is indeed the family he is in as a spouse.

And yes, they did marry. There is a Marriage event recorded for this family.

Enter your quesiton: When did they marry?

>>> They married on 18 May 1887
```
