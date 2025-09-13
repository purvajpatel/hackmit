from openai import OpenAI
from dotenv import load_dotenv
import json
import os

load_dotenv()
client = OpenAI()

def get_rag_recommendations(student_data, transcript_path, labs_data):
    """Get RAG-powered lab recommendations based on student data and transcript.
    
    Args:
        student_data (dict): Student information dictionary
        transcript_path (str): Path to the transcript PDF file
        labs_data (list): List of all available labs
        
    Returns:
        str: Processed recommendation text with specific lab suggestions
    """
    try:
        # Convert student data to JSON string
        student_json = json.dumps(student_data)
        
        # Create context from labs data
        labs_context = ""
        for lab in labs_data[:50]:  # Use top 50 labs for context
            labs_context += f"Lab: {lab['name']}\n"
            labs_context += f"Professor: {lab['professor']}\n"
            labs_context += f"School: {lab['school']}\n"
            labs_context += f"Description: {lab['description']}\n"
            labs_context += f"Website: {lab['url']}\n\n"
        
        # Upload transcript file if provided
        transcript_file_id = None
        if transcript_path and os.path.exists(transcript_path):
            transcript = client.files.create(
                file=open(transcript_path, "rb"),
                purpose="assistants"
            )
            transcript_file_id = transcript.id
        
        # Create the prompt with RAG context
        prompt = f"""
You are an expert academic advisor helping students find the perfect research labs. 

STUDENT INFORMATION:
{student_json}

AVAILABLE RESEARCH LABS:
{labs_context}

Based on the student's academic background, interests, and transcript (if provided), recommend specific research labs that would be perfect for them. 

Please provide:
1. Top 5-7 specific lab recommendations with detailed explanations
2. Why each lab matches their profile
3. What skills/experience they should highlight when applying
4. Next steps for contacting these labs
5. Additional advice for their research journey

Be specific and reference actual lab names, professors, and details from the available labs list.
"""

        # Create thread with user message and transcript attachment
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # Add transcript attachment if available
        if transcript_file_id:
            messages[0]["attachments"] = [
                { "file_id": transcript_file_id, "tools": [{"type": "file_search"}] }
            ]
        
        thread = client.beta.threads.create(messages=messages)
        
        # Run the assistant and wait for completion
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, 
            assistant_id='asst_3BJf52HQP4qM5aKESjZsL1cQ'
        )
        
        # Get messages from the thread
        messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))
        message_content = messages[0].content[0].text
        
        # Process annotations (citations) if they exist
        if hasattr(message_content, 'annotations'):
            annotations = message_content.annotations
            for annotation in annotations:
                message_content.value = message_content.value.replace(annotation.text, "")
        
        return message_content.value if hasattr(message_content, 'value') else str(message_content)
        
    except Exception as e:
        print(f"Error in RAG recommendations: {e}")
        # Fallback response if OpenAI fails
        return get_fallback_recommendations(student_data, labs_data)

def get_fallback_recommendations(student_data, labs_data):
    """Fallback recommendations when OpenAI is not available."""
    major = student_data.get('academic', {}).get('major', '').lower()
    interests = student_data.get('goals', {}).get('interests', [])
    
    # Simple matching logic
    recommended_labs = []
    for lab in labs_data:
        score = 0
        lab_name = lab.get('name', '').lower()
        lab_desc = lab.get('description', '').lower()
        lab_school = lab.get('school', '').lower()
        
        # Score based on major relevance
        if major in lab_desc or major in lab_name:
            score += 3
        
        # Score based on interests
        for interest in interests:
            if interest.lower() in lab_desc or interest.lower() in lab_name:
                score += 2
        
        # Score based on school relevance
        if major in lab_school:
            score += 1
        
        if score > 0:
            lab['relevance_score'] = score
            recommended_labs.append(lab)
    
    # Sort by relevance score
    recommended_labs.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    # Generate fallback response
    response = f"""
# Personalized Lab Recommendations

Based on your profile as a {student_data.get('academic', {}).get('year', 'student')} in {student_data.get('academic', {}).get('major', 'your field')}, here are my top recommendations:

## Top Lab Recommendations:

"""
    
    for i, lab in enumerate(recommended_labs[:5], 1):
        response += f"""
### {i}. {lab['name']}
**Professor:** {lab['professor']}  
**School:** {lab['school']}  
**Relevance Score:** {lab['relevance_score']}/10

**Why this lab is perfect for you:**
{lab['description'][:200]}...

**Next Steps:**
- Visit their website: {lab['url']}
- Research Professor {lab['professor']}'s recent publications
- Prepare a tailored application highlighting your relevant coursework

---

"""
    
    response += """
## Additional Advice:
- Reach out to current lab members for insights
- Attend department seminars to meet professors
- Prepare a strong research proposal
- Highlight relevant coursework and projects in your application

Good luck with your research journey!
"""
    
    return response

# Example usage
if __name__ == "__main__":
    student_info = {
        "name": "John Doe",
        "academic": {
            "major": "computer-science",
            "gpa": "3.2",
            "year": "Junior",
        },
        "goals": {
            "interests": ["artificial intelligence", "machine learning"]
        }
    }
    
    # Mock labs data
    labs_data = [
        {
            "name": "AI Research Lab",
            "professor": "Dr. Smith",
            "school": "Computer Science",
            "description": "Focuses on artificial intelligence and machine learning research",
            "url": "https://example.com"
        }
    ]
    
    recommendations = get_rag_recommendations(student_info, None, labs_data)
    print(recommendations)
