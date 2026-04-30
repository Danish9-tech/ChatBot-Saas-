class IU_Chatbot {
    constructor() {
        this.init();
    }

    init() {
        // Extract script tag info
        const scriptTag = document.currentScript || document.querySelector('script[src*="chatbot.js"]');
        this.apiKey = scriptTag ? scriptTag.getAttribute('data-api-key') : null;
        this.baseUrl = scriptTag ? new URL(scriptTag.src).origin : 'http://localhost:8000';
        
        // Generate or retrieve session ID
        this.sessionId = localStorage.getItem('iu_chatbot_session_id');
        if (!this.sessionId) {
            this.sessionId = 'sess_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('iu_chatbot_session_id', this.sessionId);
        }

        if (!this.apiKey) {
            console.error('IU Chatbot: Missing data-api-key on script tag.');
            return;
        }

        this.injectCSS();
        this.createUI();
        this.bindEvents();
        this.loadHistory();
    }

    injectCSS() {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = `${this.baseUrl}/public/chatbot.css`;
        document.head.appendChild(link);
    }

    createUI() {
        const wrapper = document.createElement('div');
        wrapper.id = 'iu-chatbot-widget';
        wrapper.innerHTML = `
            <div id="iu-chatbot-container">
                <div id="iu-chatbot-header">
                    <div id="iu-chatbot-header-info">
                        <div id="iu-chatbot-logo">IU</div>
                        <div>
                            <p id="iu-chatbot-title">Help Desk</p>
                            <p id="iu-chatbot-subtitle">We typically reply in seconds</p>
                        </div>
                    </div>
                    <button id="iu-chatbot-close">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                    </button>
                </div>
                <div id="iu-chatbot-messages">
                    <div class="iu-message bot">Hello! How can I help you today?</div>
                </div>
                <div id="iu-chatbot-suggestions"></div>
                <div id="iu-chatbot-input-area">
                    <input type="text" id="iu-chatbot-input" placeholder="Type your message..." />
                    <button id="iu-chatbot-send">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                    </button>
                </div>
            </div>
            <button id="iu-chatbot-toggle">
                <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>
            </button>
        `;
        document.body.appendChild(wrapper);

        this.elements = {
            container: document.getElementById('iu-chatbot-container'),
            toggle: document.getElementById('iu-chatbot-toggle'),
            close: document.getElementById('iu-chatbot-close'),
            messages: document.getElementById('iu-chatbot-messages'),
            suggestions: document.getElementById('iu-chatbot-suggestions'),
            input: document.getElementById('iu-chatbot-input'),
            send: document.getElementById('iu-chatbot-send')
        };

        this.showSuggestions([
            "What is the admission process?",
            "What are the semester fees?",
            "How can I apply for a hostel?"
        ]);
    }

    bindEvents() {
        this.elements.toggle.addEventListener('click', () => this.toggleChat());
        this.elements.close.addEventListener('click', () => this.toggleChat());
        
        this.elements.send.addEventListener('click', () => this.sendMessage());
        this.elements.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
    }

    toggleChat() {
        this.elements.container.classList.toggle('open');
        if (this.elements.container.classList.contains('open')) {
            this.elements.input.focus();
            this.scrollToBottom();
        }
    }

    showSuggestions(suggestions) {
        this.elements.suggestions.innerHTML = '';
        suggestions.forEach(text => {
            const btn = document.createElement('button');
            btn.className = 'iu-suggestion-chip';
            btn.textContent = text;
            btn.addEventListener('click', () => {
                this.elements.input.value = text;
                this.sendMessage();
            });
            this.elements.suggestions.appendChild(btn);
        });
    }

    hideSuggestions() {
        this.elements.suggestions.innerHTML = '';
        this.elements.suggestions.style.display = 'none';
    }

    appendMessage(text, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `iu-message ${sender}`;
        msgDiv.textContent = text;
        this.elements.messages.appendChild(msgDiv);
        this.scrollToBottom();
    }

    showTyping() {
        const msgDiv = document.createElement('div');
        msgDiv.className = `iu-message bot iu-typing`;
        msgDiv.id = 'iu-typing-indicator';
        msgDiv.innerHTML = `
            <div class="iu-typing-indicator">
                <div class="iu-dot"></div>
                <div class="iu-dot"></div>
                <div class="iu-dot"></div>
            </div>
        `;
        this.elements.messages.appendChild(msgDiv);
        this.scrollToBottom();
    }

    removeTyping() {
        const el = document.getElementById('iu-typing-indicator');
        if (el) el.remove();
    }

    scrollToBottom() {
        this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
    }

    async loadHistory() {
        try {
            const res = await fetch(`${this.baseUrl}/api/v1/history?session_id=${this.sessionId}`, {
                headers: { 'x-api-key': this.apiKey }
            });
            if (res.ok) {
                const history = await res.json();
                if (history.length > 0) {
                    this.elements.messages.innerHTML = ''; // clear default greeting
                    history.forEach(msg => {
                        this.appendMessage(msg.message, msg.sender);
                    });
                }
            }
        } catch (e) {
            console.error("Failed to load history", e);
        }
    }

    async sendMessage() {
        const text = this.elements.input.value.trim();
        if (!text) return;

        this.elements.input.value = '';
        this.elements.input.disabled = true;
        this.elements.send.disabled = true;
        this.hideSuggestions();

        this.appendMessage(text, 'user');
        this.showTyping();

        try {
            const res = await fetch(`${this.baseUrl}/api/v1/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-api-key': this.apiKey
                },
                body: JSON.stringify({
                    query: text,
                    session_id: this.sessionId
                })
            });

            this.removeTyping();

            if (res.ok) {
                const data = await res.json();
                this.appendMessage(data.answer, 'bot');
            } else {
                this.appendMessage("Sorry, I'm having trouble connecting to the server.", 'bot');
            }
        } catch (e) {
            this.removeTyping();
            this.appendMessage("Sorry, a network error occurred.", 'bot');
        } finally {
            this.elements.input.disabled = false;
            this.elements.send.disabled = false;
            this.elements.input.focus();
        }
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new IU_Chatbot());
} else {
    new IU_Chatbot();
}
