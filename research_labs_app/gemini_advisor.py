# gemini_advisor.py
import os, json, re, urllib.parse
from dotenv import load_dotenv

load_dotenv()

# pip install google-generativeai
import google.generativeai as genai

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set in environment.")
genai.configure(api_key=API_KEY)

EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+", re.IGNORECASE)
URL_RE   = re.compile(r"https?://\S+", re.IGNORECASE)

# ---------------- Email helpers ----------------
def domain_from_url(url: str) -> str:
    if not url: return ""
    try:
        return urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        return ""

def slugify_name_for_email(full_name: str) -> str:
    """Convert 'Dr. Jane Q. Doe' -> 'jane.doe'."""
    if not full_name: return ""
    name = re.sub(r"^(prof\.?|dr\.?)\s+", "", full_name.strip(), flags=re.I)
    parts = [p.lower() for p in re.split(r"[^\w]+", name) if p]
    if not parts: return ""
    if len(parts) > 1:
        return f"{parts[0]}.{parts[-1]}"
    return parts[0]

def guess_domain_from_school(school: str) -> str:
    s = (school or "").lower()
    if "ut dallas" in s: return "utdallas.edu"
    if "mit" in s: return "mit.edu"
    if "stanford" in s: return "stanford.edu"
    if "berkeley" in s: return "berkeley.edu"
    if "harvard" in s: return "harvard.edu"
    if "cmu" in s or "carnegie mellon" in s: return "cmu.edu"
    return "college.edu"

def infer_email(professor: str, url: str, school: str) -> str:
    local = slugify_name_for_email(professor)
    if not local: return ""
    dom = domain_from_url(url) or guess_domain_from_school(school)
    return f"{local}@{dom}" if dom else ""

# ---------------- Gemini RAG ----------------
def get_gemini_rag_recommendations(student_data, transcript_path, labs_data):
    """
    Returns a list[dict] of recommendations:
      {name, professor, professor_email, school, url, description, relevance_score, skills[], coursework[]}
    """
    try:
        # Compact labs context
        lines = []
        for lab in (labs_data or [])[:50]:
            lines.append(
                f"- name: {lab.get('name','')}\n"
                f"  professor: {lab.get('professor','')}\n"
                f"  professor_email: {lab.get('professor_email','')}\n"
                f"  school: {lab.get('school','')}\n"
                f"  url: {lab.get('url','')}\n"
                f"  description: {lab.get('description','')}"
            )
        labs_context = "\n".join(lines)

        transcript_text = (student_data.get('transcript_text') or '').strip()
        coursework_hint = student_data.get('coursework') or []

        # Prompt
        prompt = f"""
You are an expert academic advisor. Produce ONLY valid JSON with this shape:

{{
  "recommendations": [
    {{
      "name": "string",
      "professor": "string",
      "professor_email": "string",
      "school": "string",
      "url": "string",
      "description": "string",
      "relevance_score": 0,
      "skills": ["string"],
      "coursework": ["string"]
    }}
  ]
}}

Rules:
- Return 2–3 items.
- Always include "professor_email". If missing, infer "firstname.lastname@institution.edu".
- description must concisely include: why it matches, skills to highlight, and next steps.
- Use ONLY labs from the provided list (use exact names/professors).
- Use transcript/coursework to tailor the match and list specific classes/skills.

Student profile (JSON):
{json.dumps(student_data, ensure_ascii=False)}

Transcript text (if any):
{transcript_text[:4000]}

Coursework hints (if any): {json.dumps(coursework_hint, ensure_ascii=False)}

Available labs (summaries):
{labs_context}
""".strip()

        model = genai.GenerativeModel("gemini-1.5-pro")
        resp = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.35,
                "top_k": 1,
                "top_p": 1,
                "max_output_tokens": 1200,
            },
        )

        text = (resp.text or "").strip()
        recs = _extract_json_recs(text)
        if recs: return recs

        heur = _heuristic_parse(text)
        if heur: return heur

        return _fallback(student_data, labs_data)
    except Exception as e:
        print(f"[Gemini] Error: {e}")
        return _fallback(student_data, labs_data)

# ---------------- Parsing ----------------
def _extract_json_recs(text: str):
    if not text: return None
    try:
        data = json.loads(text)
        arr = data.get("recommendations")
        if isinstance(arr, list) and arr:
            return _normalize(arr)
    except Exception:
        pass
    try:
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e != -1 and e > s:
            data = json.loads(text[s:e+1])
            arr = data.get("recommendations")
            if isinstance(arr, list) and arr:
                return _normalize(arr)
    except Exception:
        pass
    return None

def _normalize(arr):
    out = []
    for r in arr:
        if not isinstance(r, dict): continue
        prof = (r.get("professor") or "").strip()
        url  = (r.get("url") or "#").strip()
        sch  = (r.get("school") or "").strip()
        desc = (r.get("description") or "").strip()
        email = (r.get("professor_email") or "").strip()
        skills = r.get("skills") or []
        coursework = r.get("coursework") or []

        if not email:
            m = EMAIL_RE.search(desc)
            if m:
                email = m.group(0)
        if not email:
            email = infer_email(prof, url, sch)

        out.append({
            "name": (r.get("name") or "Recommended Lab").strip(),
            "professor": prof,
            "professor_email": email,
            "school": sch,
            "url": url,
            "description": desc,
            "relevance_score": int(r.get("relevance_score") or 0),
            "skills": [str(s).strip() for s in skills if str(s).strip()],
            "coursework": [str(c).strip() for c in coursework if str(c).strip()],
        })
    return out

def _heuristic_parse(text: str):
    chunks = re.split(r"\n(?=\s*(?:\d+\. |#{2,3}\s))", text or "")
    items = []
    for ch in chunks:
        ch = ch.strip()
        if not ch: continue
        m = re.match(r"^(?:\d+\.\s*|#{2,3}\s*)(.+)$", ch)
        title = m.group(1).strip() if m else "Recommended Lab"
        prof = _find(ch, r"Professor[:\-]\s*([^\n]+)")
        school = _find(ch, r"School[:\-]\s*([^\n]+)")
        url = ""
        m_url = URL_RE.search(ch)
        if m_url: url = m_url.group(0)
        m_email = EMAIL_RE.search(ch)
        email = m_email.group(0) if m_email else infer_email(prof, url, school)
        items.append({
            "name": title,
            "professor": prof,
            "professor_email": email,
            "school": school,
            "url": url or "#",
            "description": ch,
            "relevance_score": 0,
            "skills": [],
            "coursework": [],
        })
        if len(items) >= 3: break
    return items or None

def _find(text, pat):
    m = re.search(pat, text, re.IGNORECASE)
    return m.group(1).strip() if m else ""

# ---------------- Fallback ----------------
def _fallback(student_data, labs_data):
    major = (student_data.get("academic", {}).get("major") or "").lower()
    interests = [str(i).lower() for i in (student_data.get("goals", {}).get("interests") or [])]
    scored = []
    for lab in labs_data or []:
        s = 0
        n = (lab.get("name") or "").lower()
        d = (lab.get("description") or "").lower()
        sch = (lab.get("school") or "").lower()
        if major and (major in n or major in d): s += 3
        for it in interests:
            if it and (it in n or it in d): s += 2
        if major and major in sch: s += 1
        if s > 0: scored.append((s, lab))
    scored.sort(key=lambda t: t[0], reverse=True)
    top = [lab for s, lab in scored[:3]]
    out = []
    for lab in top:
        prof = lab.get("professor", "")
        url  = lab.get("url", "#")
        sch  = lab.get("school", "")
        email = lab.get("professor_email") or infer_email(prof, url, sch)
        out.append({
            "name": lab.get("name", "Recommended Lab"),
            "professor": prof,
            "professor_email": email or "",
            "school": sch,
            "url": url or "#",
            "description": (lab.get("description", "") or "")[:400],
            "relevance_score": lab.get("relevance_score", 0),
            "skills": [],
            "coursework": [],
        })
    return out