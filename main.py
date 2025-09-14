import asyncio
from dotenv import load_dotenv
from root_agent.agent import root_agent
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from agent_utils import call_agent_async
import json
import os
import argparse
import asyncio
from dedalus_labs import AsyncDedalus, DedalusRunner
from dotenv import load_dotenv
from dedalus_labs.utils.streaming import stream_async

load_dotenv()

# Global variable to store the final email

async def research_query(query):
    client = AsyncDedalus()
    runner = DedalusRunner(client)

    result = await runner.run(
        input= query,
        model="openai/gpt-4.1",
        mcp_servers=[
            "joerup/exa-mcp",        # Semantic search engine
            "tsion/brave-search-mcp",  # Privacy-focused web search
            "dallinger/wikipedia-mcp",  # Wikipedia search
            "modelcontextprotocol/google-search",  # Google search
            "modelcontextprotocol/github"  # GitHub profiles
        ]
    )

    return (f"Web Search Results:\n{result.final_output}")

username =  'makeup_lover300' #args.user


APP_NAMES = "Agentic Test"
USER_IDS = {"makeup_addict100": ["17841475063166045"]}


#Uncomment once more characters are generated for each account

#for i, key in enumerate(USER_IDS.keys()):
#    USER_IDS[key].append(CHARACTERS[i])


db_url = "sqlite:///./my_agent_data.db"

session_service = DatabaseSessionService(db_url = db_url)



async def main_async(APP_NAME, USER_ID, initial_state):

    existing_sessions = await session_service.list_sessions(
        app_name = APP_NAME,
        user_id = USER_ID
    )

    if existing_sessions and len(existing_sessions.sessions) > 0:
        SESSION_ID = existing_sessions.sessions[0].id
        print(f"Continuing session {SESSION_ID}")
    else:
        new_session = await session_service.create_session(
            app_name = APP_NAME,
            user_id = USER_ID,
            state = initial_state
        )
        SESSION_ID = new_session.id
        print("Created new session")

    runner = Runner(
        agent = root_agent,
        app_name = APP_NAME,
        session_service = session_service,
    )

    print("\nWelcome to Content Generation Agent!")

    # Process the user query through the agent
    await call_agent_async(runner, USER_ID, SESSION_ID, '''
You are an outreach strategist for cold emails to professors/professionals. Make sure it is suited for the recipient and uses your professional voice.

Requirements:
- Clear, tailored subject
- ~150–300 words; no emojis/hashtags
- Brief self-intro; 1–2 concrete ties to recipient's work
- 1 clear call-to-action; professional sign-off

Output only the final email (subject + body).
''')
    updated_session = await session_service.get_session(
        app_name = APP_NAME,
        user_id = USER_ID,
        session_id = SESSION_ID
    )

    # Now check if state has the 'generated_email'
    generated_email = updated_session.state.get("email")
    if generated_email is None:
        print("No email found in session state.")
    else:
        print("Here is the generated email:\n")
        print(generated_email)
    return generated_email




async def main():
    import sys
    
    # Check if running from command line with arguments
    if len(sys.argv) > 1:
        # Running from Flask app - get professor and lab info from command line
        professor_name = sys.argv[1] if len(sys.argv) > 1 else "Unknown Professor"
        lab_name = sys.argv[2] if len(sys.argv) > 2 else "Unknown Lab"
        recipient_info = f"Professor: {professor_name}, Lab: {lab_name}"
        
        # Try to load student.json if it exists
        student_file = "student.json"
        if os.path.exists(student_file):
            with open(student_file, "r") as f:
                character_profile = json.load(f)
        else:
            # Fallback to default character
            with open("student_cs.json", "r") as f:
                character_profile = json.load(f)
    else:
        # Running normally - use research query
        recipient_info = await research_query('Give me information about Richard Golden from UT Dallas')
        with open("student_cs.json", "r") as f:
            character_profile = json.load(f)
        
    name = APP_NAMES
    user = username
    initial_state = {
        "user_name": "Alex",
        "recipient_info": recipient_info,
        "character": character_profile,
        "review_feedback": "Initial email generation - no feedback yet"
    }
    # Check if running from Flask app (command line args)
    is_flask_call = len(sys.argv) > 1
    
    if not is_flask_call:
        print(recipient_info)
    
    email = await main_async(APP_NAME=name, USER_ID=user, initial_state=initial_state)
    
    # Clean up database file
    if os.path.exists('my_agent_data.db'):
        os.remove('my_agent_data.db')
        if not is_flask_call:
            print(f"my_agent_data.db deleted.")
    else:
        if not is_flask_call:
            print(f"my_agent_data.db does not exist.")
    
    # If called from Flask, write email to file and output it
    if is_flask_call and email:
        # Write email to file for Flask app to read
        with open("final_email.txt", "w") as f:
            f.write(email)
        print(email)


if __name__ == "__main__":
    asyncio.run(main())
    