/* =========================================
   AI LAYER: Google Gemini API (Flash 1.5)
   ========================================= */

const ai = {
    // We store history in a generic format, then convert it for Gemini when sending
    chatHistory: [
        { role: "system", content: "You are a helpful study tutor. Keep answers concise." }
    ],
    fileContext: "",

    getApiKey: function() {
        return document.getElementById('apiKeyInput').value;
    },

    // 1. GENERIC API CALL (Switched to Google Gemini)
    call: async function(messages, jsonMode = false) {
        const key = this.getApiKey();
        if (!key) {
            if(window.app) app.showToast("⚠️ API Key Missing! Get one from Google AI Studio.");
            return null;
        }

        // --- MODEL SELECTION ---
        // "gemini-1.5-flash" is the cheap, fast version you requested.
        // Change to "gemini-1.5-pro" if you want smarter (but more expensive) logic.
        const MODEL_NAME = "gemini-1.5-flash"; 
        const ENDPOINT = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL_NAME}:generateContent?key=${key}`;

        // --- CONVERT MESSAGES TO GEMINI FORMAT ---
        // OpenAI uses { role: "user", content: "..." }
        // Gemini uses { role: "user", parts: [{ text: "..." }] }
        // System instructions are handled separately in Gemini REST API
        
        let systemInstructionText = "";
        const googleContents = messages
            .filter(msg => {
                if (msg.role === "system") {
                    systemInstructionText += msg.content + "\n";
                    return false; // Remove system msgs from the main chat list
                }
                return true;
            })
            .map(msg => ({
                role: msg.role === "assistant" ? "model" : "user", // Gemini uses 'model', not 'assistant'
                parts: [{ text: msg.content }]
            }));

        const payload = {
            contents: googleContents,
            system_instruction: {
                parts: [{ text: systemInstructionText.trim() }]
            },
            generationConfig: {
                temperature: 0.7,
                // If jsonMode is true, force JSON output
                response_mime_type: jsonMode ? "application/json" : "text/plain"
            }
        };

        try {
            const res = await fetch(ENDPOINT, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            
            const data = await res.json();
            
            if (data.error) {
                console.error("Gemini Error:", data.error);
                throw new Error(data.error.message);
            }

            // Extract text from Gemini response
            return data.candidates[0].content.parts[0].text;

        } catch (e) {
            console.error(e);
            if(window.app) app.showToast("AI Error: " + e.message);
            return null;
        }
    },

    // 2. GENERATE STUDY PLAN
    generatePlan: async function() {
        const out = document.getElementById('planOutput');
        out.innerHTML = `<div style="text-align:center; padding:20px; color:#6366f1;">🧠 Gemini is thinking...</div>`;

        const context = {
            energy: data.userEnergy,
            tasks: data.taskList.filter(t => !t.done),
            courses: data.courseList.map(c => ({ name: c.name, difficulty: c.difficulty }))
        };

        const prompt = `
            Create a daily study plan based on Energy Level ${data.userEnergy}/5.
            Tasks: ${JSON.stringify(context.tasks)}.
            Courses: ${JSON.stringify(context.courses)}.
            Return valid JSON with a key "sessions" which is an array of objects.
            Each object must have: "title", "duration_min" (number), and "type".
            Do not include markdown formatting like \`\`\`json. Just the raw JSON.
        `;

        // We send a simplified history for the planner
        const res = await this.call([
            { role: "system", content: "You are a JSON scheduler." },
            { role: "user", content: prompt }
        ], true);

        if (res) {
            try {
                // Gemini sometimes wraps JSON in markdown blocks, we clean it
                const cleanJson = res.replace(/```json/g, '').replace(/```/g, '').trim();
                const plan = JSON.parse(cleanJson);
                
                out.innerHTML = plan.sessions.map(s => `
                    <div class="plan-item">
                        <div style="display:flex; flex-direction:column;">
                            <span style="font-weight:600;">${s.title}</span>
                            <span style="font-size:11px; color:#6b7280;">${s.type}</span>
                        </div>
                        <div style="font-weight:bold; color:#6366f1;">${s.duration_min}m</div>
                    </div>
                `).join('');
                if(window.app) app.showToast("Plan Generated!");
            } catch (e) {
                console.error("JSON Parse Error", e);
                out.innerHTML = `<div class="empty-state">Error parsing plan. Try again.</div>`;
            }
        } else {
            out.innerHTML = `<div class="empty-state">Failed to generate. Check API Key.</div>`;
        }
    },

    // 3. CHAT LOGIC
    sendMessage: async function() {
        const inp = document.getElementById('chatInput');
        const txt = inp.value.trim();
        if (!txt) return;

        // UI Update
        const log = document.getElementById('chatLog');
        log.innerHTML += `<div class="chat-msg msg-user">${txt}</div>`;
        inp.value = "";
        log.scrollTop = log.scrollHeight;

        // Add to history
        this.chatHistory.push({ role: "user", content: txt });

        // Add System Context for File
        let currentMessages = [...this.chatHistory];
        if (this.fileContext) {
            // Inject file context as a system message at the start for this turn
            currentMessages.unshift({ 
                role: "system", 
                content: `Reference this user file content: ${this.fileContext.substring(0, 10000)}` 
            });
        }
        // Add Task Context
        currentMessages.unshift({
             role: "system", 
             content: `User Tasks: ${JSON.stringify(data.taskList)}` 
        });

        const reply = await this.call(currentMessages);

        if (reply) {
            this.chatHistory.push({ role: "assistant", content: reply });
            log.innerHTML += `<div class="chat-msg msg-ai">${reply}</div>`;
            log.scrollTop = log.scrollHeight;
        }
    },

    // 4. FILE HANDLER (PDF/Text)
    handleFileUpload: async function(e) {
        const file = e.target.files[0];
        if (!file) return;

        if(window.app) app.showToast("Reading file...");
        
        try {
            if (file.type === "application/pdf") {
                const buf = await file.arrayBuffer();
                const pdf = await pdfjsLib.getDocument(buf).promise;
                let text = "";
                for (let i = 1; i <= pdf.numPages; i++) {
                    const page = await pdf.getPage(i);
                    const content = await page.getTextContent();
                    text += content.items.map(item => item.str).join(" ");
                }
                this.fileContext = text;
                if(window.app) app.showToast("PDF Read Successfully!");
                document.getElementById('chatLog').innerHTML += `<div class="chat-msg msg-ai">I've read your PDF. Ask me to summarize it!</div>`;
                
            } else {
                const reader = new FileReader();
                reader.onload = (ev) => {
                    this.fileContext = ev.target.result;
                    if(window.app) app.showToast("File Read!");
                    document.getElementById('chatLog').innerHTML += `<div class="chat-msg msg-ai">I've read your text file.</div>`;
                };
                reader.readAsText(file);
            }
        } catch (err) {
            console.error(err);
            if(window.app) app.showToast("Error reading file");
        }
    }
};