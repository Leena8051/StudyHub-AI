/* =========================================================
   JAVASCRIPT LOGIC
   ========================================================= */

// --- 1. STATE & DATA ---
let courseList = [
    { id: 1, name: "Introduction to Computer Science", code: "CS101", difficulty: "medium", color: "blue", stats: "0 tasks • 0.0h studied" },
    { id: 2, name: "Calculus I", code: "MATH201", difficulty: "hard", color: "red", stats: "0 tasks • 0.0h studied" },
    { id: 3, name: "English Composition", code: "ENG102", difficulty: "easy", color: "green", stats: "0 tasks • 0.0h studied" },
    { id: 4, name: "Physics I", code: "PHY101", difficulty: "very hard", color: "purple", stats: "0 tasks • 0.0h studied" }
];
let taskList = [];
let aiPlan = [];
let userEnergy = 5;
let fileContextContent = "";
// YOUR API KEY HERE
const API_KEY = "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";

// --- 2. INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById("currentDate").innerText = new Date().toLocaleDateString('en-US', options);
    renderWeek();
    renderCourses();
    updateStats();
    setupFileUpload();
});

// --- 3. NAVIGATION ---
function showPage(pageId, element) {
    document.querySelectorAll('.page-section').forEach(el => el.classList.remove('active'));
    document.getElementById(pageId).classList.add('active');
    if(element) {
        document.querySelectorAll('.menu-item').forEach(el => el.classList.remove('active'));
        element.classList.add('active');
    }
}

function openCourseDetails(code) {
    document.querySelectorAll('.page-section').forEach(el => el.classList.remove('active'));
    if(code.startsWith("CS")) document.getElementById('csDetailsPage').classList.add('active');
    else if(code.startsWith("MATH")) document.getElementById('calcDetailsPage').classList.add('active');
    else if(code.startsWith("ENG")) document.getElementById('engDetailsPage').classList.add('active');
}

function openModal(id) { 
    if(id === 'taskModal') populateCourseSelect();
    document.getElementById(id).style.display = 'flex'; 
}
function closeModal(id) { document.getElementById(id).style.display = 'none'; }

function populateCourseSelect() {
    const sel = document.getElementById('taskCourse');
    sel.innerHTML = courseList.map(c => `<option value="${c.name}">${c.name}</option>`).join('');
}

// --- 4. RENDER FUNCTIONS ---
function renderWeek() {
    const days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
    const container = document.getElementById('weekCalendar');
    let html = '';
    let todayIndex = new Date().getDay() - 1; if(todayIndex < 0) todayIndex = 6; 
    let todayDate = new Date().getDate();
    days.forEach((d, i) => {
        let num = todayDate - todayIndex + i; 
        let active = (i === todayIndex) ? 'active' : ''; 
        html += `<div class="day-col ${active}"><span class="day-name">${d}</span><div class="day-num">${num > 0 ? num : 1}</div><div class="day-dot"></div></div>`;
    });
    container.innerHTML = html;
}

function renderCourses() {
    const html = courseList.map(c => {
        let diffColorClass = (c.difficulty === "easy") ? "tag-easy" : ((c.difficulty === "medium") ? "tag-medium" : "tag-hard");
        let colorClass = (c.color === "blue") ? "cc-blue" : ((c.color === "red") ? "cc-red" : ((c.color === "green") ? "cc-green" : "cc-purple"));
        return `
            <div class="course-card-clone" onclick="openCourseDetails('${c.code}')">
                <div class="cc-header">
                    <div class="cc-icon ${colorClass}">${c.code.substring(0,2)}</div>
                    <span class="cc-tag ${diffColorClass}">${c.difficulty}</span>
                </div>
                <div class="cc-body"><h4>${c.name}</h4><p>${c.code}</p></div>
                <div class="cc-footer">
                    <div class="cc-stats"><span>📖 0 tasks</span><span>🕒 0.0h studied</span></div>
                    <div class="cc-arrow">›</div>
                </div>
            </div>`;
    }).join('');
    document.getElementById('miniCoursesArea').innerHTML = html;
    document.getElementById('fullCoursesGrid').innerHTML = html;
    document.getElementById('courseCount').innerText = courseList.length;
}

function updateStats() {
    document.getElementById('tasksDue').innerText = taskList.filter(t => !t.done).length;
    document.getElementById('progressText').innerText = "0%";
    document.getElementById('progressVal').innerText = "0%";
}

// --- 5. LOGIC ACTIONS ---
function addTask() {
    const title = document.getElementById('taskTitle').value;
    const course = document.getElementById('taskCourse').value;
    const date = document.getElementById('taskDate').value;
    const priority = document.getElementById('taskPriority').value;
    if(title) {
        taskList.push({ id: Date.now(), title, course, date, priority, done: false });
        closeModal('taskModal');
        showToast('Task added');
        updateStats();
        // Render pending tasks to dashboard
        const container = document.getElementById('taskListArea');
        const pending = taskList.filter(t => !t.done);
        container.innerHTML = (pending.length === 0) ? `<div style="text-align:center; padding:30px; color:#9ca3af; font-size:14px;">No upcoming tasks</div>` : pending.map(t => `<div class="task-item"><div class="task-left"><input type="checkbox" class="task-checkbox" onclick="finishTask(${t.id})"><div class="task-info"><h4>${t.title}</h4><span>${t.course} • Due ${t.date}</span></div></div><span class="task-tag ${t.priority === 'urgent' ? 'tag-urgent' : 'tag-medium'}">${t.priority}</span></div>`).join('');
    }
}

function addCourse() {
    const name = document.getElementById('courseName').value;
    const code = document.getElementById('courseCode').value;
    const diff = document.getElementById('courseDiff').value;
    if(name) {
        courseList.push({ id: Date.now(), name, code, difficulty: diff, color: (diff === "hard" ? "red" : "blue") });
        closeModal('courseModal');
        showToast('Course added');
        renderCourses();
    }
}

function finishTask(id) {
    const t = taskList.find(x => x.id === id);
    if(t) { t.done = true; showToast("Task completed!"); updateStats(); }
}

// ENERGY
const energyLevels = { 1: { color: "#ef4444", text: "Light review only" }, 2: { color: "#f97316", text: "Easy tasks" }, 3: { color: "#eab308", text: "Regular study" }, 4: { color: "#84cc16", text: "Good for most tasks" }, 5: { color: "#10b981", text: "Tackle hard topics" } };
function setEnergy(val) {
    userEnergy = val;
    document.querySelectorAll('.energy-btn').forEach(b => b.classList.remove('selected'));
    const clicked = document.querySelector(`.energy-btn[data-level="${val}"]`);
    if(clicked) clicked.classList.add('selected');
    const labelDiv = document.getElementById('energyLabel');
    const data = energyLevels[val];
    labelDiv.innerText = data.text;
    labelDiv.style.color = data.color;
}

function showToast(msg) {
    const t = document.getElementById('toast');
    t.innerText = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2500);
}

function addTimeSlot() {
    const div = document.createElement('div');
    div.className = 'schedule-row';
    div.style.background = '#f3f4f6'; div.style.padding = '15px'; div.style.borderRadius = '14px'; div.style.marginBottom = '12px'; div.style.display = 'flex'; div.style.alignItems = 'center'; div.style.gap = '15px';
    div.innerHTML = `<select style="padding:8px; border-radius:8px; border:1px solid #ddd;"><option>Mon</option><option>Tue</option><option>Wed</option></select><input type="time" style="padding:8px; border-radius:8px; border:1px solid #ddd;"><input placeholder="Activity" style="flex:1; padding:8px; border-radius:8px; border:1px solid #ddd;"><span onclick="this.parentElement.remove()" style="cursor:pointer; color:red;">🗑</span>`;
    document.getElementById('scheduleContainer').appendChild(div);
}

// --- 7. AI INTEGRATION ---
async function callOpenAI(messages, jsonMode = false) {
    if (!API_KEY) return null;
    const body = { model: "gpt-4o-mini", messages: messages, temperature: 0.7 };
    if(jsonMode) body.response_format = { type: "json_object" };
    try {
        const res = await fetch("https://api.openai.com/v1/chat/completions", { method: "POST", headers: { "Content-Type": "application/json", "Authorization": `Bearer ${API_KEY}` }, body: JSON.stringify(body) });
        const data = await res.json();
        return data.choices[0].message.content;
    } catch(e) { return null; }
}

async function generateAndRenderPlan(trigger = false) {
    const out = document.getElementById('planOutput');
    out.innerHTML = `<div style="text-align:center; padding:10px; color:#6366f1;">🔮 Generating Plan...</div>`;
    const data = { energy: userEnergy, tasks: taskList.filter(t => !t.done), courses: courseList, period: document.getElementById('planPeriod').value };
    const prompt = `Create a ${data.period} study plan for energy ${data.energy}/5. Tasks: ${JSON.stringify(data.tasks)}. JSON: { "sessions": [{ "title": "Math", "duration": 30, "type": "Focus" }] }`;
    const res = await callOpenAI([{ role: "system", content: "You are a JSON generator." }, { role: "user", content: prompt }], true);
    if(res) {
        const plan = JSON.parse(res);
        out.innerHTML = plan.sessions.map(s => `<div class="plan-item"><div><strong>${s.title}</strong> <span style="font-size:12px; color:#6b7280;">(${s.type})</span></div><div style="font-weight:600; color:#6366f1;">${s.duration}m</div></div>`).join('');
    }
}

function addChatMsg(role, text, type) {
    const log = document.getElementById('chatLog');
    const div = document.createElement('div');
    div.className = `chat-msg ${type}`;
    div.innerHTML = text.replace(/\n/g, '<br>');
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
}

function quickChat(txt) { document.getElementById('chatInput').value = txt; sendChat(); }

async function sendChat() {
    const input = document.getElementById('chatInput');
    const txt = input.value.trim();
    if(!txt) return;
    addChatMsg("You", txt, 'msg-user');
    input.value = '';
    const context = { energy: userEnergy, tasks: taskList.filter(t => !t.done), courses: courseList };
    const messages = [{ role: "system", content: `You are StudyBuddy. Context: ${JSON.stringify(context)}` }, { role: "user", content: txt }];
    const reply = await callOpenAI(messages);
    if(reply) addChatMsg("Buddy", reply, 'msg-ai');
}

function setupFileUpload() {
    const el = document.getElementById('fileUpload');
    el.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if(!file) return;
        if(file.type === "application/pdf") {
            try {
                const buff = await file.arrayBuffer();
                const pdf = await pdfjsLib.getDocument(buff).promise;
                let full = "";
                for(let i=1; i<=pdf.numPages; i++) {
                    const page = await pdf.getPage(i);
                    const t = await page.getTextContent();
                    full += t.items.map(s => s.str).join(" ");
                }
                fileContextContent = full;
                addChatMsg("System", "PDF read! Ask me anything.", 'msg-ai');
            } catch(err) {}
        }
    });
}

let timerInterval;
function startTimer() {
    if(timerInterval) return;
    let time = 25 * 60;
    const display = document.getElementById('timerDisplay');
    timerInterval = setInterval(() => {
        time--;
        let m = Math.floor(time / 60); let s = time % 60;
        display.innerText = `${m}:${s < 10 ? '0'+s : s}`;
        if(time <= 0) stopTimer();
    }, 1000);
}

function stopTimer() { clearInterval(timerInterval); timerInterval = null; document.getElementById('timerDisplay').innerText = "25:00"; }