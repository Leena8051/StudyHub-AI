import streamlit as st
import sqlite3
import hashlib
import os
import re
import json
from datetime import datetime, date, timedelta

# Optional file parsing libs (installed via pip)
try:
    from docx import Document
except Exception:
    Document = None

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

# Optional AI
try:
    import google.generativeai as genai
except Exception:
    genai = None

st.set_page_config(page_title="StudyHub", page_icon="🎓", layout="wide")

st.markdown("""
<style>
  /* App background */
  .stApp { background: #F5F6FA; }

  /* Sidebar like screenshot */
  section[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid #E9EDF5;
  }
  section[data-testid="stSidebar"] > div {
    padding-top: 18px;
  }

  /* Sidebar radio (navigation) - make it look like soft purple selected pill */
  div[role="radiogroup"] label {
    border-radius: 12px !important;
    padding: 10px 12px !important;
    margin: 6px 0 !important;
  }
  div[role="radiogroup"] label:has(input:checked) {
    background: #EFE9FF !important;   /* soft purple */
  }

  /* Cards */
  .sh-card {
    background: #FFFFFF;
    border: 1px solid #EEF1F7;
    border-radius: 18px;
    padding: 18px;
    box-shadow: 0 10px 24px rgba(16,24,40,0.06);
  }
  .sh-title {
    font-size: 38px;
    font-weight: 900;
    margin: 0 0 14px 0;
    color: #111827;
  }

  /* Stat cards */
  .stat {
    border-radius: 18px;
    padding: 18px;
    color: white;
    height: 120px;
    display:flex;
    flex-direction:column;
    justify-content:space-between;
    position: relative;
    overflow:hidden;
  }
  .stat .big { font-size: 40px; font-weight: 900; line-height: 1; }
  .stat .lbl { font-size: 14px; opacity: .95; font-weight: 700; }

  /* Small icon pill */
  .iconpill{
    width:42px;height:42px;border-radius:14px;
    background: rgba(255,255,255,0.18);
    display:flex;align-items:center;justify-content:center;
    font-size:18px;
  }

  /* Top-right buttons */
  .top-actions { display:flex; gap:12px; justify-content:flex-end; }
  .btn-soft {
    padding: 10px 14px;
    border-radius: 12px;
    background: #FFFFFF;
    border: 1px solid #E6EAF2;
    font-weight: 800;
    color: #111827;
  }
  .btn-primary {
    padding: 10px 14px;
    border-radius: 12px;
    background: #5B5BEA;
    border: 1px solid #5B5BEA;
    font-weight: 800;
    color: white;
  }

  /* Progress ring placeholder */
  .ring{
    width:72px;height:72px;border-radius:999px;
    border: 10px solid #EEF1F7;
    display:flex;align-items:center;justify-content:center;
    font-weight:900;color:#111827;
  }

  /* AI buddy input row */
  .ai-row{
    display:flex; gap:10px; align-items:center;
    padding-top: 10px;
  }
  .ai-input{
    flex:1;
    border: 1px solid #E6EAF2;
    border-radius: 12px;
    padding: 10px 12px;
    background:#FFFFFF;
  }
  .ai-send{
    border-radius:12px;
    padding: 10px 18px;
    background:#5B5BEA;
    color:#fff;
    border: 1px solid #5B5BEA;
    font-weight:900;
  }
</style>
""", unsafe_allow_html=True)


DB_PATH = "studyhub.db"

# =========================
# Database (persistent)
# =========================
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        pass_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS courses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        course_name TEXT NOT NULL,
        course_code TEXT,
        difficulty TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        course_id INTEGER,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        due_date TEXT NOT NULL,
        notes TEXT,
        created_from TEXT NOT NULL,  -- "manual" or "syllabus_ai"
        done INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE SET NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_settings(
        user_id INTEGER PRIMARY KEY,
        content_type TEXT NOT NULL DEFAULT 'Mixed Content',
        study_method TEXT NOT NULL DEFAULT 'Pomodoro Technique',
        work_minutes INTEGER NOT NULL DEFAULT 25,
        break_minutes INTEGER NOT NULL DEFAULT 5,
        daily_goal_hours INTEGER NOT NULL DEFAULT 4,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)


    conn.commit()
    conn.close()


def get_user_settings(user_id: int):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT content_type, study_method, work_minutes, break_minutes, daily_goal_hours
        FROM user_settings WHERE user_id=?
    """, (user_id,))
    row = cur.fetchone()

    if not row:
        # create defaults
        cur.execute("""
            INSERT INTO user_settings(user_id, content_type, study_method, work_minutes, break_minutes, daily_goal_hours, updated_at)
            VALUES(?,?,?,?,?,?,?)
        """, (user_id, "Mixed Content", "Pomodoro Technique", 25, 5, 4, datetime.now().isoformat()))
        conn.commit()
        row = ("Mixed Content", "Pomodoro Technique", 25, 5, 4)

    conn.close()
    return {
        "content_type": row[0],
        "study_method": row[1],
        "work_minutes": int(row[2]),
        "break_minutes": int(row[3]),
        "daily_goal_hours": int(row[4]),
    }

def save_user_settings(user_id: int, content_type: str, study_method: str, work_minutes: int, break_minutes: int, daily_goal_hours: int):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO user_settings(user_id, content_type, study_method, work_minutes, break_minutes, daily_goal_hours, updated_at)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
            content_type=excluded.content_type,
            study_method=excluded.study_method,
            work_minutes=excluded.work_minutes,
            break_minutes=excluded.break_minutes,
            daily_goal_hours=excluded.daily_goal_hours,
            updated_at=excluded.updated_at
    """, (user_id, content_type, study_method, work_minutes, break_minutes, daily_goal_hours, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def hash_password(pw: str) -> str:
    # Simple salted hash (good enough for demo). For production use bcrypt/argon2.
    salt = "studyhub_salt_v1"
    return hashlib.sha256((salt + pw).encode("utf-8")).hexdigest()

def create_user(name, email, password):
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users(name,email,pass_hash,created_at) VALUES(?,?,?,?)",
            (name, email.lower().strip(), hash_password(password), datetime.now().isoformat())
        )
        conn.commit()
        return True, "Account created. Please sign in."
    except sqlite3.IntegrityError:
        return False, "Email already exists."
    finally:
        conn.close()

def authenticate(email, password):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id,name,email,pass_hash FROM users WHERE email=?", (email.lower().strip(),))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    uid, name, em, pw_hash = row
    if hash_password(password) == pw_hash:
        return {"id": uid, "name": name, "email": em}
    return None

def add_course(user_id, name, code, difficulty):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO courses(user_id,course_name,course_code,difficulty,created_at)
        VALUES(?,?,?,?,?)
    """, (user_id, name, code, difficulty, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def list_courses(user_id):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id, course_name, course_code, difficulty FROM courses WHERE user_id=? ORDER BY id DESC", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def add_task(user_id, course_id, title, category, due_date_iso, notes="", created_from="manual"):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tasks(user_id,course_id,title,category,due_date,notes,created_from,done,created_at)
        VALUES(?,?,?,?,?,?,?,?,?)
    """, (user_id, course_id, title, category, due_date_iso, notes, created_from, 0, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def list_tasks(user_id, from_date=None, to_date=None):
    conn = db()
    cur = conn.cursor()
    q = "SELECT id, course_id, title, category, due_date, notes, done FROM tasks WHERE user_id=?"
    params = [user_id]

    if from_date:
        q += " AND date(due_date) >= date(?)"
        params.append(from_date.isoformat())
    if to_date:
        q += " AND date(due_date) <= date(?)"
        params.append(to_date.isoformat())

    q += " ORDER BY date(due_date) ASC"
    cur.execute(q, tuple(params))
    rows = cur.fetchall()
    conn.close()
    return rows

def mark_done(task_id, done):
    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET done=? WHERE id=?", (1 if done else 0, task_id))
    conn.commit()
    conn.close()

# =========================
# File → text
# =========================
def read_uploaded_file_to_text(uploaded_file):
    if not uploaded_file:
        return ""

    name = uploaded_file.name.lower()
    data = uploaded_file.read()

    # TXT
    if name.endswith(".txt"):
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return data.decode(errors="ignore")

    # PDF
    if name.endswith(".pdf"):
        with open("_tmp.pdf", "wb") as f:
            f.write(data)
        reader = PdfReader("_tmp.pdf")
        text = []
        for p in reader.pages:
            text.append(p.extract_text() or "")
        return "\n".join(text)

    # DOCX
    if name.endswith(".docx"):
        with open("_tmp.docx", "wb") as f:
            f.write(data)
        doc = Document("_tmp.docx")
        return "\n".join([p.text for p in doc.paragraphs])

    # fallback
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""

# =========================
# AI extraction (Gemini)
# =========================
TASK_SCHEMA = {
    "tasks": [
        {
            "title": "string",
            "category": "assignment|quiz|exam|project|reading|other",
            "due_date": "YYYY-MM-DD",
            "notes": "string"
        }
    ]
}

def parse_tasks_with_gemini(syllabus_text, gemini_key):
    """
    Returns list of dict tasks.
    """
    if not genai or not gemini_key:
        return None, "AI not available (missing library or key)."

    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
You are an assistant that extracts all tasks and deadlines from a course syllabus.
Return ONLY valid JSON that matches this schema exactly:
{json.dumps(TASK_SCHEMA, indent=2)}

Rules:
- Find every graded item and deadline (assignments, quizzes, exams, projects, labs, readings if deadlines exist).
- Convert dates to ISO format YYYY-MM-DD. If a date is unclear, omit that item.
- Categorize into: assignment, quiz, exam, project, reading, other
- Keep titles short and clear.
- Add notes if useful (e.g., "Chapter 3", "Submit on LMS", "In-class").
Syllabus:
\"\"\"{syllabus_text[:18000]}\"\"\"  # (limit to avoid token overload)
"""

    try:
        resp = model.generate_content(prompt)
        text = resp.text.strip()
        # Sometimes model wraps JSON in ```json ... ```
        text = re.sub(r"^```json\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
        obj = json.loads(text)
        tasks = obj.get("tasks", [])
        # validate minimal fields
        cleaned = []
        for t in tasks:
            if not t.get("title") or not t.get("due_date") or not t.get("category"):
                continue
            # basic date validation
            try:
                datetime.strptime(t["due_date"], "%Y-%m-%d")
            except Exception:
                continue
            cleaned.append({
                "title": str(t["title"]).strip(),
                "category": str(t["category"]).strip().lower(),
                "due_date": t["due_date"],
                "notes": str(t.get("notes","")).strip()
            })
        return cleaned, None
    except Exception as e:
        return None, f"Gemini parse failed: {e}"

# =========================
# Fallback extraction (no AI)
# =========================
def parse_tasks_fallback(syllabus_text):
    """
    Very simple extraction:
    looks for lines containing keywords and dates like Feb 20, 2026 OR 2026-02-20.
    """
    tasks = []

    # ISO date
    iso_pat = r"\b(20\d{2})-(\d{2})-(\d{2})\b"
    # Month name date (simple)
    mon_pat = r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),\s*(20\d{2})\b"

    keywords = [
        ("assignment", ["assignment", "hw", "homework", "problem set"]),
        ("quiz", ["quiz"]),
        ("exam", ["exam", "midterm", "final"]),
        ("project", ["project"]),
        ("reading", ["reading"]),
    ]

    lines = [l.strip() for l in syllabus_text.splitlines() if l.strip()]
    for line in lines:
        low = line.lower()

        # find date
        due = None
        m1 = re.search(iso_pat, line)
        if m1:
            due = f"{m1.group(1)}-{m1.group(2)}-{m1.group(3)}"
        else:
            m2 = re.search(mon_pat, line, flags=re.IGNORECASE)
            if m2:
                mon_map = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
                mm = mon_map[m2.group(1)[:3].lower()]
                dd = int(m2.group(2))
                yy = int(m2.group(3))
                due = f"{yy:04d}-{mm:02d}-{dd:02d}"

        if not due:
            continue

        category = "other"
        for cat, words in keywords:
            if any(w in low for w in words):
                category = cat
                break

        # title: keep the line but shorten
        title = line
        title = re.sub(r"\s+", " ", title)
        if len(title) > 80:
            title = title[:77] + "..."

        tasks.append({"title": title, "category": category, "due_date": due, "notes": ""})

    # Deduplicate
    uniq = {}
    for t in tasks:
        key = (t["title"], t["due_date"])
        uniq[key] = t
    return list(uniq.values())

# =========================
# Calendar helpers
# =========================
def month_range(d: date):
    first = d.replace(day=1)
    # next month
    if first.month == 12:
        nxt = first.replace(year=first.year+1, month=1, day=1)
    else:
        nxt = first.replace(month=first.month+1, day=1)
    last = nxt - timedelta(days=1)
    return first, last

def to_ics(tasks_rows):
    """
    tasks_rows: list rows from DB: (id, course_id, title, category, due_date, notes, done)
    """
    lines = []
    lines.append("BEGIN:VCALENDAR")
    lines.append("VERSION:2.0")
    lines.append("PRODID:-//StudyHub//Calendar//EN")

    for row in tasks_rows:
        _, _, title, category, due_date, notes, done = row
        dt = due_date.replace("-", "")
        uid = f"{hashlib.md5((title+due_date).encode()).hexdigest()}@studyhub"
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        lines.append(f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}")
        lines.append(f"DTSTART;VALUE=DATE:{dt}")
        lines.append(f"SUMMARY:{title} [{category}]")
        if notes:
            safe = notes.replace("\n", "\\n")
            lines.append(f"DESCRIPTION:{safe}")
        if done:
            lines.append("STATUS:COMPLETED")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\n".join(lines)

# =========================
# UI: Auth
# =========================
init_db()

def ensure_login():
    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user:
        return True

    st.title("🎓 StudyHub — Sign In")

    tab1, tab2 = st.tabs(["Sign In", "Create Account"])

    with tab1:
        email = st.text_input("Email", placeholder="you@example.com")
        pw = st.text_input("Password", type="password", placeholder="••••••••")
        if st.button("Sign In", use_container_width=True):
            u = authenticate(email, pw)
            if u:
                st.session_state.user = u
                st.success(f"Welcome, {u['name']}!")
                st.rerun()
            else:
                st.error("Invalid email or password.")

    with tab2:
        name = st.text_input("Full Name", placeholder="Your name")
        email2 = st.text_input("Email address", placeholder="you@example.com")
        pw2 = st.text_input("Password", type="password")
        pw3 = st.text_input("Confirm Password", type="password")
        if st.button("Create Account", use_container_width=True):
            if not name.strip() or not email2.strip() or not pw2:
                st.error("Fill all fields.")
            elif pw2 != pw3:
                st.error("Passwords do not match.")
            else:
                ok, msg = create_user(name, email2, pw2)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    st.stop()

ensure_login()
user = st.session_state.user

# =========================
# Sidebar navigation + Gemini key placeholder
# =========================
with st.sidebar:
    st.markdown("""
    <div style="display:flex; gap:10px; align-items:center; padding:6px 2px 14px 2px;">
      <div style="width:44px;height:44px;border-radius:14px;background:linear-gradient(135deg,#6D28D9,#5B5BEA);
                  display:flex;align-items:center;justify-content:center;color:white;font-weight:900;">🎓</div>
      <div>
        <div style="font-weight:900;font-size:20px;line-height:1;">StudyHub</div>
        <div style="color:#6B7280;font-size:13px;margin-top:2px;">AI Study Platform</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        ["Dashboard", "Courses", "Calendar","AI Buddy"],
        index=0,
        label_visibility="collapsed"
    )

    st.markdown("<hr style='border:none;height:1px;background:#EEF1F7;margin:16px 0;'>", unsafe_allow_html=True)

    st.markdown("<div style='font-weight:900;margin-bottom:8px;'>Gemini API Key:</div>", unsafe_allow_html=True)
    gemini_key = st.text_input(
        "Gemini API Key",
        value=st.session_state.get("gemini_key",""),
        placeholder="PASTE_YOUR_GEMINI_API_KEY_HERE",
        type="password",
        label_visibility="collapsed"
    )
    st.session_state.gemini_key = gemini_key

    st.markdown("<div style='height:45vh;'></div>", unsafe_allow_html=True)

    st.markdown("""
    <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 6px;">
      <div style="font-weight:900;font-size:18px;">Notifications</div>
      <div style="background:#FF0000;color:white;font-weight:900;border-radius:999px;padding:3px 10px;">0</div>
    </div>
    <div style="padding:10px 6px;font-weight:900;font-size:18px;">Settings</div>
    """, unsafe_allow_html=True)

# =========================
# Dashboard
# =========================
if page == "Dashboard":
    # --- data ---
    courses = list_courses(user["id"])
    all_tasks = list_tasks(user["id"])
    active_courses = len(courses)
    study_hours = 0.0
    tasks_due = sum(1 for t in all_tasks if t[6] == 0)
    streak_days = 0

    # --- header row like screenshot ---
    header_left, header_right = st.columns([0.72, 0.28])
    with header_left:
        st.markdown(f"<div class='sh-title'>Welcome back, {user['name']}! 👋</div>", unsafe_allow_html=True)
    with header_right:
        st.markdown("<div class='top-actions'>"
                    "<button class='btn-soft'>+ Add Task</button>"
                    "<button class='btn-primary'>+ Add Course</button>"
                    "</div>", unsafe_allow_html=True)

    st.write("")

    # --- 4 colored stat cards ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="stat" style="background:linear-gradient(135deg,#4F6BFF,#6D28D9);">
          <div class="iconpill">📘</div>
          <div>
            <div class="big">{active_courses}</div>
            <div class="lbl">Active Courses</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="stat" style="background:linear-gradient(135deg,#7C3AED,#A855F7);">
          <div class="iconpill">🕒</div>
          <div>
            <div class="big">{study_hours:.1f}h</div>
            <div class="lbl">Study Hours</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="stat" style="background:linear-gradient(135deg,#F97316,#FB923C);">
          <div class="iconpill">🎯</div>
          <div>
            <div class="big">{tasks_due}</div>
            <div class="lbl">Tasks Due</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="stat" style="background:linear-gradient(135deg,#F43F5E,#FB7185);">
          <div class="iconpill">🔥</div>
          <div>
            <div class="big">{streak_days} days</div>
            <div class="lbl">Study Streak</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # --- second row 3 cards ---
    r1, r2, r3 = st.columns([0.36, 0.32, 0.32])

    with r1:
        st.markdown("""
        <div class="sh-card">
          <div style="font-weight:900;font-size:18px;margin-bottom:6px;">How's your energy today?</div>
          <div style="color:#6B7280;font-size:13px;margin-bottom:12px;">AI will adjust tasks based on your energy level.</div>
        """, unsafe_allow_html=True)
        energy = st.radio("energy", ["1","2","3","4","5"], horizontal=True, label_visibility="collapsed", index=4)
        st.markdown("<div style='color:#10B981;font-weight:900;margin-top:10px;'>Tackle hard topics</div></div>", unsafe_allow_html=True)

    with r2:
        st.markdown("""
        <div class="sh-card" style="display:flex;justify-content:space-between;align-items:center;">
          <div>
            <div style="font-weight:900;font-size:18px;margin-bottom:6px;">Today's Progress</div>
            <div style="color:#6B7280;font-size:13px;">Tasks completed</div>
            <div style="font-size:28px;font-weight:900;margin-top:10px;">0%</div>
            <div style="color:#10B981;font-weight:900;margin-top:10px;">↗ Keep going!</div>
          </div>
          <div class="ring">0%</div>
        </div>
        """, unsafe_allow_html=True)

    with r3:
        st.markdown("""
        <div class="sh-card">
          <div style="font-weight:900;font-size:18px;margin-bottom:6px;">This Week</div>
          <div style="color:#6B7280;font-size:13px;"> </div>
          <div style="height:58px;"></div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # --- bottom row: Upcoming tasks + AI buddy ---
    b1, b2 = st.columns([0.58, 0.42])

    with b1:
        st.markdown("""
        <div class="sh-card">
          <div style="font-weight:900;font-size:18px;">Upcoming Tasks</div>
          <div style="height:12px;"></div>
        """, unsafe_allow_html=True)

        upcoming = list_tasks(user["id"], from_date=date.today(), to_date=date.today()+timedelta(days=21))
        if not upcoming:
            st.info("No upcoming tasks yet.")
        else:
            for row in upcoming[:6]:
                task_id, course_id, title, category, due_date, notes, done = row
                st.write(f"• **{title}** — {category} — {due_date}")

        st.markdown("</div>", unsafe_allow_html=True)

        st.write("")

        st.markdown("""
        <div class="sh-card">
          <div style="display:flex;gap:12px;align-items:center;justify-content:space-between;">
            <div>
              <div style="font-weight:900;font-size:18px;">AI Study Plan</div>
              <div style="color:#6B7280;font-size:13px;margin-top:4px;">Plan adapts to difficulty, deadlines, progress, and your energy level.</div>
            </div>
          </div>
        """, unsafe_allow_html=True)

        cA, cB, cC, cD = st.columns([0.22,0.26,0.26,0.26])
        with cA:
            st.selectbox("freq", ["Daily","Weekly"], label_visibility="collapsed")
        with cB:
            st.selectbox("mode", ["Summaries","Flashcards","Mixed"], label_visibility="collapsed")
        with cC:
            st.selectbox("method", ["Pomodoro","Deep Work"], label_visibility="collapsed")
        with cD:
            st.button("Generate", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

    with b2:
        st.write("")

        st.markdown("""
        <div class="sh-card">
          <div style="font-weight:900;font-size:18px;">Calendar (Next 30 Days)</div>
          <div style="color:#6B7280;font-size:13px;margin-top:6px;">Assignments • Quizzes • Exams • Projects</div>
          <div style="height:12px;"></div>
        """, unsafe_allow_html=True)

        rows = list_tasks(user["id"], from_date=date.today(), to_date=date.today()+timedelta(days=30))
        if not rows:
            st.info("No tasks yet. Upload a syllabus in Courses to auto-fill.")
        else:
            # filter
            cats = ["all","assignment","quiz","exam","project","reading","other"]
            chosen = st.selectbox("Filter", cats, index=0, label_visibility="collapsed")

            for r in rows[:10]:
                task_id, course_id, title, category, due_date, notes, done = r
                if chosen != "all" and category != chosen:
                    continue

                badge = {
                    "assignment":"📝",
                    "quiz":"✅",
                    "exam":"🧪",
                    "project":"📦",
                    "reading":"📖",
                    "other":"📌"
                }.get(category, "📌")

                st.write(f"{badge} **{title}** — `{category}` — **{due_date}**")

        st.markdown("</div>", unsafe_allow_html=True)


# =========================
# Courses + Upload syllabus → AI extraction → tasks saved
# =========================
elif page == "Courses":
    st.title("📚 Courses")

    st.subheader("Add Course")
    c1, c2, c3 = st.columns([0.45, 0.25, 0.30])
    with c1:
        course_name = st.text_input("Course name", placeholder="e.g., CIS321 Database")
    with c2:
        course_code = st.text_input("Course code", placeholder="e.g., CIS321")
    with c3:
        difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard", "very hard"], index=1)

    if st.button("➕ Create Course", use_container_width=True):
        if not course_name.strip():
            st.error("Course name is required.")
        else:
            add_course(user["id"], course_name.strip(), course_code.strip(), difficulty)
            st.success("Course created.")
            st.rerun()

    st.divider()

    courses = list_courses(user["id"])
    if not courses:
        st.info("No courses yet. Create one first.")
        st.stop()

    # Choose course for syllabus upload
    st.subheader("Upload Syllabus (AI will extract tasks + deadlines)")
    course_map = {f"{name} ({code})": cid for (cid, name, code, diff) in courses}
    selected_label = st.selectbox("Choose course", list(course_map.keys()))
    selected_course_id = course_map[selected_label]

    uploaded = st.file_uploader("Upload syllabus file (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])

    colA, colB = st.columns([0.7, 0.3])
    with colA:
        st.caption("The AI reads the syllabus and extracts: task title, category (assignment/quiz/exam/etc), due date.")
    with colB:
        run_ai = st.button("✨ Extract & Add to Calendar", use_container_width=True)

    if run_ai:
        if not uploaded:
            st.error("Please upload a syllabus file first.")
        else:
            text = read_uploaded_file_to_text(uploaded)
            if not text.strip():
                st.error("Could not read text from this file.")
            else:
                with st.spinner("Reading syllabus and extracting tasks..."):
                    tasks, err = parse_tasks_with_gemini(text, st.session_state.gemini_key)
                    if tasks is None:
                        # fallback
                        tasks = parse_tasks_fallback(text)
                        st.warning(f"AI not used. Using fallback extractor. Reason: {err}")

                if not tasks:
                    st.error("No tasks with valid due dates were found.")
                else:
                    # preview
                    st.success(f"Found {len(tasks)} task(s). Preview below:")
                    st.json(tasks[:12])

                    # save
                    saved = 0
                    for t in tasks:
                        add_task(
                            user_id=user["id"],
                            course_id=selected_course_id,
                            title=t["title"],
                            category=t["category"],
                            due_date_iso=t["due_date"],
                            notes=t.get("notes",""),
                            created_from="syllabus_ai"
                        )
                        saved += 1

                    st.success(f"✅ Saved {saved} task(s) to your calendar.")
                    st.info("Go to the Calendar tab to view everything neatly organized.")

    st.divider()
    st.subheader("Your Courses")
    for (cid, name, code, diff) in courses:
        st.markdown(f"**{name}**  — `{code}`  •  *{diff}*")

# =========================
# Calendar view + ICS export
# =========================
elif page == "Calendar":
    st.title("🗓️ Calendar")

    view = st.selectbox("View", ["This month", "Next 30 days", "All tasks"], index=0)

    if view == "This month":
        first, last = month_range(date.today())
        rows = list_tasks(user["id"], from_date=first, to_date=last)
        st.caption(f"{first.isoformat()} → {last.isoformat()}")

    elif view == "Next 30 days":
        rows = list_tasks(user["id"], from_date=date.today(), to_date=date.today() + timedelta(days=30))
        st.caption(f"{date.today().isoformat()} → {(date.today()+timedelta(days=30)).isoformat()}")

    else:
        rows = list_tasks(user["id"])

    if not rows:
        st.info("No tasks scheduled yet. Upload a syllabus in Courses to auto-fill your calendar.")
    else:
        # Group by date
        grouped = {}
        for r in rows:
            due = r[4]
            grouped.setdefault(due, []).append(r)

        # Show day blocks
        for due_date, items in grouped.items():
            with st.container():
                st.markdown(f"### {due_date}")
                for row in items:
                    task_id, course_id, title, category, due_date, notes, done = row
                    c = st.columns([0.08, 0.55, 0.16, 0.21])
                    with c[0]:
                        checked = st.checkbox("Done", value=bool(done), key=f"cal_done_{task_id}", label_visibility="collapsed")
                        if checked != bool(done):
                            mark_done(task_id, checked)
                            st.rerun()
                    with c[1]:
                        st.write(f"**{title}**")
                        if notes:
                            st.caption(notes)
                    with c[2]:
                        st.write(category.capitalize())
                    with c[3]:
                        st.write("✅ Done" if done else "⏳ Pending")

        st.divider()
        st.subheader("Export to Calendar (.ics)")

        ics_text = to_ics(rows)
        st.download_button(
            label="⬇️ Download ICS (import into Apple/Google Calendar)",
            data=ics_text.encode("utf-8"),
            file_name="studyhub_calendar.ics",
            mime="text/calendar",
            use_container_width=True
        )

elif page == "Settings":
    # ===== Exact-ish Theme Colors =====
    PRIMARY = "#4F46E5"       # button purple/blue
    PRIMARY_SOFT = "#EEF2FF"  # soft purple background
    TEXT_MUTED = "#6B7280"
    BORDER = "#E5E7EB"
    BG = "#F5F6FA"

    st.markdown(f"""
    <style>
      .stApp {{ background:{BG}; }}
      section[data-testid="stSidebar"] {{
        background: white;
        border-right: 1px solid {BORDER};
      }}

      /* Card */
      .card {{
        background: white;
        border: 1px solid {BORDER};
        border-radius: 16px;
        padding: 18px 18px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.04);
        margin-bottom: 18px;
      }}

      .title {{
        font-size: 44px;
        font-weight: 800;
        margin: 0;
        line-height: 1.05;
      }}
      .subtitle {{
        color: {TEXT_MUTED};
        font-size: 16px;
        margin-top: 6px;
        margin-bottom: 18px;
      }}

      .card-h {{
        display:flex;
        align-items:center;
        gap:10px;
        font-weight:800;
        font-size: 18px;
        margin-bottom: 10px;
      }}
      .muted {{ color:{TEXT_MUTED}; font-size: 13px; margin-top:-6px; }}

      /* Avatar circle */
      .avatar {{
        width: 56px;
        height: 56px;
        border-radius: 999px;
        background: linear-gradient(135deg, #6D28D9, {PRIMARY});
        display:flex;
        align-items:center;
        justify-content:center;
        color:white;
        font-weight:900;
        font-size: 22px;
      }}

      /* Streamlit widgets spacing */
      .block-container {{ padding-top: 22px; }}
      div[data-baseweb="select"] > div {{
        border-radius: 12px !important;
      }}
      .stSlider > div {{
        padding-top: 6px;
      }}

      /* Make primary button look like screenshot */
      .stButton > button[kind="primary"] {{
        background: {PRIMARY} !important;
        border: 1px solid {PRIMARY} !important;
        border-radius: 12px !important;
        height: 46px;
        font-weight: 700;
      }}
      .stButton > button[kind="secondary"] {{
        border-radius: 12px !important;
        height: 46px;
        font-weight: 700;
      }}
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown('<p class="title">Settings</p>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Customize your study experience</div>', unsafe_allow_html=True)

elif page == "AI Buddy":
    st.title("🤖 AI Buddy — Paste Syllabus")

    courses = list_courses(user["id"])
    if not courses:
        st.info("Create a course first, then paste syllabus here.")
        st.stop()

    course_map = {f"{name} ({code})": cid for (cid, name, code, diff) in courses}
    selected_label = st.selectbox("Choose course", list(course_map.keys()))
    selected_course_id = course_map[selected_label]

    syllabus_text = st.text_area(
        "Paste syllabus text",
        height=260,
        placeholder="Paste the full syllabus text here... (assignments, quizzes, exams, deadlines, etc.)"
    )

    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.caption("AI will extract tasks + deadlines and categorize them.")
    with col2:
        run = st.button("✨ Extract & Add", use_container_width=True)

    if run:
        if not syllabus_text.strip():
            st.error("Paste the syllabus text first.")
        else:
            with st.spinner("Extracting tasks from syllabus..."):
                tasks, err = parse_tasks_with_gemini(syllabus_text, st.session_state.get("gemini_key",""))
                if tasks is None:
                    tasks = parse_tasks_fallback(syllabus_text)
                    st.warning(f"AI not used. Using fallback. Reason: {err}")

            if not tasks:
                st.error("No tasks with valid due dates were found.")
            else:
                st.success(f"Found {len(tasks)} task(s). Preview:")
                st.json(tasks[:20])

                if st.button("✅ Confirm & Save Tasks", use_container_width=True):
                    saved = 0
                    for t in tasks:
                        add_task(
                            user_id=user["id"],
                            course_id=selected_course_id,
                            title=t["title"],
                            category=t["category"],
                            due_date_iso=t["due_date"],
                            notes=t.get("notes",""),
                            created_from="syllabus_ai"
                        )
                        saved += 1

                    st.success(f"Saved {saved} task(s) to your calendar ✅")
                    st.info("Go to Calendar tab to view everything organized.")
                    st.rerun()


    # Load current settings
    s = get_user_settings(user["id"])

    # ===== Profile Card =====
    initials = (user["name"].strip()[:1] or "U").upper()
    st.markdown(f"""
      <div class="card">
        <div class="card-h">👤&nbsp; Profile</div>
        <div class="muted">Your account information</div>
        <div style="display:flex; gap:14px; align-items:center; margin-top:14px;">
          <div class="avatar">{initials}</div>
          <div>
            <div style="font-weight:800; font-size:16px;">{user["name"]}</div>
            <div style="color:{TEXT_MUTED}; font-size:13px;">{user["email"]}</div>
          </div>
        </div>
      </div>
    """, unsafe_allow_html=True)

    # ===== Preferences Card =====
    st.markdown(f"""
      <div class="card">
        <div class="card-h">📘&nbsp; Study Preferences</div>
        <div class="muted">How you prefer to study</div>
      </div>
    """, unsafe_allow_html=True)

    # Put widgets inside the same visual area
    pref_col = st.container()
    with pref_col:
        content_type = st.selectbox(
            "Preferred Content Type",
            ["Mixed Content", "Summaries", "Videos", "Images/Diagrams"],
            index=["Mixed Content", "Summaries", "Videos", "Images/Diagrams"].index(s["content_type"]) if s["content_type"] in ["Mixed Content", "Summaries", "Videos", "Images/Diagrams"] else 0
        )
        st.caption("AI will prioritize this content type in recommendations")

        study_method = st.selectbox(
            "Preferred Study Method",
            ["Pomodoro Technique", "Deep Work", "Spaced Review", "Active Recall"],
            index=["Pomodoro Technique", "Deep Work", "Spaced Review", "Active Recall"].index(s["study_method"]) if s["study_method"] in ["Pomodoro Technique", "Deep Work", "Spaced Review", "Active Recall"] else 0
        )

    # ===== Timer Settings Card =====
    st.markdown(f"""
      <div class="card">
        <div class="card-h">🕒&nbsp; Timer Settings</div>
        <div class="muted">Customize your study timer</div>
      </div>
    """, unsafe_allow_html=True)

    work_minutes = st.slider("Work Duration", 10, 120, int(s["work_minutes"]), step=5)
    st.caption(f"{work_minutes} min")

    break_minutes = st.slider("Break Duration", 5, 60, int(s["break_minutes"]), step=5)
    st.caption(f"{break_minutes} min")

    # ===== Daily Goals Card =====
    st.markdown(f"""
      <div class="card">
        <div class="card-h">🎯&nbsp; Daily Goals</div>
        <div class="muted">Set your study targets</div>
      </div>
    """, unsafe_allow_html=True)

    daily_goal_hours = st.slider("Daily Study Goal", 1, 12, int(s["daily_goal_hours"]), step=1)
    st.caption(f"{daily_goal_hours} hours")

    # ===== Bottom Buttons =====
    left, right = st.columns([0.78, 0.22])
    with left:
        if st.button("💾  Save Settings", type="primary", use_container_width=True):
            save_user_settings(
                user["id"],
                content_type=content_type,
                study_method=study_method,
                work_minutes=work_minutes,
                break_minutes=break_minutes,
                daily_goal_hours=daily_goal_hours
            )
            st.success("Saved ✅")

    with right:
        if st.button("Sign Out", type="secondary", use_container_width=True):
            st.session_state.user = None
            st.rerun()
