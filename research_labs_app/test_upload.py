#!/usr/bin/env python3
import requests
import json
import os

# Test the transcript upload functionality
def test_transcript_upload():
    print("🧪 Testing transcript upload functionality...")
    
    # Test data
    student_data = {
        "name": "Test Student",
        "academic": {
            "major": "Computer Science",
            "gpa": "3.5",
            "year": "Junior"
        },
        "goals": {
            "careerGoals": ["research"],
            "interests": ["artificial intelligence", "machine learning"]
        }
    }
    
    # Create a test PDF file
    test_pdf_content = b"Test transcript content for upload testing"
    test_file_path = "test_transcript.pdf"
    with open(test_file_path, "wb") as f:
        f.write(test_pdf_content)
    
    try:
        # Test the RAG endpoint
        files = {'transcript': open(test_file_path, 'rb')}
        data = {'student_data': json.dumps(student_data)}
        
        response = requests.post('http://localhost:8080/api/rag-recommendations', 
                               files=files, data=data, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✅ Upload successful!")
            print(f"Response length: {len(result.get('recommendations', ''))}")
        else:
            print(f"❌ Upload failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Clean up test file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

if __name__ == "__main__":
    test_transcript_upload()
