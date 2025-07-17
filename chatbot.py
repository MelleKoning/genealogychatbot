from typing import Dict, Any, List, Optional

import os
import json
import sys
import time
import re
import inspect

try:
    import litellm
except ImportError:
    raise Exception("GrampsChat requires litellm")
# import markdown

litellm.drop_params = True

from gramps.gen.plug import Gramplet
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.simple import SimpleAccess
from gramps.gen.db.utils import open_database
from gramps.gen.display.place import displayer as place_displayer
from gramps.gen.config import CONFIGMAN
_ = glocale.translation.gettext

HELP_TEXT = """
GrampsChat uses the following OS environment variables:

```
export GRAMPS_AI_MODEL_NAME="<ENTER MODEL NAME HERE>"
```

This is always needed. Examples: "ollama/deepseek-r1:1.5b", "openai/gpt-4o-mini", "gemini/gemini-2.5-flash"

```
export GRAMPS_AI_MODEL_URL="<ENTER URL HERE>"
```

This is needed if running your own LLM server. Example: "http://127.0.0.1:8000"

You can find a list of litellm providers here:
https://docs.litellm.ai/docs/providers

You can find a list of ollama models here:
https://ollama.com/library/deepseek-r1:1.5b

### Optional

If you are running a commercial AI model provider, you will need their API key.

#### Example

For OpenAI:

```
export OPENAI_API_KEY="sk-..."
```

For Gemini:

```
export GEMINI_API_KEY="gemini-key..."
```

"""

SYSTEM_PROMPT = """
You are a helpful and highly analytical genealogist, an expert in the Gramps open source genealogy program.
Your primary goal is to assist the user by providing accurate and relevant genealogical information.

**Crucial Guidelines for Tool Usage and Output:**

1.  **Prioritize User Response:** Always aim to provide a direct answer to the user's query as soon as you have sufficient information. Do not over-rely on tools if the answer can be reasonably inferred or constructed from existing knowledge or prior tool outputs.
2.  **Tool Purpose:** Use tools ONLY when necessary to gather specific information that directly helps answer the user's request.
3.  **About data details from tools:** 
    * Never mention database keys, grampsID keys, or a person's 'handle' directly to the user.
    * Do present names of people to communicate human readable data received from tools 
4.  **Progress Monitoring & Self-Correction:**
    * **Assess Tool Results:** After each tool call, carefully evaluate its output. Did it provide the expected information? Is it sufficient to progress towards the user's goal?
    * **Avoid Redundancy:** Do not call the same tool twice in a row.
    * **Avoid looping:** If you have made 2-3 consecutive tool calls that do not significantly advance towards the user's question, or if you encounter persistent errors, assume you are stuck or lacking the necessary data.
5.  **Graceful Exit & Partial Results:**
    * **If Stuck or Unable to Progress:** If you can not make progress, or have made several unproductive tool calls, **stop attempting further tool calls immediately.**
    * **Summarize Findings:** Instead, synthesize all the information you *have* gathered so far, even if it's incomplete or not directly leading to a full answer. Clearly state what you found and what information you were unable to obtain.
    * **Suggest Next Steps/Ask for Clarification:** If you cannot fully answer the question, clearly state what additional information you would need from the user to proceed, or suggest a different line of inquiry.

You can get the start point of the genealogy tree using the `start_point` tool.
"""

GRAMPS_AI_MODEL_NAME = os.environ.get("GRAMPS_AI_MODEL_NAME")
GRAMPS_AI_MODEL_URL = os.environ.get("GRAMPS_AI_MODEL_URL")
# overwrite the default database path in case the env variable is set
GRAMPS_DB_LOCATION = os.environ.get("GRAMPS_DB_LOCATION")

from litellm_utils import function_to_litellm_definition


class Chatbot:
    def __init__(self, database_name):
        self.debug_mode = self.ask_debug_mode()
        self.db = open_database(database_name, force_unlock=True)
        if self.db is None:
            raise Exception(f"Unable to open database {database_name}")
        self.messages = []
        self.sa = SimpleAccess(self.db)
        self.tool_map = {
            "start_point": self.start_point,
            "get_mother_of_person": self.get_mother_of_person,
            "get_family": self.get_family,
            "get_person": self.get_person,
            "get_children_of_person": self.get_children_of_person,
            "get_father_of_person": self.get_father_of_person,
            "get_person_birth_date": self.get_person_birth_date,
            "get_person_death_date": self.get_person_death_date,
            "get_person_birth_place": self.get_person_birth_place,
            "get_person_death_place": self.get_person_death_place,
            "get_person_event_list": self.get_person_event_list,
            "get_event": self.get_event,
            "get_event_place": self.get_event_place,
            "get_child_in_families": self.get_child_in_families,
            "find_people_by_name": self.find_people_by_name,
        }
        self.tool_definitions = [
            function_to_litellm_definition(self.start_point),
            function_to_litellm_definition(self.get_mother_of_person),
            function_to_litellm_definition(self.get_family),
            function_to_litellm_definition(self.get_person),
            function_to_litellm_definition(self.get_children_of_person),
            function_to_litellm_definition(self.get_father_of_person),
            function_to_litellm_definition(self.get_person_birth_date),
            function_to_litellm_definition(self.get_person_death_date),
            function_to_litellm_definition(self.get_person_birth_place),
            function_to_litellm_definition(self.get_person_death_place),
            function_to_litellm_definition(self.get_person_event_list),
            function_to_litellm_definition(self.get_event),
            function_to_litellm_definition(self.get_event_place),
            function_to_litellm_definition(self.get_child_in_families),
            function_to_litellm_definition(self.find_people_by_name),
        ]

    def chat(self):
        self.messages.append({"role": "system", "content": SYSTEM_PROMPT})
        query = input("\n\nEnter your question: ")
        while query:
            self.get_chatbot_response(query)
            query = input("\n\nEnter your question: ")

    def ask_debug_mode(self) -> bool:
        response = input("Do you want to enable debug mode? (y/n): ").strip().lower()
        return response == 'y'

    # @_throttle.rate_limited(_limiter)
    def _llm_complete(
        self,
        all_messages: List[Dict[str, str]],
        tool_definitions: Optional[List[Dict[str, str]]],
        seed: int,
    ) -> Any:
        # disabled debug_mode for requests
        # as the tools in the requests is too lengthy for logging
        #if self.debug_mode:
            # Log the request
         #   print("\033[94mRequest to AI Model:\033[0m")
          #  print(json.dumps({
           #     "model": GRAMPS_AI_MODEL_NAME,
            #    "messages": all_messages,
             #   "seed": seed,
              #  "tools": tool_definitions
            #}, indent=2))
        response = litellm.completion(
            model=GRAMPS_AI_MODEL_NAME,  # self.model,
            messages=all_messages,
            seed=seed,
            tools=tool_definitions,
            tool_choice="auto" if tool_definitions is not None else None,
        )
        if self.debug_mode:
            # Log the response
            print("\033[92mResponse from AI Model:\033[0m")
            # Convert response to a dictionary if possible
            response_dict = response.to_dict() if hasattr(response, 'to_dict') else str(response)
            print(json.dumps(response_dict, indent=2))
        return response

    def get_chatbot_response(
        self,
        user_input: str,
        seed: int = 42,
    ) -> Any:
        self.messages.append({"role": "user", "content": user_input})
        retval = self._llm_loop(seed)
        print("\n\n>>>", retval),  # is_user=False)
        self.messages.append(
            {
                "role": "assistant",
                "content": retval,
            }
        )

    def _llm_loop(self, seed):
        # Tool-calling loop
        final_response = "I was unable to find the desired information."
        count = 0
        print("   Thinking...", end="")
        sys.stdout.flush()

        limit_loop = 6
        while count < limit_loop:
            time.sleep(1)  # Add a one-second delay to prevent overwhelming the AI remote
            count += 1

            # Determine if this is the final attempt
            is_final_attempt = (count == limit_loop)

            # If it's the final attempt, we do not send tools to the LLM.
            # This ensures that the LLM is forced to provide a final response
            # without attempting to call any more tools.
            tools_to_send = self.tool_definitions if not is_final_attempt else None

            # For the final attempt, we might also want to add a reinforcing system message
            # to ensure it knows to summarize.
            messages_for_llm = list(self.messages)

            if is_final_attempt:
                # Append a temporary system message to guide the final response
                messages_for_llm.append(
                    {
                        "role": "system",
                        "content": "You have reached the maximum number of "
                        "tool-calling attempts. Based on the information gathered "
                        "so far, provide the most complete answer you can, or "
                        "clearly state what information you could not obtain. Do "
                        "not attempt to call any more tools."
                    }
                )

            response = self._llm_complete(messages_for_llm, tools_to_send, seed) # Pass the conditional tools

            if not response.choices:
                print("No response choices available from the AI model.")
                break

            msg = response.choices[0].message
            self.messages.append(msg.to_dict()) # Add the actual message to the persistent history

            # Check for tool calls OR if it's the final attempt
            if msg.tool_calls and not is_final_attempt: # Only execute tools if not the final attempt
                for tool_call in msg["tool_calls"]:
                    print(f"Executing tool call: {tool_call['function']['name']}")
                    print("This is a local tool call.")
                    tool_name = tool_call["function"]["name"]
                    arguments = json.loads(tool_call["function"]["arguments"])
                    print(".", end="")
                    sys.stdout.flush()
                    tool_func = self.tool_map.get(tool_name)
                    try:
                        if tool_func is not None:
                            sig = inspect.signature(tool_func)
                            if len(sig.parameters) == 0:
                                # Ignore any arguments, call with none
                                tool_result = tool_func()
                            else:
                                tool_result = tool_func(**arguments)

                        else : tool_result = "Unknown tool: {tool_name}"

                        content_for_llm = ""
                        if isinstance(tool_result, (dict, list)):
                            content_for_llm = json.dumps(tool_result)
                        else:
                            content_for_llm = str(tool_result)
                        if self.debug_mode:
                            print("\033[93mTool call result:\033[0m")
                            print(content_for_llm)

                    except Exception as exc:
                        print(exc)
                        content_for_llm = f"Error in calling tool `{tool_name}`: {exc}" # Include exception for LLM clarity

                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": content_for_llm,
                        }
                    )
            else:
                # This 'else' block is now entered if:
                # 1. The LLM provided a final generative response (no tool_calls)
                # 2. It's the final attempt (count == 6) and it might *still* try to call a tool,
                #    but we've removed the tools, so it's forced to respond.
                final_response = response.choices[0].message.content
                break # Exit the loop as we have a final response or hit max attempts

        # If the loop finishes without a 'break' (e.g., if the last message was a tool call,
        # but it was the 6th iteration and we forced it to output text), ensure final_response
        # is set. This might be redundant if the new logic above ensures it, but good for safety.
        if final_response == "I was unable to find the desired information." and self.messages and self.messages[-1].get("content"):
            final_response = self.messages[-1]["content"]

        return final_response

    # Tools:

    def get_person(self, person_handle: str) -> Dict[str, Any]:
        """
        Given a person's handle, get the data dictionary of that person.
        """
        data = dict(self.db.get_raw_person_data(person_handle))
        return data

    def get_mother_of_person(self, person_handle: str) -> Dict[str, Any]:
        """
        Given a person's handle, return their mother's data dictionary.
        The person_handle to pass to this func is the "person_handle" (a string) for the person
        whose mother you want to find.
        """
        person_obj = self.db.get_person_from_handle(person_handle)
        obj = self.sa.mother(person_obj)
        data = dict(self.db.get_raw_person_data(obj.handle))
        return data

    def get_family(self, family_handle: str) -> Dict[str, Any]:
        """
        Get the data of a family given the family handle in the argument. 
        * family handles are different from a person handle. 
        * a person has family handles in two different fields:
        - "parent_family_list" has the list of family handles the person is a child in
        - "family_list" has the list of family handles the person is a parent in
        The result of "get_family" tool contains several handles as follows:
        "father_handle": person_handle of the father in the family
        "mother_handle": person_handle of the mother in the family
        "child_ref_list": list of person_handles of children in the family,
        each item in the "child_ref_list" has a "ref" which is the person_handle of children of the family.
        Details of the persons can be retrieved using the "get_person" tool
        """
        data = dict(self.db.get_raw_family_data(family_handle))
        return data

    def start_point(self) -> Dict[str, Any]:
        """
        Get the start point of the genealogy tree, i.e., the default person.
        This tool does not take any "arguments". 
        * Call this tool without arguments
        * When no "person_handle" value is in the session context yet
        then use this tool to get the first person in the genealogy tree.
        
        The result of start_point contains values for:
        * The "first_name" contains the first name of the person.
        * The "surname_list" and then "surname" contains the last name(s) of the person.
        * The "handle" is the key that looks like a hash string for the person to use for other tool calls.
        * "family_list" is a list of handles where the person is a parent.
        * "parent_family_list" is a list of handles for the families where the person is listed as a child.
        """
        obj = self.db.get_default_person()
        if obj:
            data = dict(self.db.get_raw_person_data(obj.handle))
            return data
        return None

    def get_children_of_person(self, person_handle: str) -> List[str]:
        """
        Get a list of children handles of a person's main family,
        given a person's handle.
        Result:
        * provides "handle" values of children, to be used as arguments for get_person tool.
        """
        obj = self.db.get_person_from_handle(person_handle)
        family_handle_list = obj.get_family_handle_list()
        if family_handle_list:
            family_id = family_handle_list[0]
            family = self.db.get_family_from_handle(family_id)
            return [handle.ref for handle in family.get_child_ref_list()]
        else:
            return []

    def get_father_of_person(self, person_handle: str) -> Dict[str, Any]:
        """
        Given a person's handle, return their father's data dictionary.
        The "person_handle" to pass to this func is the "person_handle" (a string)
        for the person whose father you want to find.
        """
        person_obj = self.db.get_person_from_handle(person_handle)
        obj = self.sa.father(person_obj)
        data = dict(self.db.get_raw_person_data(obj.handle))
        return data

    def get_person_birth_date(self, person_handle: str) -> str:
        """
        Given a person's handle, return the birth date as a string.
        """
        person = self.db.get_person_from_handle(person_handle)
        return self.sa.birth_date(person)

    def get_person_death_date(self, person_handle: str) -> str:
        """
        Given a person's handle, return the death date as a string.
        """
        person = self.db.get_person_from_handle(person_handle)
        return self.sa.death_date(person)

    def get_person_birth_place(self, person_handle: str) -> str:
        """
        Given a person's handle, return the birth date as a string.
        """
        person = self.db.get_person_from_handle(person_handle)
        return self.sa.birth_place(person)

    def get_person_death_place(self, person_handle: str) -> str:
        """
        Given a person's handle, return the death place as a string.
        """
        person = self.db.get_person_from_handle(person_handle)
        return self.sa.death_place(person)

    def get_person_event_list(self, person_handle: str) -> List[str]:
        """
        Get a list of event handles associated with a person,
        given the person handle. Use `get_event(event_handle)`
        to look up details about an event.
        """
        obj = self.db.get_person_from_handle(person_handle)
        if obj:
            return [ref.ref for ref in obj.get_event_ref_list()]

    def get_event(self, event_handle: str) -> Dict[str, Any]:
        """
        Given an event_handle, get the associated data dictionary.
        """
        data = dict(self.db.get_raw_event_data(event_handle))
        return data

    def get_event_place(self, event_handle: str) -> str:
        """
        Given an event_handle, return the associated place string.
        """
        event = self.db.get_event_from_handle(event_handle)
        return place_displayer.display_event(self.db, event)

    def get_child_in_families(self, person_handle: str) -> List[Dict[str, Any]]:
        """
        Retrieve detailed information about all families where the given person is listed as a child.
        This tool is essential for genealogical research, allowing users to identify the person's siblings
        and parents by examining the family structures they belong to. It returns a list of dictionaries,
        each containing comprehensive data about a family, facilitating in-depth family tree analysis.
        """
        person_obj = self.db.get_person_from_handle(person_handle)
        families = self.sa.child_in(person_obj)
        family_data_list = []

        for family in families:
            family_data = self.get_family(family.handle)
            family_data_list.append(family_data)

        return family_data_list

    def find_people_by_name(self, search_string: str) -> List[Dict[str, Any]]:
        """
        Searches the Gramps database for people whose primary or alternate names
        contain the given search string (case-insensitive), using the all_people iterator.

        Args:
            search_string: The string to match in person names.

        Returns:
            A list of dictionaries, where each dictionary contains the raw data
            of a matching person.
        """
        matching_people_raw_data = []
        search_pattern = re.compile(re.escape(search_string), re.IGNORECASE)

        for person_obj in self.sa.all_people():
            matched = False

            # Helper function to check fields within a Name or Surname object
            def check_name_fields(name_or_surname_obj: Any) -> bool:
                """Checks relevant string fields of a Name or Surname object for a match."""
                fields_to_check = []

                # Fields common to Name object (primary_name or alternate_name elements)
                if hasattr(name_or_surname_obj, 'first_name'):
                    fields_to_check.append(name_or_surname_obj.first_name)
                # Corrected: 'prefix' and 'suffix' are properties of the Name object itself, not the Surname object.
                if hasattr(name_or_surname_obj, 'prefix'):
                    fields_to_check.append(name_or_surname_obj.prefix)
                if hasattr(name_or_surname_obj, 'suffix'):
                    fields_to_check.append(name_or_surname_obj.suffix)
                if hasattr(name_or_surname_obj, 'title'):
                    fields_to_check.append(name_or_surname_obj.title)
                if hasattr(name_or_surname_obj, 'call'):
                    fields_to_check.append(name_or_surname_obj.call)
                if hasattr(name_or_surname_obj, 'nick'):
                    fields_to_check.append(name_or_surname_obj.nick)
                if hasattr(name_or_surname_obj, 'famnick'):
                    fields_to_check.append(name_or_surname_obj.famnick)
                if hasattr(name_or_surname_obj, 'patronymic'):
                    fields_to_check.append(name_or_surname_obj.patronymic)

                # Fields specific to Surname object (within surname_list)
                if hasattr(name_or_surname_obj, 'surname'): # This means it's a Surname object
                    fields_to_check.append(name_or_surname_obj.surname)
                    # Note: Surname objects can also have their own 'prefix' and 'connector'
                    # which are separate from the 'prefix' of the main Name object.
                    if hasattr(name_or_surname_obj, 'connector'):
                        fields_to_check.append(name_or_surname_obj.connector)

                for field_value in fields_to_check:
                    # Ensure field_value is a non-empty string before attempting search
                    if isinstance(field_value, str) and field_value and search_pattern.search(field_value):
                        return True
                return False

            # Check primary name fields
            if person_obj.primary_name:
                if check_name_fields(person_obj.primary_name):
                    matched = True

                # Surnames are in a list, iterate through each Surname object
                if not matched and hasattr(person_obj.primary_name, 'surname_list'):
                    for surname_obj in person_obj.primary_name.surname_list:
                        if check_name_fields(surname_obj): # Check the Surname object
                            matched = True
                            break

            # Check alternate name fields if not already matched
            if not matched and hasattr(person_obj, 'alternate_names') and person_obj.alternate_names:
                for alt_name in person_obj.alternate_names:
                    if check_name_fields(alt_name):
                        matched = True
                        break

                    # Check surnames within alternate name
                    if not matched and hasattr(alt_name, 'surname_list'):
                        for alt_surname_obj in alt_name.surname_list:
                            if check_name_fields(alt_surname_obj):
                                matched = True
                                break
                        if matched: # Break from outer alt_names loop if matched
                            break

            if matched:
                # Use the existing _get_raw_person_from_id_data to get raw data
                # self.db is assumed to be the database access object within the tool's class.
                raw_data = dict(self.db._get_raw_person_from_id_data(person_obj.gramps_id))
                desired_fields = {
                    "handle": raw_data.get("handle"),
                    "first_name": raw_data.get("primary_name", {}).get("first_name"),
                    "surname": raw_data.get("primary_name", {}).get("surname_list", [{}])[0].get("surname"),
                    "prefix": raw_data.get("primary_name", {}).get("surname_list", [{}])[0].get("prefix")
                }
                matching_people_raw_data.append(desired_fields)

        return matching_people_raw_data


if __name__ == "__main__":
    # Get the database name from the environment variable
    database_name = os.getenv("GRAMPS_DB_NAME")
    print(f"Attempting to initialize Chatbot with database: {database_name}")
    # Use env variable if set, otherwise default to ./grampsdb below script
    if GRAMPS_DB_LOCATION:
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        # If the env var is a relative path, resolve it relative to script
        if not os.path.isabs(GRAMPS_DB_LOCATION):
            GRAMPS_DB_FOLDER = os.path.join(SCRIPT_DIR, GRAMPS_DB_LOCATION)
        else:
            GRAMPS_DB_FOLDER = GRAMPS_DB_LOCATION
        print(f"Using database folder: {GRAMPS_DB_FOLDER}")
        if not os.path.isdir(GRAMPS_DB_FOLDER):
            raise Exception(
                f"GRAMPS_DB_FOLDER path does not exist: {GRAMPS_DB_FOLDER}\n"
                f"GRAMPS_DB_LOCATION env: {GRAMPS_DB_LOCATION}"
            )
        CONFIGMAN.set("database.path", GRAMPS_DB_FOLDER)
    chatbot = Chatbot(database_name)
    chatbot.chat()
