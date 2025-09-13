# app.py
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import json, os, uuid
import re
from pypdf import PdfReader

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

        # Provider switch: prefer OpenAI if chosen and available; else Gemini
        if AI_PROVIDER == 'openai':
            if not OPENAI_AVAILABLE:
                return jsonify({'error': 'OpenAI provider not available. Install openai and set OPENAI_API_KEY.'}), 503
            recs = get_openai_rag_recommendations(
                student_data={**student_data, 'transcript_text': transcript_text, 'coursework': coursework},
                transcript_path=transcript_path,
                labs_data=labs_data
            )
        else:
            if not GEMINI_AVAILABLE:
                return jsonify({'error': 'Gemini provider not available. Install google-generativeai and set GEMINI_API_KEY.'}), 503
            recs = get_gemini_rag_recommendations(
                student_data={**student_data, 'transcript_text': transcript_text, 'coursework': coursework},
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

if __name__ == '__main__':
    print("Starting ResearchConnect…")
    print(f"Gemini RAG features: {'Enabled' if GEMINI_AVAILABLE else 'Disabled'}")
    app.run(debug=True, port=8080)