"""
Tools for the verification agent

This module contains all the tool functions used by the verification agent.
"""

from typing import Any, Dict, Optional, List
from google.adk.tools.tool_context import ToolContext
import re
import os
import sys

# Add the parent directory to the path to import main functions
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))


def contains_emoji(text: str) -> bool:
    """Check if text contains emojis"""
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002700-\U000027BF"  # dingbats
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA70-\U0001FAFF"  # symbols & pictographs extended-A
        "]+",
        flags=re.UNICODE
    )
    return bool(emoji_pattern.search(text))


def count_words(text: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Tool to count words in the provided text and provide length-based feedback.
    Updates review_status in the state based on word count requirements.

    Args:
        text: The text to analyze for word count
        tool_context: Context for accessing and updating session state

    Returns:
        Dict[str, Any]: Dictionary containing:
            - result: 'fail' or 'pass'
            - word_count: number of words in text
            - message: feedback message about the length
    """
    words = text.split()
    word_count = len(words)
    MIN_WORDS = 150
    MAX_WORDS = 300

    print("\n----------- TOOL DEBUG -----------")
    print(f"Checking text length: {word_count} words")
    print("----------------------------------\n")

    if word_count < MIN_WORDS:
        words_needed = MIN_WORDS - word_count
        tool_context.state["review_status"] = "fail"
        return {
            "result": "fail",
            "word_count": word_count,
            "words_needed": words_needed,
            "message": f"Email is too short. Add {words_needed} more words to reach minimum length of {MIN_WORDS}.",
        }
    elif word_count > MAX_WORDS:
        words_to_remove = word_count - MAX_WORDS
        tool_context.state["review_status"] = "fail"
        return {
            "result": "fail",
            "word_count": word_count,
            "words_to_remove": words_to_remove,
            "message": f"Email is too long. Remove {words_to_remove} words to meet maximum length of {MAX_WORDS}.",
        }
    elif text.count('#') > 0:
        tool_context.state["review_status"] = "fail"
        return {
            "result": "fail",
            "word_count": word_count,
            "message": "Email contains hashtags. Remove hashtags.",
        }
    elif contains_emoji(text):
        tool_context.state["review_status"] = "fail"
        return {
            "result": "fail",
            "word_count": word_count,
            "message": "Email contains emojis. Remove emojis.",
        }
    else:
        tool_context.state["review_status"] = "pass"
        return {
            "result": "pass",
            "word_count": word_count,
            "message": f"Email length is good ({word_count} words).",
        }


def send_email(email: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Send an email using Gmail API when the email meets all quality requirements.
    
    Args:
        email: The email content to send
        recipient_email: Email address of the recipient
        sender_email: Email address of the sender
        subject: Subject line for the email
        tool_context: Context for tool execution
        
    Returns:
        Dict[str, Any]: Dictionary containing:
            - success: boolean indicating if email was sent successfully
            - message: status message
            - message_id: Gmail message ID if successful
            - error: error message if failed
    
    print("\n----------- SENDING EMAIL -----------")
    print(f"Sending email to: {recipient_email}")
    print(f"Subject: {subject}")
    print("------------------------------------\n")
    
    try:
        # Get credentials file path from environment or use default
        credentials_file = os.getenv('GMAIL_CREDENTIALS_FILE', 'credentials.json')
        
        # Send the email using Gmail API
        result = send_email_gmail(
            sender=sender_email,
            to=recipient_email,
            subject=subject,
            body=email,
            credentials_file=credentials_file
        )
        
        if result['success']:
            print(f"Email sent successfully! Message ID: {result.get('message_id')}")
            return {
                'success': True,
                'message': f'Email sent successfully to {recipient_email}',
                'message_id': result.get('message_id'),
                'thread_id': result.get('thread_id')
            }
        else:
            print(f"Failed to send email: {result.get('error')}")
            return {
                'success': False,
                'message': f'Failed to send email: {result.get("error")}',
                'error': result.get('error')
            }
            
    except Exception as e:
        error_msg = f"Unexpected error while sending email: {str(e)}"
        print(error_msg)
        return {
            'success': False,
            'message': error_msg,
            'error': str(e)
        }
        """
    print(email)
    #global final_email
    #final_email = email
    return {}

def exit_loop(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Call this function ONLY when the post meets all quality requirements,
    signaling the iterative process should end.

    Args:
        tool_context: Context for tool execution

    Returns:
        Empty dictionary
    """
    print("\n----------- EXIT LOOP TRIGGERED -----------")
    print("Post review completed successfully")
    print("Loop will exit now")
    print("------------------------------------------\n")

    # Save the final email to global variable

    tool_context.actions.escalate = True
    return {}
