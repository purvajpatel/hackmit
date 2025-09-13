import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
#from langchain.memory import ConversationBufferMemory
from typing import Optional, List, Dict
import json
import requests
from PIL import Image
from io import BytesIO
import google.generativeai as genai


def return_instructions_email_outreach():
    """Instructions for the cold email outreach agent"""
    return """
    You are an Email Outreach Agent specialized in crafting professional, respectful, and persuasive cold emails to professors or professionals for ***research opportunities***. Your role is to generate well-structured outreach emails that convey interest, highlight qualifications, and increase the chances of a positive response. Try to mention a specific lab. Mention research in subject line.

    Your workflow:
    1. Understand the target recipient (professor/professional) and their area of expertise
    2. Generate a personalized and professional cold email that:
       - Introduces the sender clearly
       - Demonstrates genuine interest in the recipient’s work
       - Highlights relevant skills, experiences, or projects
       - Politely requests a meeting, mentorship, or research opportunity
    3. Optimize for clarity, conciseness, and professionalism
    4. Validate the email against professional communication best practices
    5. Return the final, optimized email

    Focus on creating emails that are:
    - Within the 150-300 word range
    - Respectful and professional
    - Personalized to the recipient’s expertise or research
    - Clear in intent without being overly long
    - Free of grammatical or formatting issues
    - Likely to encourage a reply

    ## RECIPIENT INFO
    {recipient_info}

    ## CHARACTER INFO
    {character}
    
    IMPORTANT: YOU SHOULD NOT HAVE FILL IN THE BLANK FOR THE RECIPIENT OR CHARACTER INFO. YOU SHOULD USE THE RECIPIENT INFO AND CHARACTER INFO TO GENERATE THE EMAIL. DO NOT HAVE PLACEHOLDERS LIKE "[Your Name]".

    ## OUTPUT INSTRUCTIONS:

    Return a dictionary in the following format:

    {
        email: "generated email here"
    }
    """


# Define Caption Generation Agent
email_gen_agent = Agent(
    model='gemini-2.0-flash',
    name='caption_generation_agent',
    instruction=return_instructions_email_outreach(),
    description = 'Generates the initial cold email for the professors/professionals',
    output_key = 'email'
)

if __name__ == "__main__":
    session_service = InMemorySessionService()
    session = session_service.create_session(
        app_name="caption_generation_app",
        user_id="user1",
        session_id="caption_generation_session"
    )
    runner = Runner(
        app_name="caption_generation_app",
        agent=email_gen_agent,
        session_service=session_service
    )
    
    # Test the caption generation agent
    result_generator = runner.run(
        user_id="user1",
        session_id=session.id,
        new_message=types.Content(parts=[types.Part(text="Generate a caption for beauty tips content")])
    )
    
    # Iterate over the generator to get results
    for result in result_generator:
        print(result)