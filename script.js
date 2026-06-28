// script.js – Grok Scheme Assistant (full flow with premium UI)

/* ==== State Management ==== */
const state = {
  step: "greeting",
  userName: null,
  language: null,
  schemes: [],
  selectedScheme: null,
  confidence: 1.0,
  tempDetails: null,
  details: null,
};

/* ==== DOM References ==== */
const chatArea = document.getElementById("chat-area");
const textInput = document.getElementById("text-input");
const sendBtn = document.getElementById("send-btn");
const voiceBtn = document.getElementById("voice-btn");

/* ==== Utility Functions ==== */
function addMessage(text, from = "bot") {
  const msg = document.createElement("div");
  msg.className = `message ${from}`;
  const ts = document.createElement("span");
  ts.className = "timestamp";
  const now = new Date();
  ts.textContent = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const content = document.createElement("span");
  content.className = "content";
  content.textContent = text;
  msg.appendChild(ts);
  msg.appendChild(content);
  chatArea.appendChild(msg);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function addChips(options, callback) {
  const container = document.createElement("div");
  container.className = "chip-container";
  options.forEach(opt => {
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.textContent = opt.label;
    chip.onclick = () => callback(opt.value);
    container.appendChild(chip);
  });
  // Persistent Start Over chip (always last)
  const startOver = document.createElement("div");
  startOver.className = "chip";
  startOver.textContent = "Start Over";
  startOver.onclick = () => resetConversation();
  container.appendChild(startOver);
  chatArea.appendChild(container);
  chatArea.scrollTop = chatArea.scrollHeight;
  return container;
}

function addConfidenceChip(confidence, container = null) {
  const perc = Math.round(confidence * 100);
  const chip = document.createElement("div");
  chip.className = "chip confidence-chip";
  chip.textContent = `Confidence: ${perc}%`;
  const target = container || document.querySelector('.chip-container');
  if (target) {
    const startOver = target.querySelector('.chip:last-child');
    target.insertBefore(chip, startOver);
  }
}

/* ==== Conversation Flow ==== */
function greet() {
  addMessage("👋 Hello! I’m Grok, your scheme‑assistant. What’s your name?");
  state.step = "askName";
}

function handleName(input) {
  const name = input.trim().split(/\s+/)[0]; // first token as name
  if (name) {
    state.userName = name;
    addMessage(`Nice to meet you, ${name}!`, "user");
    addMessage(`Hi ${name} 👋`);
    askLanguage();
  } else {
    addMessage("Sorry, I didn’t catch that. Please tell me your name.");
  }
}

function askLanguage() {
  addMessage("Which language would you like to continue in?");
  const langs = [
    { label: "English", value: "en" },
    { label: "Telugu", value: "te" },
    { label: "Hindi", value: "hi" },
    { label: "Marathi", value: "mr" },
  ];
  addChips(langs, lang => {
    state.language = lang;
    addMessage(`Proceeding in ${lang === "en" ? "English" : "Telugu"}...`, "user");
    showProjectIntro();
  });
  state.step = "languageSelected";
}

function showProjectIntro() {
  addMessage("I’m here to help you discover government schemes that fit your profile. I’ll ask a few details and then suggest the best options.", "bot");
  const opts = [
    { label: "🚀 Proceed to details", value: "proceed" },
    { label: "🔁 Change Language", value: "changeLang" },
  ];
  addChips(opts, choice => {
    if (choice === "proceed") {
      requestDetailsForm();
    } else {
      askLanguage();
    }
  });
}

/* ==== Details Form ==== */
function requestDetailsForm() {
  const formHtml = `
    <div class="form">
      <label>Land owned (sq ft): <input type="number" id="land" placeholder="e.g., 1200"/></label><br/>
      <label>Annual income (₹): <input type="number" id="income" placeholder="e.g., 250000"/></label><br/>
      <button id="formSubmitBtn">Submit</button>
    </div>`;
  const wrapper = document.createElement("div");
  wrapper.className = "message bot";
  wrapper.innerHTML = formHtml;
  chatArea.appendChild(wrapper);
  chatArea.scrollTop = chatArea.scrollHeight;
  document.getElementById("formSubmitBtn").onclick = () => {
    const land = document.getElementById("land").value.trim();
    const income = document.getElementById("income").value.trim();
    if (!land || !income) {
      const err = document.createElement('div');
      err.className = 'error-message';
      err.textContent = 'All fields are required.';
      document.querySelector('.form').appendChild(err);
      return;
    }
    state.tempDetails = { land, income };
    addMessage(`You entered: Land=${land} sq ft, Income=₹${income}`, "user");
    confirmDetailsPrompt();
  };
}

function confirmDetailsPrompt() {
  const { land, income } = state.tempDetails || {};
  addMessage(`Please confirm your details:\nLand: ${land} sq ft\nIncome: ₹${income}`, "bot");
  const opts = [
    { label: "✅ Yes, correct", value: "yes" },
    { label: "❌ No, edit", value: "no" },
  ];
  addChips(opts, ans => {
    if (ans === "yes") {
      state.details = state.tempDetails;
      state.tempDetails = null;
      fetchSchemes();
    } else {
      requestDetailsForm();
    }
  });
}

/* ==== Mock Scheme Retrieval ==== */
function fetchSchemes() {
  addMessage("Looking up the best schemes for you…", "bot");
  setTimeout(() => {
    state.schemes = [
      { id: 1, name: "Education Grant", description: "Support for school fees." },
      { id: 2, name: "Agriculture Loan", description: "Low‑interest loan for farmers." },
      { id: 3, name: "Health Subsidy", description: "Free health check‑ups." },
      { id: 4, name: "Housing Scheme", description: "Affordable housing assistance." },
    ];
    presentSchemes();
  }, 800);
}

function presentSchemes() {
  addMessage("Here are the schemes I found. Which one interests you?", "bot");
  const opts = state.schemes.map(s => ({ label: `${s.name}: ${s.description}`, value: s.id }));
  const container = addChips(opts, id => {
    state.selectedScheme = state.schemes.find(s => s.id === id);
    addMessage(`You selected: ${state.selectedScheme.name}`, "user");
    showSchemeDetails();
    addApplyNowChip();
  });
  addConfidenceChip(state.confidence, container);
}

function showSchemeDetails() {
  const s = state.selectedScheme;
  addMessage(`**${s.name}**\n${s.description}\n\nWould you like to apply for this scheme?`, "bot");
  const opts = [
    { label: "✅ Yes, apply", value: "yes" },
    { label: "❌ No, choose another", value: "no" },
    { label: "🔁 Change Language", value: "changeLang" },
  ];
  addChips(opts, answer => {
    if (answer === "yes") {
      addMessage("Great! Let’s gather a few details.", "user");
      requestDetailsForm();
    } else if (answer === "changeLang") {
      askLanguage();
    } else {
      presentSchemes();
    }
  });
}

function addApplyNowChip() {
  const chip = document.createElement('div');
  chip.className = 'chip';
  chip.textContent = 'Apply Now';
  chip.onclick = () => requestDetailsForm();
  const container = document.querySelector('.chip-container');
  if (container) {
    const startOver = container.querySelector('.chip:last-child');
    container.insertBefore(chip, startOver);
  }
}

/* ==== Finalisation ==== */
function finalizeApplication() {
  addMessage("Your application is being processed. You’ll receive an email confirmation shortly.", "bot");
  scheduleEmailReminder();
}

function scheduleEmailReminder() {
  const reminder = {
    text: `Your ${state.selectedScheme.name} application is pending.`,
    trigger: Date.now() + 5 * 60 * 1000,
  };
  localStorage.setItem(`reminder_${Date.now()}`, JSON.stringify(reminder));
}

/* ==== Voice Input ==== */
let recognizer = null;
function toggleVoice() {
  if (!('webkitSpeechRecognition' in window)) {
    alert('Voice recognition not supported in this browser.');
    return;
  }
  if (!recognizer) {
    recognizer = new webkitSpeechRecognition();
    recognizer.lang = state.language || 'en-IN';
    recognizer.interimResults = false;
    recognizer.onresult = e => {
      const transcript = e.results[0][0].transcript;
      textInput.value = transcript;
      sendMessage();
    };
    recognizer.onerror = e => console.error('Voice error:', e);
  }
  recognizer.lang = state.language || 'en-IN';
  voiceBtn.classList.toggle('recording');
  if (voiceBtn.classList.contains('recording')) recognizer.start();
  else recognizer.stop();
}

/* ==== Message Handler ==== */
function sendMessage() {
  const txt = textInput.value.trim();
  if (!txt) return;
  addMessage(txt, "user");
  textInput.value = "";
  switch (state.step) {
    case "askName":
      handleName(txt);
      break;
    default:
      console.log("No dedicated handler for step", state.step);
  }
}

/* ==== Reset Conversation ==== */
function resetConversation() {
  chatArea.innerHTML = "";
  Object.assign(state, {
    step: "greeting",
    userName: null,
    language: null,
    schemes: [],
    selectedScheme: null,
    confidence: 1.0,
    tempDetails: null,
    details: null,
  });
  greet();
}

/* ==== Event Listeners ==== */
sendBtn.addEventListener("click", sendMessage);
textInput.addEventListener("keypress", e => { if (e.key === "Enter") sendMessage(); });
voiceBtn.addEventListener("click", toggleVoice);

/* ==== Initialization ==== */
greeting();
