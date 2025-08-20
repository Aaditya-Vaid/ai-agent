from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
from googleapiclient.discovery import build
from google.genai.errors import APIError, ClientError
from tenacity import retry, retry_if_exception_type, wait_exponential, stop_after_attempt
import json
import logging


from .tools import get_weather, add_draft, send_email, update_draft, list_drafts
from .auth import authorize

load_dotenv()
MODEL = os.getenv("MODEL")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, max=60, min=1),
    retry=retry_if_exception_type((APIError, ClientError))
)
def _function_calling_with_retry(contents, config):
    """Helper function to call the model with retry logic."""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=config
    )
    return response

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, max=60, min=1),
    retry=retry_if_exception_type((APIError, ClientError))
)
def _tool_response_with_retry(contents):
    """Helper function to get tool responses with retry logic."""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=MODEL,
        contents=contents
    )
    return response

class Agent:
    def __init__(self):
        self.contents = self._initialize_contents()
        self.function_declarations = self._get_function_declarations()
        self.tools = types.Tool(function_declarations=self.function_declarations)
        self.config = types.GenerateContentConfig(tools=[self.tools])
        self.available_tools = {
            "get_weather": get_weather,
            "add_draft": add_draft,
            "send_email": send_email,
            "list_drafts": list_drafts,
            "update_draft": update_draft
        }

    def _initialize_contents(self):
        """Initializes the system prompt with user profile information."""
        user_profile = self._get_user_profile()
        system_prompt = f"""
        User profile is {user_profile}
        For multiple tasks in a single query, treat each task as a separate query.
        
        In case of using tool related to weather:
        for each city/place mentioned, call the functions separately.
        
        In case of using tool related to gmail:
        If the user asks for writing an email or drafting an email then always write an email first before calling any tool and get it checked by human.
        If the user approves the email, ask for sending the email. If the user agrees then call the send_email function, otherwise add the email to the drafts by calling add_draft function.
        If the user rejects the email or ask for changing the email, re-write the email.
        
        Format of email should be:
        to: string
        subject: string
        body: string
        
        If the user asks for list of drafts, call list_drafts function and give user a list containing draft information like draft id, recipients, subject and body.
        If the user asks to update a pre-existing draft, before updating the draft, write a new email then ask user if its okay or not. If the user is okay with the new email call update_draft function and make sure that you have draft id.
        """
        return [("system", system_prompt)]

    def _get_function_declarations(self):
        """Defines and returns the tool definitions for the model."""
        return [
            {
                "name": "get_weather",
                "description": "Returns weather information of a place.",
                "parameters": {
                    "type": "object",
                    "properties":{
                        "place": {"type": "string", "description": "Name of the place"},
                        "aqi": {"type": "boolean", "description": "True if aqi is asked else False."}
                    },
                    "required": ["place", "aqi"]
                }
            },
            {
                "name": "add_draft",
                "description": "Adds the draft into drafts",
                "parameters": {
                    "type": "object",
                    "properties":{
                        "to": {"type": "string", "description": "email address of the reciever"},
                        "subject": {"type": "string", "description": "subject of the email"},
                        "body": {"type": "string", "description": "actual body of the email"}
                    },
                    "required": ["to", "subject", "body"]
                }
            },
            {
                "name": "send_email",
                "description": "sends the email",
                "parameters": {
                    "type": "object",
                    "properties":{
                        "to": {"type": "string", "description": "email address of the reciever"},
                        "subject": {"type": "string", "description": "subject of the email"},
                        "body": {"type": "string", "description": "actual body of the email"}
                    },
                    "required": ["to", "subject", "body"]
                }
            },
            {
                "name": "list_drafts",
                "description": "returns a list of drafts"
            },
            {
                "name": "update_draft",
                "description": "Updates a pre-existing draft.",
                "parameters":{
                    "type": "object",
                    "properties":{
                        "draft_id": {"type": "string", "description": "Id of the draft to be updated."},
                        "to": {"type": "string", "description": "email address of the reciever"},
                        "subject": {"type": "string", "description": "subject of the email"},
                        "body": {"type": "string", "description": "actual body of the email"}
                    },
                    "required":["draft_id", "to", "subject", "body"]
                }
            }
        ]

    def _get_user_profile(self):
        """Fetches the user's profile using the People API."""
        creds = authorize()
        if not creds:
            return "Unable to retrieve user profile."
        try:
            people_service = build('people', 'v1', credentials=creds)
            user_profile = people_service.people().get(
                resourceName='people/me',
                personFields='names,emailAddresses'
            ).execute()
            return user_profile
        except Exception as e:
            logging.error(f"Error fetching user profile: {e}")
            return "Unable to retrieve user profile."

    def _handle_tool_calls(self, tool_calls):
        """Executes tool calls and appends their responses to the conversation."""
        if not tool_calls:
            return
        
        for tool_call in tool_calls:
            function_name = tool_call.name
            call_function = self.available_tools.get(function_name)
            if not call_function:
                logging.warning(f"Tool '{function_name}' not found.")
                continue
            
            function_args = tool_call.args
            function_response = call_function(**function_args)
            
            logging.info(f"Calling tool: {function_name} with args: {json.dumps(function_args)}")
            logging.info(f"Tool response: {json.dumps(function_response)}")
            
            function_response_part = types.Part.from_function_response(
                name=tool_call.name,
                response={"result": function_response}
            )
            self.contents.append(types.Content(role="tool", parts=[function_response_part]))
    
    def run(self):
        """The main conversational loop."""
        user_name = self._get_user_profile()
        if user_name != "Unable to retrieve user profile.":
            logging.info(f"Agent initialized for user: {self.user_profile['names'][0]['givenName']}")
            print(f"Hello, {user_name['names'][0]['givenName']}!")
        
        while True:
            user_query = input("User: ")
            if user_query.lower() in ("bye", "exit", "goodbye", "quit"):
                logging.info(f"Human message: {user_query}. Exiting application.")
                print("Goodbye! 👋")
                break

            logging.info("="*30+" Human Message "+"="*27)
            logging.info(user_query)
            
            try:
                self.contents.append(("user", user_query))
                
                response = _function_calling_with_retry(self.contents, self.config)
                self.contents.append(response.candidates[0].content)
                
                tool_calls = response.function_calls
                if tool_calls:
                    self._handle_tool_calls(tool_calls)
                    response = _tool_response_with_retry(self.contents)
                    self.contents.append(response.candidates[0].content)
                
                logging.info("="*30+" AI Message "+"="*30)
                logging.info(response.text)
            
            except (APIError, ClientError) as e:
                logging.error(f"API Error: {e}. Resetting conversation state.")
                print("An API error occurred. Let's try again from the beginning.")
                self.contents = self._initialize_contents()
            except Exception as e:
                logging.critical(f"An unexpected error occurred in the main loop: {e}", exc_info=True)
                print("An unexpected error occurred. Exiting.")
                break

if __name__ == "__main__":
    agent = Agent()
    agent.run()