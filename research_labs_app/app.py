# app.py
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import json, os, uuid
import re
from pypdf import PdfReader
from datetime import datetime
import tempfile
import io
from lab_data_service import LabDataService
import asyncio

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'pdf'}
CLIENT_MAX_MB = 16
SERVER_MAX_MB = 32

app = Flask(__name__, static_folder='static', template_folder='templates')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = SERVER_MAX_MB * 1024 * 1024

# -------------------- Optional Gemini RAG --------------------
try:
    from gemini_advisor import get_gemini_rag_recommendations
    GEMINI_AVAILABLE = True
except Exception as e:
    print(f"Gemini AI not available or failed to import: {e}")
    GEMINI_AVAILABLE = False

# Optional OpenAI provider
try:
    from openai_advisor import get_openai_rag_recommendations  # type: ignore
    OPENAI_AVAILABLE = True
except Exception as e:
    print(f"OpenAI advisor not available: {e}")
    OPENAI_AVAILABLE = False

AI_PROVIDER = os.getenv('AI_PROVIDER', 'gemini').lower()
def load_labs_data():
    path = os.path.join(DATA_DIR, 'utd_all_labs.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except FileNotFoundError:
        print(f"[WARN] Labs data not found at {path}. Returning empty list.")
        return []
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse labs JSON: {e}")
        return []

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_pdf_text(pdf_path: str) -> str:
    try:
        reader = PdfReader(pdf_path)
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or '')
            except Exception:
                continue
        return "\n".join(texts)
    except Exception:
        return ''

COURSE_TOKEN_RE = re.compile(r"([A-Z]{2,4})\s?-?\s?(\d{3,4})|([A-Za-z][\w\s&/-]{2,40})\s?(?:\(?\d+\)?\s*credits?)?", re.IGNORECASE)

def extract_coursework_hint(text: str, limit: int = 20):
    if not text: return []
    candidates = set()
    for m in COURSE_TOKEN_RE.finditer(text):
        token = (m.group(0) or '').strip()
        if len(token) >= 3:
            candidates.add(token[:80])
        if len(candidates) >= limit:
            break
    return list(candidates)

def enhance_student_data(student_data):
    """Enhance student data by parsing transcript text and extracting comprehensive information"""
    enhanced_data = student_data.copy()
    
    # Get transcript text if available
    transcript_text = student_data.get('transcript_text', '')
    
    if transcript_text:
        print(f"Parsing transcript text ({len(transcript_text)} characters)")
        
        # Extract name from transcript
        if not enhanced_data.get('name'):
            name_patterns = [
                r'(?:Name|Student Name|Full Name)[:\s]+([A-Za-z\s]+)',
                r'^([A-Z][a-z]+ [A-Z][a-z]+)',
                r'(?:Applicant|Candidate)[:\s]+([A-Za-z\s]+)'
            ]
            for pattern in name_patterns:
                name_match = re.search(pattern, transcript_text, re.IGNORECASE | re.MULTILINE)
                if name_match:
                    enhanced_data['name'] = name_match.group(1).strip()
                    break
        
        # Extract major from transcript
        if not enhanced_data.get('academic', {}).get('major'):
            major_patterns = [
                r'(?:Major|Program|Degree|Field of Study)[:\s]+([A-Za-z\s&]+)',
                r'(?:Bachelor|Master|PhD) of ([A-Za-z\s]+)',
                r'(?:Computer Science|Engineering|Mathematics|Physics|Biology|Chemistry|Psychology|Business)'
            ]
            for pattern in major_patterns:
                major_match = re.search(pattern, transcript_text, re.IGNORECASE)
                if major_match:
                    if 'academic' not in enhanced_data:
                        enhanced_data['academic'] = {}
                    enhanced_data['academic']['major'] = major_match.group(1).strip()
                    break
        
        # Extract GPA from transcript
        if not enhanced_data.get('academic', {}).get('gpa'):
            gpa_patterns = [
                r'(?:GPA|Grade Point Average)[:\s]+(\d+\.?\d*)',
                r'(?:Overall GPA|Cumulative GPA)[:\s]+(\d+\.?\d*)',
                r'GPA[:\s]*(\d+\.?\d*)'
            ]
            for pattern in gpa_patterns:
                gpa_match = re.search(pattern, transcript_text, re.IGNORECASE)
                if gpa_match:
                    if 'academic' not in enhanced_data:
                        enhanced_data['academic'] = {}
                    enhanced_data['academic']['gpa'] = gpa_match.group(1)
                    break
        
        # Extract year/level from transcript
        if not enhanced_data.get('academic', {}).get('year'):
            year_patterns = [
                r'(?:Year|Level|Status|Class)[:\s]+(Freshman|Sophomore|Junior|Senior|Graduate|Undergraduate|Graduate Student)',
                r'(?:Currently|Currently enrolled as)[:\s]+(Freshman|Sophomore|Junior|Senior|Graduate)',
                r'(?:Academic Standing)[:\s]+(Freshman|Sophomore|Junior|Senior|Graduate)'
            ]
            for pattern in year_patterns:
                year_match = re.search(pattern, transcript_text, re.IGNORECASE)
                if year_match:
                    if 'academic' not in enhanced_data:
                        enhanced_data['academic'] = {}
                    enhanced_data['academic']['year'] = year_match.group(1)
                    break
        
        # Extract comprehensive coursework
        coursework = extract_coursework_hint(transcript_text, limit=50)
        if coursework:
            enhanced_data['coursework'] = coursework
        
        # Extract skills/technologies mentioned
        skills = []
        skill_keywords = [
            'python', 'java', 'javascript', 'c++', 'c#', 'matlab', 'r', 'sql', 'html', 'css',
            'machine learning', 'ai', 'artificial intelligence', 'data science', 'statistics',
            'research', 'analysis', 'deep learning', 'neural networks', 'tensorflow', 'pytorch',
            'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring', 'git', 'docker',
            'kubernetes', 'aws', 'azure', 'gcp', 'linux', 'unix', 'database', 'mongodb',
            'postgresql', 'mysql', 'redis', 'kafka', 'spark', 'hadoop', 'blockchain'
        ]
        for keyword in skill_keywords:
            if keyword.lower() in transcript_text.lower():
                skills.append(keyword.title())
        if skills:
            enhanced_data['skills'] = list(set(skills))
        
        # Extract projects
        projects = []
        project_patterns = [
            r'(?:Project|Capstone|Thesis|Dissertation)[:\s]+([^.\n]+)',
            r'(?:Developed|Created|Built|Designed)[:\s]+([^.\n]+)',
            r'(?:Worked on|Implemented|Programmed)[:\s]+([^.\n]+)',
            r'(?:Final Project|Senior Project|Research Project)[:\s]+([^.\n]+)'
        ]
        for pattern in project_patterns:
            matches = re.findall(pattern, transcript_text, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 10:  # Filter out very short matches
                    projects.append(match.strip())
        
        if projects:
            enhanced_data['projects'] = list(set(projects))[:10]  # Limit to 10 projects
        
        # Extract internships and work experience
        internships = []
        work_patterns = [
            r'(?:Internship|Intern)[:\s]+([^.\n]+)',
            r'(?:Worked at|Employed at|Position at)[:\s]+([^.\n]+)',
            r'(?:Experience at|Role at)[:\s]+([^.\n]+)',
            r'(?:Summer Intern|Research Intern|Software Intern)[:\s]+([^.\n]+)'
        ]
        for pattern in work_patterns:
            matches = re.findall(pattern, transcript_text, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 10:
                    internships.append(match.strip())
        
        if internships:
            enhanced_data['internships'] = list(set(internships))[:5]  # Limit to 5 internships
        
        # Extract research experience
        research_experience = []
        research_patterns = [
            r'(?:Research|Study|Investigation)[:\s]+([^.\n]+)',
            r'(?:Research Assistant|Research Intern)[:\s]+([^.\n]+)',
            r'(?:Published|Co-authored)[:\s]+([^.\n]+)',
            r'(?:Conference|Journal|Paper)[:\s]+([^.\n]+)'
        ]
        for pattern in research_patterns:
            matches = re.findall(pattern, transcript_text, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 10:
                    research_experience.append(match.strip())
        
        if research_experience:
            enhanced_data['research_experience'] = list(set(research_experience))[:5]
        
        # Extract achievements and awards
        achievements = []
        achievement_patterns = [
            r'(?:Award|Recognition|Honor)[:\s]+([^.\n]+)',
            r'(?:Dean\'s List|Honor Roll|Scholarship)[:\s]+([^.\n]+)',
            r'(?:Competition|Contest|Hackathon)[:\s]+([^.\n]+)',
            r'(?:Winner|Finalist|Participant)[:\s]+([^.\n]+)'
        ]
        for pattern in achievement_patterns:
            matches = re.findall(pattern, transcript_text, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 10:
                    achievements.append(match.strip())
        
        if achievements:
            enhanced_data['achievements'] = list(set(achievements))[:5]
        
        # Extract extracurricular activities
        activities = []
        activity_patterns = [
            r'(?:Club|Organization|Society)[:\s]+([^.\n]+)',
            r'(?:Volunteer|Community Service)[:\s]+([^.\n]+)',
            r'(?:Leadership|President|Vice President|Secretary)[:\s]+([^.\n]+)',
            r'(?:Member of|Active in)[:\s]+([^.\n]+)'
        ]
        for pattern in activity_patterns:
            matches = re.findall(pattern, transcript_text, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 10:
                    activities.append(match.strip())
        
        if activities:
            enhanced_data['extracurricular_activities'] = list(set(activities))[:5]
        
        # Extract relevant courses (more specific than coursework)
        relevant_courses = []
        course_patterns = [
            r'(?:CS|CSE|ECE|MATH|STAT|PHYS|CHEM|BIO)\s*\d{3,4}[:\s]+([^.\n]+)',
            r'(?:Course|Class)[:\s]+([A-Za-z\s]+(?:Programming|Data|Machine|AI|Software|Algorithm|Database|Network))',
            r'(?:Advanced|Upper-level)[:\s]+([^.\n]+)'
        ]
        for pattern in course_patterns:
            matches = re.findall(pattern, transcript_text, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 5:
                    relevant_courses.append(match.strip())
        
        if relevant_courses:
            enhanced_data['relevant_courses'] = list(set(relevant_courses))[:10]
        
        print(f"Extracted data: {len(enhanced_data)} fields")
    
    # Ensure all required fields have default values
    if not enhanced_data.get('name'):
        enhanced_data['name'] = 'Student'
    if 'academic' not in enhanced_data:
        enhanced_data['academic'] = {}
    if not enhanced_data['academic'].get('major'):
        enhanced_data['academic']['major'] = 'Computer Science'
    if not enhanced_data['academic'].get('gpa'):
        enhanced_data['academic']['gpa'] = '3.5'
    if not enhanced_data['academic'].get('year'):
        enhanced_data['academic']['year'] = 'Junior'
    
    # Add a summary of extracted information
    enhanced_data['extraction_summary'] = {
        'total_fields': len(enhanced_data),
        'has_projects': 'projects' in enhanced_data,
        'has_internships': 'internships' in enhanced_data,
        'has_research': 'research_experience' in enhanced_data,
        'has_skills': 'skills' in enhanced_data,
        'extraction_timestamp': str(datetime.now())
    }
    
    return enhanced_data

# ---- Errors ----
@app.errorhandler(413)
def too_large(e): return jsonify({'error': f'File too large. Max {CLIENT_MAX_MB}MB allowed.'}), 413
@app.errorhandler(404)
def not_found(e): return jsonify({'error': 'Not found'}), 404
@app.errorhandler(500)
def server_error(e): return jsonify({'error': 'Internal server error'}), 500

# ---- Routes ----
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/api/status')
def get_status():
    return jsonify({
        'status': 'running',
        'ai_provider': AI_PROVIDER,
        'gemini_available': GEMINI_AVAILABLE,
        'openai_available': OPENAI_AVAILABLE,
        'limits': {'client_max_mb': CLIENT_MAX_MB, 'server_max_mb': SERVER_MAX_MB},
        'features': {
            'lab_browsing': True,
            'basic_recommendations': True,
            'rag_analysis': GEMINI_AVAILABLE or OPENAI_AVAILABLE,
            'transcript_upload': GEMINI_AVAILABLE or OPENAI_AVAILABLE
        }
    })

@app.route('/api/labs')
def get_labs():
    labs = load_labs_data()
    school = (request.args.get('school') or '').strip().lower()
    search = (request.args.get('search') or '').strip().lower()
    professor = (request.args.get('professor') or '').strip().lower()
    professor_email_q = (request.args.get('professor_email') or '').strip().lower()

    def matches(lab):
        name = (lab.get('name') or '').lower()
        desc = (lab.get('description') or '').lower()
        prof = (lab.get('professor') or '').lower()
        prof_email = (lab.get('professor_email') or '').lower()
        schl = (lab.get('school') or '').lower()
        if school and school not in schl: return False
        if professor and professor not in prof: return False
        if professor_email_q and professor_email_q not in prof_email: return False
        if search and not (search in name or search in desc or search in prof or search in schl): return False
        return True

    if school or search or professor or professor_email_q:
        labs = [lab for lab in labs if matches(lab)]
    return jsonify(labs)

@app.route('/api/schools')
def get_schools():
    labs = load_labs_data()
    return jsonify(sorted({lab.get('school', '') for lab in labs if lab.get('school')}))

@app.route('/api/lab/<int:lab_id>')
def get_lab_details(lab_id):
    labs = load_labs_data()
    if 0 <= lab_id < len(labs): return jsonify(labs[lab_id])
    return jsonify({'error': 'Lab not found'}), 404

@app.route('/api/recommendations', methods=['POST'])
def get_recommendations():
    try:
        payload = request.get_json(force=True, silent=False)
        major = (payload.get('major') or '').lower()
        interests = [str(x).lower() for x in (payload.get('interests') or [])]

        labs = load_labs_data()
        recommended = []
        for lab in labs:
            score = 0
            name = (lab.get('name') or '').lower()
            desc = (lab.get('description') or '').lower()
            school = (lab.get('school') or '').lower()

            if major and (major in name or major in desc): score += 3
            for it in interests:
                if it and (it in name or it in desc): score += 2
            if major and major in school: score += 1

            if score > 0:
                lab_copy = dict(lab)
                lab_copy['relevance_score'] = score
                recommended.append(lab_copy)

        recommended.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return jsonify({'recommendations': recommended[:10], 'total_labs': len(labs), 'matching_labs': len(recommended)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rag-recommendations', methods=['POST'])
def rag_recommendations():
    transcript_path = None
    try:
        student_json = request.form.get('student_data')
        if not student_json: return jsonify({'error': 'Missing student data'}), 400
        try:
            student_data = json.loads(student_json)
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON in student_data'}), 400

        f = request.files.get('transcript')
        if f and f.filename:
            if not allowed_file(f.filename):
                return jsonify({'error': f'Only .pdf files are allowed (max {CLIENT_MAX_MB}MB).'}), 400
            safe = secure_filename(f.filename)
            unique = f"{uuid.uuid4().hex}_{safe}"
            transcript_path = os.path.join(app.config['UPLOAD_FOLDER'], unique)
            f.save(transcript_path)

        labs_data = load_labs_data()

        transcript_text = extract_pdf_text(transcript_path) if transcript_path else ''
        coursework = extract_coursework_hint(transcript_text)

        # Enhanced student data with transcript information
        enhanced_student_data = {**student_data, 'transcript_text': transcript_text, 'coursework': coursework}
        
        # Save enhanced student data to student.json for email generation
        student_json_path = os.path.join(BASE_DIR, '..', 'student.json')
        with open(student_json_path, 'w', encoding='utf-8') as f:
            json.dump(enhanced_student_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved enhanced student data to student.json with {len(enhanced_student_data)} fields")
        print(f"Transcript text length: {len(transcript_text)} characters")
        print(f"Coursework extracted: {len(coursework)} items")

        # Provider switch: prefer OpenAI if chosen and available; else Gemini
        if AI_PROVIDER == 'openai':
            if not OPENAI_AVAILABLE:
                return jsonify({'error': 'OpenAI provider not available. Install openai and set OPENAI_API_KEY.'}), 503
            recs = get_openai_rag_recommendations(
                student_data=enhanced_student_data,
                transcript_path=transcript_path,
                labs_data=labs_data
            )
        else:
            if not GEMINI_AVAILABLE:
                return jsonify({'error': 'Gemini provider not available. Install google-generativeai and set GEMINI_API_KEY.'}), 503
            recs = get_gemini_rag_recommendations(
                student_data=enhanced_student_data,
                transcript_path=transcript_path,
                labs_data=labs_data
            )
        return jsonify({'recommendations': recs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if transcript_path and os.path.exists(transcript_path):
            try: os.remove(transcript_path)
            except OSError: pass

@app.route('/api/search-university-labs', methods=['POST'])
def search_university_labs():
    """Search for labs at a specific university using MCP agents"""
    try:
        data = request.get_json()
        university_name = data.get('university_name', '').strip()
        
        if not university_name:
            return jsonify({'error': 'University name is required'}), 400
        
        # Initialize the lab data service
        lab_service = LabDataService()
        
        # Run the async search
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            labs = loop.run_until_complete(lab_service.search_university_labs(university_name, limit=20))
        finally:
            loop.close()
        
        return jsonify({
            'success': True,
            'university': university_name,
            'labs': labs,
            'count': len(labs)
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to search university labs: {str(e)}'}), 500

@app.route('/api/draft-email', methods=['POST'])
def draft_email():
    """Generate a cold email for a specific professor/lab"""
    try:
        data = request.get_json()
        professor_name = data.get('professor_name', '').strip()
        lab_name = data.get('lab_name', '').strip()
        student_data = data.get('student_data', {})
        
        print(f"Received data: {data}")
        print(f"Student data: {student_data}")
        
        if not professor_name or not lab_name:
            return jsonify({'error': 'Professor name and lab name are required'}), 400
        
        # Check if student.json already exists (from RAG analysis)
        student_json_path = os.path.join(BASE_DIR, '..', 'student.json')
        
        if os.path.exists(student_json_path):
            # Use existing student data from RAG analysis
            with open(student_json_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            print(f"Using existing student data from RAG analysis with {len(existing_data)} fields")
        else:
            # Fallback: enhance the current student data
            enhanced_student_data = enhance_student_data(student_data)
            with open(student_json_path, 'w', encoding='utf-8') as f:
                json.dump(enhanced_student_data, f, indent=2, ensure_ascii=False)
            print(f"Created new student data with {len(enhanced_student_data)} fields")
        
        # Import and run the email generation system
        import subprocess
        import sys
        
        # Create a research query for the professor
        research_query = f"Give me information about {professor_name} from {lab_name}"
        
        # Run the main.py email generation system with professor and lab arguments
        result = subprocess.run([
            sys.executable, 
            os.path.join(BASE_DIR, '..', 'main.py'),
            professor_name,
            lab_name
        ], 
        capture_output=True, 
        text=True, 
        cwd=os.path.join(BASE_DIR, '..')
        )
        
        if result.returncode != 0:
            return jsonify({'error': f'Email generation failed: {result.stderr}'}), 500
        
        # Read the generated email from the file that main.py creates
        email_file_path = os.path.join(BASE_DIR, '..', 'final_email.txt')
        if not os.path.exists(email_file_path):
            return jsonify({'error': 'Email file was not created'}), 500
        
        with open(email_file_path, 'r', encoding='utf-8') as f:
            email_content = f.read().strip()
        
        if not email_content:
            return jsonify({'error': 'No email content found in file'}), 500
        
        return jsonify({
            'success': True,
            'email': email_content,
            'professor_name': professor_name,
            'lab_name': lab_name
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate email: {str(e)}'}), 500

@app.route('/generate_questions', methods=['POST'])
def generate_questions():
    """Generate interview questions based on lab information"""
    try:
        data = request.get_json()
        professor_name = data.get('professor_name', '')
        lab_name = data.get('lab_name', '')
        lab_description = data.get('lab_description', '')
        
        if not professor_name or not lab_name:
            return jsonify({'error': 'Professor name and lab name are required'}), 400
        
        # Generate questions using AI
        questions = generate_interview_questions(professor_name, lab_name, lab_description)
        
        return jsonify({
            'success': True,
            'questions': questions
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate questions: {str(e)}'}), 500

@app.route('/analyze_interview', methods=['POST'])
def analyze_interview():
    """Analyze uploaded interview answer audio and provide AI feedback"""
    try:
        # Get uploaded audio file
        audio_file = request.files.get('audio')
        question_text = request.form.get('question_text', '')
        lab_context = request.form.get('lab_context', '')
        
        if not audio_file:
            return jsonify({'error': 'No audio file provided'}), 400
        
        # Save audio file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            audio_file.save(temp_audio.name)
            temp_audio_path = temp_audio.name
        
        try:
            # Transcribe audio using Gemini (or fallback to OpenAI)
            transcript = transcribe_audio(temp_audio_path)
            
            # Generate feedback using AI
            feedback = generate_interview_feedback(transcript, question_text, lab_context)
            
            return jsonify({
                'success': True,
                'feedback': feedback,
                'transcript': transcript
            })
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
                
    except Exception as e:
        return jsonify({'error': f'Failed to analyze interview: {str(e)}'}), 500

def transcribe_audio(audio_path):
    """Transcribe audio using available AI provider"""
    try:
        if AI_PROVIDER == 'gemini' and GEMINI_AVAILABLE:
            return transcribe_with_gemini(audio_path)
        elif AI_PROVIDER == 'openai' and OPENAI_AVAILABLE:
            return transcribe_with_openai(audio_path)
        else:
            # Fallback: return a placeholder transcript
            return "[Audio transcription not available - using mock transcript for demo]"
    except Exception as e:
        print(f"Transcription error: {e}")
        return "[Transcription failed - using mock transcript for demo]"

def transcribe_with_gemini(audio_path):
    """Transcribe audio using Gemini"""
    try:
        from google import genai
        
        # Create Gemini client
        client = genai.Client()
        
        # Upload audio file to Gemini
        audio_file = client.files.upload(file=audio_path)
        
        # Generate transcription
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[
                "Generate a transcript of the speech. Only return the transcription text, no additional commentary.",
                audio_file
            ]
        )
        
        return response.text.strip()
        
    except Exception as e:
        print(f"Gemini transcription error: {e}")
        raise

def transcribe_with_openai(audio_path):
    """Transcribe audio using OpenAI Whisper"""
    try:
        import openai
        
        with open(audio_path, 'rb') as audio_file:
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file
            )
        
        return transcript.text.strip()
        
    except Exception as e:
        print(f"OpenAI transcription error: {e}")
        raise

def generate_interview_questions(professor_name, lab_name, lab_description):
    """Generate interview questions based on lab information"""
    try:
        if AI_PROVIDER == 'gemini' and GEMINI_AVAILABLE:
            return generate_questions_with_gemini(professor_name, lab_name, lab_description)
        elif AI_PROVIDER == 'openai' and OPENAI_AVAILABLE:
            return generate_questions_with_openai(professor_name, lab_name, lab_description)
        else:
            # Fallback mock questions
            return generate_mock_questions(professor_name, lab_name)
    except Exception as e:
        print(f"Question generation error: {e}")
        return generate_mock_questions(professor_name, lab_name)

def generate_interview_feedback(transcript, question_text, lab_context):
    """Generate AI feedback for interview answer"""
    try:
        if AI_PROVIDER == 'gemini' and GEMINI_AVAILABLE:
            return generate_interview_feedback_with_gemini(transcript, question_text, lab_context)
        elif AI_PROVIDER == 'openai' and OPENAI_AVAILABLE:
            return generate_interview_feedback_with_openai(transcript, question_text, lab_context)
        else:
            # Fallback mock feedback
            return generate_mock_interview_feedback(transcript, question_text)
    except Exception as e:
        print(f"Feedback generation error: {e}")
        return generate_mock_interview_feedback(transcript, question_text)

def generate_questions_with_gemini(professor_name, lab_name, lab_description):
    """Generate interview questions using Gemini"""
    try:
        import google.generativeai as genai
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""You are a research professor conducting interviews for undergraduate research positions.

Generate 5 realistic interview questions that {professor_name} from {lab_name} might ask a student.

Lab Context:
{lab_description}

Generate questions that cover:
1. Technical background and skills
2. Research interest and motivation
3. Problem-solving approach
4. Time commitment and availability
5. Specific knowledge related to the lab's research area

Return ONLY a JSON array of question strings, no additional text.
Example format: ["Question 1?", "Question 2?", "Question 3?", "Question 4?", "Question 5?"]"""
        
        response = model.generate_content(prompt)
        
        # Parse JSON response
        import json
        try:
            questions = json.loads(response.text.strip())
            return questions if isinstance(questions, list) else []
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return generate_mock_questions(professor_name, lab_name)
        
    except Exception as e:
        print(f"Gemini question generation error: {e}")
        raise

def generate_interview_feedback_with_gemini(transcript, question_text, lab_context):
    """Generate interview feedback using Gemini"""
    try:
        import google.generativeai as genai
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""You are an expert interview coach helping students prepare for research lab interviews.

The student was asked this question:
**Question:** {question_text}

**Lab Context:** {lab_context}

**Student's Answer Transcript:**
{transcript}

WRITE THE FIRST SENTENCE OF THEIR TRANSCRIPT

YOU MUST USE YOU AND ANALYZE THEIR TRANSCRIPT

Analyze their answer in these categories:
- **Content Quality**: Did they answer the question thoroughly and demonstrate relevant knowledge?
- **Communication Skills**: How clear and articulate was their response?
- **Enthusiasm & Interest**: Did they show genuine passion for the research?
- **Professionalism**: How professional and prepared did they sound?
- **Overall Impression**: What's your assessment of their interview performance?

Use second person ("you") and be constructive but direct.
Format your response with bold section headers and clear feedback."""
        
        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        print(f"Gemini interview feedback error: {e}")
        raise

def generate_questions_with_openai(professor_name, lab_name, lab_description):
    """Generate interview questions using OpenAI"""
    try:
        import openai
        
        prompt = f"""You are a research professor conducting interviews for undergraduate research positions.

Generate 5 realistic interview questions that {professor_name} from {lab_name} might ask a student.

Lab Context:
{lab_description}

Generate questions that cover:
1. Technical background and skills
2. Research interest and motivation
3. Problem-solving approach
4. Time commitment and availability
5. Specific knowledge related to the lab's research area

Return ONLY a JSON array of question strings, no additional text.
Example format: ["Question 1?", "Question 2?", "Question 3?", "Question 4?", "Question 5?"]"""
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a research professor conducting interviews."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.7
        )
        
        # Parse JSON response
        import json
        try:
            questions = json.loads(response.choices[0].message.content.strip())
            return questions if isinstance(questions, list) else []
        except json.JSONDecodeError:
            return generate_mock_questions(professor_name, lab_name)
        
    except Exception as e:
        print(f"OpenAI question generation error: {e}")
        raise

def generate_interview_feedback_with_openai(transcript, question_text, lab_context):
    """Generate interview feedback using OpenAI"""
    try:
        import openai
        
        prompt = f"""You are an expert interview coach helping students prepare for research lab interviews.

The student was asked this question:
**Question:** {question_text}

**Lab Context:** {lab_context}

**Student's Answer Transcript:**
{transcript}

Analyze their answer in these categories:
- **Content Quality**: Did they answer the question thoroughly and demonstrate relevant knowledge?
- **Communication Skills**: How clear and articulate was their response?
- **Enthusiasm & Interest**: Did they show genuine passion for the research?
- **Professionalism**: How professional and prepared did they sound?
- **Overall Impression**: What's your assessment of their interview performance?

Then give 2-3 specific, actionable tips to improve their answer.
Use second person ("you") and be constructive but direct.
Format your response with bold section headers and clear feedback."""
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert interview coach."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"OpenAI interview feedback error: {e}")
        raise

def generate_mock_questions(professor_name, lab_name):
    """Generate mock interview questions when AI providers are unavailable"""
    return [
        "Tell me about your background and what interests you about our research.",
        "What programming languages or technical skills do you have experience with?",
        "How do you approach solving complex problems you haven't encountered before?",
        "What is your availability for research work during the semester?",
        f"What do you know about the work we do in {lab_name}?"
    ]

def generate_mock_interview_feedback(transcript, question_text):
    """Generate mock interview feedback when AI providers are unavailable"""
    return """**Content Quality**
Your answer addressed the main points of the question and showed relevant knowledge. You demonstrated understanding of the topic.

**Communication Skills**
Your response was clear and well-structured. You spoke at an appropriate pace and used professional language.

**Enthusiasm & Interest**
You conveyed genuine interest in the research opportunity. Your passion for the field comes through in your response.

**Professionalism**
You maintained a professional tone throughout your answer and showed good preparation.

**Overall Impression**
Solid interview response that demonstrates your qualifications and genuine interest in the position.

**Actionable Tips:**
1. **Add specific examples**: Include concrete examples from your coursework or projects that relate to the question
2. **Connect to the lab's work**: Explicitly tie your answer back to the specific research being done in this lab
3. **Show initiative**: Mention any additional steps you've taken to learn about this field or prepare for research

*Note: This is demo feedback. Connect your AI provider for personalized analysis.*"""

if __name__ == '__main__':
    print("Starting Researchly…")
    print(f"Gemini RAG features: {'Enabled' if GEMINI_AVAILABLE else 'Disabled'}")
    print(f"Interview Practice features: {'Enabled' if (GEMINI_AVAILABLE or OPENAI_AVAILABLE) else 'Mock Mode'}")
    app.run(debug=True, port=8080)