/* =========================================
   APP LAYER: UI Logic & Events
   ========================================= */

const app = {
    timerInterval: null,
    timerTime: 25 * 60,

    init: function() {
        // 1. Load Data
        data.load();

        // 2. Initial Render
        this.updateUI();
        this.renderCourses();
        this.renderTasks();

        // 3. Setup Listeners
        const fileUpload = document.getElementById('fileUpload');
        if (fileUpload) {
            fileUpload.addEventListener('change', (e) => ai.handleFileUpload(e));
        }
        
        // 4. Set Initial Energy UI
        this.updateEnergyUI();
    },

    // --- NAVIGATION ---
    navTo: function(pageId, btn) {
        document.querySelectorAll('.page-section').forEach(el => el.classList.remove('active'));
        document.getElementById(pageId).classList.add('active');
        
        if (btn) {
            document.querySelectorAll('.menu-item').forEach(el => el.classList.remove('active'));
            btn.classList.add('active');
        }
    },

    // --- MODALS ---
    openModal: function(id) { 
        document.getElementById(id).style.display = 'flex'; 
    },

    closeModal: function(id) { 
        document.getElementById(id).style.display = 'none'; 
    },
    
    openTaskModal: function() {
        const sel = document.getElementById('taskCourse');
        // Populate the dropdown with courses from data.js
        if(data.courseList.length > 0) {
            sel.innerHTML = data.courseList.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        } else {
            sel.innerHTML = `<option value="">No courses yet</option>`;
        }
        this.openModal('taskModal');
    },

    // --- NEW: COLOR PICKER LOGIC (Required for your new Modal) ---
    selectColor: function(element, colorCode) {
        // 1. Remove 'active' class from all swatches
        document.querySelectorAll('.color-swatch').forEach(el => el.classList.remove('active'));
        
        // 2. Add 'active' class to the clicked one
        element.classList.add('active');
        
        // 3. Update the hidden input value so data.js can read it
        document.getElementById('courseColor').value = colorCode;
    },

    showToast: function(msg) {
        const t = document.getElementById('toast');
        t.innerText = msg;
        t.classList.add('show');
        setTimeout(() => t.classList.remove('show'), 3000);
    },

    // --- RENDERING UI ---
    updateUI: function() {
        this.updateStats();
        this.updateEnergyUI();
    },

    updateEnergyUI: function() {
        document.querySelectorAll('.energy-btn').forEach(b => b.classList.remove('selected'));
        const btn = document.querySelector(`.energy-btn[data-level="${data.userEnergy}"]`);
        if(btn) btn.classList.add('selected');
        
        const labels = {
            1: "Rest day. Light reading only.",
            2: "Low energy. Quick tasks.",
            3: "Balanced mode. Standard study.",
            4: "High energy. Good focus.",
            5: "Maximum Power! Tackle hard subjects."
        };
        const lbl = document.getElementById('energyLabel');
        if(lbl) lbl.innerText = labels[data.userEnergy] || "Balanced";
    },

    renderCourses: function() {
        // Render Mini Grid (Dashboard) and Full Grid (Courses Page)
        const html = data.courseList.map(c => `
            <div class="course-card-clone" onclick="app.openCourseDetails(${c.id})">
                <div style="display:flex; justify-content:space-between;">
                    <div class="logo-icon" style="background:${c.color};">${c.code.substring(0,2)}</div>
                    <span class="task-tag tag-${c.difficulty === 'hard' || c.difficulty === 'very hard' ? 'high' : 'medium'}">${c.difficulty}</span>
                </div>
                <div>
                    <h4 style="margin:10px 0 0;">${c.name}</h4>
                    <p style="margin:0; font-size:12px; color:#6b7280;">${c.code}</p>
                </div>
                <div style="margin-top:15px; font-size:12px; color:#6b7280;">
                    ${c.syllabus ? c.syllabus.length : 0} Topics • View Details
                </div>
            </div>
        `).join('');

        const grid1 = document.getElementById('miniCoursesGrid');
        const grid2 = document.getElementById('fullCoursesGrid');
        if(grid1) grid1.innerHTML = html;
        if(grid2) grid2.innerHTML = html;
        document.getElementById('courseCount').innerText = data.courseList.length;
    },

    renderTasks: function() {
        const container = document.getElementById('taskListArea');
        const pending = data.taskList.filter(t => !t.done).sort((a,b) => new Date(a.date) - new Date(b.date));

        if (pending.length === 0) {
            container.innerHTML = '<div class="empty-state">No upcoming tasks</div>';
            return;
        }

        container.innerHTML = pending.map(t => `
            <div class="task-item">
                <div style="display:flex; align-items:center;">
                    <input type="checkbox" class="task-checkbox" onclick="data.toggleTask(${t.id})">
                    <div>
                        <div style="font-weight:600; font-size:14px;">${t.title}</div>
                        <div style="font-size:12px; color:#6b7280;">${t.courseName} • Due ${t.date}</div>
                    </div>
                </div>
                <span class="task-tag tag-${t.priority}">${t.priority}</span>
            </div>
        `).join('');
        
        document.getElementById('tasksDue').innerText = pending.length;
    },

    updateStats: function() {
        const total = data.taskList.length;
        const done = data.taskList.filter(t => t.done).length;
        const pct = total === 0 ? 0 : Math.round((done / total) * 100);
        
        // Use charts.js logic
        if (typeof charts !== 'undefined') {
            charts.updateCircularProgress(pct);
        }
    },

    openCourseDetails: function(id) {
        const course = data.courseList.find(c => c.id === id);
        if (!course) return;

        document.getElementById('detailName').innerText = course.name;
        document.getElementById('detailCode').innerText = `${course.code} • ${course.difficulty}`;
        const icon = document.getElementById('detailIcon');
        icon.innerText = course.code.substring(0,2);
        icon.style.background = course.color;

        // Render Syllabus
        document.getElementById('detailSyllabus').innerHTML = (course.syllabus || []).map(s => `
            <div class="plan-item"><span>${s}</span></div>
        `).join('');

        // Render Tasks for this course
        const cTasks = data.taskList.filter(t => t.courseId == id);
        document.getElementById('detailTasks').innerHTML = cTasks.length ? cTasks.map(t => `
            <div class="task-item">${t.title} <span class="task-tag tag-${t.priority}">${t.priority}</span></div>
        `).join('') : '<p class="empty-state">No tasks yet.</p>';

        this.navTo('courseDetailsPage');
    },

    // --- TIMER ---
    selectMethod: function(el, mins) {
        document.querySelectorAll('.method-card').forEach(c => c.classList.remove('active'));
        el.classList.add('active');
        this.timerTime = mins * 60;
        this.updateTimerDisplay();
    },

    updateTimerDisplay: function() {
        const m = Math.floor(this.timerTime / 60);
        const s = this.timerTime % 60;
        document.getElementById('timerDisplay').innerText = `${m}:${s < 10 ? '0'+s : s}`;
    },

    startTimer: function() {
        if (this.timerInterval) return;
        this.timerInterval = setInterval(() => {
            this.timerTime--;
            this.updateTimerDisplay();
            if (this.timerTime <= 0) {
                this.stopTimer();
                alert("Session Complete!");
            }
        }, 1000);
    },

    stopTimer: function() {
        clearInterval(this.timerInterval);
        this.timerInterval = null;
    },

    // --- SCHEDULE ---
    addTimeSlot: function() {
        const div = document.createElement('div');
        div.style.cssText = "display:flex; gap:10px; margin-bottom:10px; align-items:center;";
        div.innerHTML = `
            <select style="width:80px; padding:10px; border-radius:10px; border:1px solid #ddd;">
                <option>Mon</option><option>Tue</option><option>Wed</option>
            </select>
            <input type="time" style="padding:10px; border-radius:10px; border:1px solid #ddd;">
            <input type="text" placeholder="Class/Activity" style="flex:1; padding:10px; border-radius:10px; border:1px solid #ddd;">
            <button onclick="this.parentElement.remove()" style="border:none; background:none; cursor:pointer;">❌</button>
        `;
        document.getElementById('scheduleContainer').appendChild(div);
    }
};

// Start the App when HTML is ready
document.addEventListener('DOMContentLoaded', () => app.init());