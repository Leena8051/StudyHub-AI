/* =========================================
   DATA LAYER: Handles State & LocalStorage
   ========================================= */

const data = {
    // Default Data
    courseList: [],
    taskList: [],
    userEnergy: 5,
    
    // Load from Browser Memory
    load: function() {
        const saved = localStorage.getItem('studyHubData');
        if (saved) {
            const parsed = JSON.parse(saved);
            this.courseList = parsed.courseList || [];
            this.taskList = parsed.taskList || [];
            this.userEnergy = parsed.userEnergy || 5;
        } else {
            // Initial Seed Data if empty
            this.courseList = [
                { id: 1, name: "Intro to CS", code: "CS101", difficulty: "medium", color: "linear-gradient(135deg,#6366f1,#8b5cf6)", syllabus: ["Algorithms", "Data Structures"] },
                { id: 2, name: "Calculus I", code: "MATH101", difficulty: "hard", color: "linear-gradient(135deg,#ef4444,#db2777)", syllabus: ["Derivatives", "Integrals"] }
            ];
        }
    },

    // Save to Browser Memory
    save: function() {
        const payload = {
            courseList: this.courseList,
            taskList: this.taskList,
            userEnergy: this.userEnergy
        };
        localStorage.setItem('studyHubData', JSON.stringify(payload));
    },

    // Set Energy
    setEnergy: function(level) {
        this.userEnergy = level;
        this.save();
        // Update UI immediately via the global app object
        if(window.app) app.updateUI();
    },

    // Create New Task
    createTask: function() {
        const title = document.getElementById('taskTitle').value;
        const date = document.getElementById('taskDate').value;
        const priority = document.getElementById('taskPriority').value;
        const courseId = document.getElementById('taskCourse').value;

        if (!title || !date) return alert("Title and Date required");

        const course = this.courseList.find(c => c.id == courseId);
        
        this.taskList.push({
            id: Date.now(),
            title, date, priority,
            courseId, 
            courseName: course ? course.name : "General",
            done: false
        });

        this.save();
        if(window.app) {
            app.renderTasks();
            app.updateStats();
            app.closeModal('taskModal');
            app.showToast("Task Created!");
        }
    },

    // 2. Create New Course
    createCourse: function() {
        const name = document.getElementById('courseName').value;
        const code = document.getElementById('courseCode').value;
        const diff = document.getElementById('courseDiff').value;
        const instructor = document.getElementById('courseInstructor').value; // NEW
        const color = document.getElementById('courseColor').value;         // NEW

        if (!name || !code) {
            alert("⚠️ Please fill in Course Name and Code.");
            return;
        }

        this.courseList.push({
            id: Date.now(),
            name: name,
            code: code, 
            difficulty: diff, 
            instructor: instructor || "TBD", // Save instructor
            color: color,                    // Save chosen color
            syllabus: ["Introduction", "Chapter 1"]
        });

        this.save();
        if(window.app) {
            app.renderCourses(); // Refresh Course Grid
            app.closeModal('courseModal');
            app.showToast("Course Added! 📚");
            
            // Clear Inputs
            document.getElementById('courseName').value = "";
            document.getElementById('courseCode').value = "";
            document.getElementById('courseInstructor').value = "";
        }
    },

    // Mark Task Complete
    toggleTask: function(id) {
        const t = this.taskList.find(x => x.id === id);
        if(t) {
            t.done = !t.done;
            this.save();
            if(window.app) {
                app.renderTasks();
                app.updateStats();
            }
        }
    }
};