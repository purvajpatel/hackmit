from google.adk.agents import Agent, LoopAgent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService


# Import sub-agents
from .sub_agents.email_gen_agent.agent import email_gen_agent
from .sub_agents.verification_agent.agent import verification_agent
from .sub_agents.email_refiner_agent.agent import email_refiner_agent

# For ADK tools compatibility, the root agent must be named `root_agent`
root_agent = LoopAgent(
    name="EmailContentPipeline",
    max_iterations = 5,
    sub_agents=[     # Run first to create content
        email_gen_agent,
        email_refiner_agent,    # Then generate captions
        verification_agent      # Finally verify and post
    ],
    description='''
    You are this character: {character}

    You are emailing this professor/professional, details included: {recipient_info}
    
    Review feedback from previous iterations: {review_feedback}
    
    You will iteratively generates cold emails to professionals until quality requirements are met. If quality requirements are met, content is emailed via Gmail.

    IMPORTANT: YOU SHOULD NOT HAVE FILL IN THE BLANK FOR THE RECIPIENT INFO. YOU SHOULD USE THE RECIPIENT INFO AND CHARACTER INFO TO GENERATE THE EMAIL. DO NOT HAVE THINGS LIKE "[Your Name]".
'''
    
)