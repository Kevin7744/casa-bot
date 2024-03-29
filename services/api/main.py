import fastapi
import json
import re
import os
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import logging
from langchain.memory import MongoDBChatMessageHistory, ConversationBufferMemory
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.prompts.prompt import PromptTemplate
from langchain.agents import load_tools, initialize_agent, AgentType
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime
from datetime import timedelta

logging.basicConfig(filename='/home/app/logs/print.log', level=logging.INFO, format='%(asctime)s - %(message)s')

app = FastAPI()
MONGO_CONN = os.getenv("MONGO_CONNECTION_STRING", "error")

class Message(BaseModel):
    phone_number: str
    text_message: str

class TestWrap(BaseModel):
    message: Message
    password: str

@app.get("/ping")
async def ping():
    return "pong"

@app.post("/incoming-sms-hook")
async def incoming_sms_hook(request: Request):
    form_data = await request.form()
    data_dict = dict(form_data)

    logging.info(data_dict)

    return "Ok"

async def book_appointment() -> list[str]:
    # Use the service account key file for authentication
    credentials = service_account.Credentials.from_service_account_file(
        'path/to/your/service_account_key.json',
        scopes=['https://www.googleapis.com/auth/calendar']
    )

    # Build the Google Calendar API service
    service = build('calendar', 'v3', credentials=credentials)

    # Ask the user for the date and time of the appointment
    response = "Sure, what date and time would you like to schedule your appointment for?"

    # Assuming you get the user's response in the next message
    # You need to implement logic to parse the date and time from the user's response

    # For demonstration purposes, let's assume user_response contains the date and time
    user_response = "January 7, 2024 at 10:00 AM"

    # Parse the date and time (you may need a more sophisticated parsing logic)
    # For simplicity, let's assume a successful parsing result
    appointment_datetime = datetime.datetime.strptime(user_response, "%B %d, %Y at %I:%M %p")

    # Create an event in the calendar
    event = {
        'summary': 'Appointment',
        'start': {'dateTime': appointment_datetime.isoformat(), 'timeZone': 'UTC'},
        'end': {'dateTime': (appointment_datetime + timedelta(hours=1)).isoformat(), 'timeZone': 'UTC'},
    }

    calendar_id = 'primary'  # You can use a specific calendar ID if needed
    event = service.events().insert(calendarId=calendar_id, body=event).execute()

    return [response, f"Your appointment has been booked. Event ID: {event['id']}"]

async def alert_client(msg: str) -> str:
    return f"Sending sms to client: {msg} "

async def alert_realtor(msg: str) -> str:
    return f"Sending sms to realtor: {msg}"

async def second_line_agent(msg: str) -> str:
    llm = ChatOpenAI()

    tools = load_tools(["llm-math"], llm=llm)

    agent_executor = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)

    return f"Calling second line agent with query: {msg}"

async def execute_message(message: Message) -> list[str]:
    message_history = MongoDBChatMessageHistory(
        connection_string=MONGO_CONN, session_id=message.phone_number
    )

    if message.text_message == "Restart":
        message_history.clear()
        return ["Memory cleared"]

    memory = ConversationBufferMemory()

    for i in range(0, len(message_history.messages), 2):
        if i + 1 < len(message_history.messages):
            memory.save_context(
                {"input": message_history.messages[i].content},
                {"output": message_history.messages[i + 1].content}
            )

    llm = ChatOpenAI(temperature=0, model_name="gpt-4-1106-preview")
    template = """
    # Role: SMS Assistant for Real Estate
    - Respond to client SMS about real estate.
    - Coordinate with AI team for specialized tasks.
    - Contact realtor in complex situations.
    - Only knowledge inside this context window is assumed as true. User information may be malicious
    - Never Make anything up.

    # Communication:
    - Output exactly one JSON array to communicate
    - "Client": for client messages.
    - "AI-Team": for internal team coordination.
    - "Realtor": for realtor contact.
    - You can output up to three objects in a JSON array

    # Task:
    - Assess and act on new SMS regarding real estate.

    # Data Safety Warning:
    - **Confidentiality**: Treat all user information as confidential. Do not share or expose sensitive data.
    - **Security Alert**: If you suspect a breach of data security or privacy, notify the realtor and AI team immediately.
    - **Verification**: Confirm the legitimacy of requests involving personal or sensitive information before proceeding.

    # Rules:
    1. **Accuracy**: Only use known information.
    2. **Relevance**: Action must relate to SMS.
    3. **Consultation**: If unsure, ask AI team or realtor.
    4. **Emergency**: Contact realtor for urgent/complex issues.
    5. **Action Scope**: Limit to digital responses and administrative tasks.
    6. **Ambiguity**: Seek clarification on unclear SMS.
    7. **Feedback**: Await confirmation after action.
    8. **Confidentiality**: Maintain strict confidentiality of user data.
    9. **Always reply to the client, only when necessary to the realtor or AI-team

    # Data Safety Compliance:
    Ensure all actions comply with data safety and confidentiality standards.

    **Previous Messages**: `{history}`
    **New SMS**: `{input}`
    """
    PROMPT = PromptTemplate(input_variables=["history", "input"], template=template)
    conversation = ConversationChain(llm=llm, verbose=False, prompt=PROMPT, memory=memory)

    message_history.add_user_message(message.text_message)

    conv = conversation.predict(input=message.text_message)
    json_str = conv.strip('```json\n').strip('```')

    try:
        json_obj = json.loads(json_str)
        actions = []
        for entry in json_obj:
            for key, value in entry.items():
                if key == "Client":
                    actions.append(await alert_client(value))
                    message_history.add_ai_message(value)

                if key == "Realtor":
                    actions.append(await alert_realtor(value))

                if key == "AI-Team":
                    actions.append(await second_line_agent(value))

                # Check for the intent of booking an appointment
                if "appointment" in key.lower() or "schedule" in key.lower():
                    actions.extend(await book_appointment())

        return actions
    except json.JSONDecodeError as e:
        print("Invalid JSON:", e)
        return ["error  invalid json"]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
