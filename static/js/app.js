/**
 * LectureLens — Frontend Application Logic
 * Modern, accessible, vanilla JavaScript controller.
 */

// Global State
let currentTranscript = "";
let currentNotes = null;
let currentAudioFile = null;
let activeFlashcardIndex = 0;
let isGenerating = false;

// Realistic Sample Lecture for Instant 1-Click Testing
const SAMPLE_LECTURE = {
  title: "Distributed Systems: CAP Theorem & Consistency Models",
  subject: "Computer Science (CS 401)",
  transcript: `Good morning everyone. Today we are diving into one of the foundational theorems of distributed computing: Brewer's CAP Theorem, formulated by Eric Brewer in 2000 and later formally proven by Seth Gilbert and Nancy Lynch in 2002.

When we design a distributed data store—meaning data partitioned across multiple independent physical machines communicating over a network—we inevitably face network latency and network partitions. A network partition occurs when communication between nodes is delayed or completely severed, dividing our cluster into disconnected sub-networks.

The CAP theorem states that any distributed data store can simultaneously guarantee at most two of the following three properties:
First, Consistency, specifically Linearizable or Strong Consistency. This means every read operation returns the most recent write or an error. All nodes see the exact same data at the exact same logical instant.
Second, Availability. Every non-failing node returns a non-error response for every received request, though without guaranteeing that it contains the most recent write.
Third, Partition Tolerance. The system continues to operate despite an arbitrary number of messages being dropped or delayed by the network between nodes.

Here is the critical insight: in the real physical world, network partitions are an inescapable physical reality. Fiber cables get severed, switches fail, packet loss spikes. Therefore, Partition Tolerance (P) is non-negotiable. 

This means in practice, our real design trade-off is not 'pick any two of three', but rather: in the presence of a network partition, do we choose Consistency (a CP system) or Availability (an AP system)?

Let's consider a CP system, such as Google Spanner or Apache HBase. When a partition occurs, to prevent serving stale data, the system refuses to accept writes or reads on isolated nodes until consistency is verified. Here, write latency spikes, or clients receive an error: availability is sacrificed to preserve absolute correctness.

Conversely, consider an AP system like Apache Cassandra or Amazon DynamoDB. In an AP design, nodes on either side of the partition continue accepting reads and writes locally. The system remains 100% available, but data becomes temporarily divergent. The system settles on Eventual Consistency, relying on vector clocks or last-write-wins to reconcile conflicts later.

Mathematically, when measuring system availability SLA:
Availability A = (Total Uptime - Downtime) / Total Uptime * 100%
For 'five nines' availability (99.999%), permissible downtime is at most 5.26 minutes per calendar year.

In summary: when designing distributed systems, understand your business domain. For financial transactions and ledger balances, choose CP. For social feeds, shopping carts, and high-throughput telemetry, choose AP.`
};

document.addEventListener("DOMContentLoaded", () => {
  initInputTabs();
  initTextareaCounters();
  initSampleLecture();
  initTxtUpload();
  initAudioUpload();
  initNotesGenerator();
  initStudyTabs();
  initFlashcards();
  initExamQuestions();
  initExports();
  initModal();
});

/* ==========================================================================
   Helper: Safe HTML Escaping (Prevents XSS)
   ========================================================================== */
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/* ==========================================================================
   Toast Notifications
   ========================================================================== */
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

/* ==========================================================================
   Input Tabs Switching
   ========================================================================== */
function initInputTabs() {
  const tabButtons = document.querySelectorAll(".tab-button");
  const tabPanes = document.querySelectorAll(".input-tab-pane");

  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-input-tab");

      tabButtons.forEach(b => b.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add("active");
    });
  });
}

/* ==========================================================================
   Textarea Live Counters & Clear
   ========================================================================== */
function initTextareaCounters() {
  const textarea = document.getElementById("transcriptText");
  const charCount = document.getElementById("charCount");
  const wordCount = document.getElementById("wordCount");
  const clearBtn = document.getElementById("clearTextBtn");

  function updateCounts() {
    const text = textarea.value.trim();
    charCount.textContent = `${textarea.value.length.toLocaleString()} characters`;
    const words = text ? text.split(/\s+/).length : 0;
    wordCount.textContent = `${words.toLocaleString()} words`;
    currentTranscript = textarea.value;
  }

  textarea.addEventListener("input", updateCounts);

  clearBtn.addEventListener("click", () => {
    textarea.value = "";
    updateCounts();
    showToast("Transcript cleared.", "info");
  });
}

/* ==========================================================================
   Sample Lecture Loader
   ========================================================================== */
function initSampleLecture() {
  const loadBtn = document.getElementById("loadSampleBtn");
  const heroBtn = document.getElementById("heroSampleBtn");
  const textarea = document.getElementById("transcriptText");
  const titleInput = document.getElementById("lectureTitle");
  const subjectInput = document.getElementById("lectureSubject");

  function loadSample() {
    // Switch to paste tab
    const pasteTabBtn = document.querySelector('[data-input-tab="tab-paste"]');
    if (pasteTabBtn) pasteTabBtn.click();

    textarea.value = SAMPLE_LECTURE.transcript;
    titleInput.value = SAMPLE_LECTURE.title;
    subjectInput.value = SAMPLE_LECTURE.subject;

    textarea.dispatchEvent(new Event("input"));

    // Scroll to studio
    const studio = document.getElementById("studio");
    if (studio) studio.scrollIntoView({ behavior: "smooth" });

    showToast("Sample lecture loaded! Click 'Generate Smart Notes' below to test.", "success");
  }

  if (loadBtn) loadBtn.addEventListener("click", loadSample);
  if (heroBtn) heroBtn.addEventListener("click", loadSample);
}

/* ==========================================================================
   Option 2: Text File Upload (.txt)
   ========================================================================== */
function initTxtUpload() {
  const dropzone = document.getElementById("txtDropzone");
  const fileInput = document.getElementById("txtFileInput");
  const browseBtn = document.getElementById("browseTxtBtn");
  const fileCard = document.getElementById("txtFileInfoCard");
  const fileName = document.getElementById("txtFileName");
  const fileSize = document.getElementById("txtFileSize");
  const replaceBtn = document.getElementById("replaceTxtBtn");
  const removeBtn = document.getElementById("removeTxtBtn");
  const textarea = document.getElementById("transcriptText");

  browseBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files.length) {
      handleTxtFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) {
      handleTxtFile(fileInput.files[0]);
    }
  });

  function handleTxtFile(file) {
    if (!file.name.toLowerCase().endsWith(".txt")) {
      showToast("Please select a plain text (.txt) file.", "error");
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target.result;
      if (!content || content.trim().length === 0) {
        showToast("The selected text file is empty.", "warning");
        return;
      }

      // Update UI
      fileName.textContent = file.name;
      const sizeKb = (file.size / 1024).toFixed(1);
      const words = content.trim().split(/\s+/).length;
      fileSize.textContent = `${sizeKb} KB • ${words.toLocaleString()} words`;

      dropzone.style.display = "none";
      fileCard.style.display = "flex";

      // Populate textarea & state
      textarea.value = content;
      textarea.dispatchEvent(new Event("input"));

      // Pre-fill lecture title from filename if empty
      const titleInput = document.getElementById("lectureTitle");
      if (!titleInput.value) {
        titleInput.value = file.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
      }

      showToast(`Loaded ${file.name} successfully.`, "success");
    };

    reader.onerror = () => {
      showToast("Failed to read file. Please ensure it is UTF-8 encoded.", "error");
    };

    reader.readAsText(file, "UTF-8");
  }

  replaceBtn.addEventListener("click", () => fileInput.click());

  removeBtn.addEventListener("click", () => {
    fileInput.value = "";
    fileCard.style.display = "none";
    dropzone.style.display = "block";
    textarea.value = "";
    textarea.dispatchEvent(new Event("input"));
    showToast("Uploaded text file removed.", "info");
  });
}

/* ==========================================================================
   Option 3: Audio File Upload & Transcription
   ========================================================================== */
function initAudioUpload() {
  const dropzone = document.getElementById("audioDropzone");
  const fileInput = document.getElementById("audioFileInput");
  const browseBtn = document.getElementById("browseAudioBtn");
  const fileCard = document.getElementById("audioFileInfoCard");
  const fileName = document.getElementById("audioFileName");
  const fileSize = document.getElementById("audioFileSize");
  const removeBtn = document.getElementById("removeAudioBtn");
  const transcribeBtn = document.getElementById("transcribeBtn");
  const progressBox = document.getElementById("transcribeProgress");
  const stepMsg = document.getElementById("transcribeStepMsg");
  const reviewBox = document.getElementById("transcribedReviewBox");
  const reviewText = document.getElementById("audioExtractedText");
  const reviewMeta = document.getElementById("transcribedMeta");
  const useTranscriptBtn = document.getElementById("useAudioTranscriptBtn");
  const textarea = document.getElementById("transcriptText");

  browseBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files.length) {
      handleAudioFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) {
      handleAudioFile(fileInput.files[0]);
    }
  });

  function handleAudioFile(file) {
    const validExts = [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".webm"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!validExts.includes(ext)) {
      showToast(`Unsupported audio format '${ext}'. Allowed: MP3, WAV, M4A, AAC, FLAC, OGG`, "error");
      return;
    }

    if (file.size > 30 * 1024 * 1024) {
      showToast("Audio file exceeds maximum size of 30MB.", "error");
      return;
    }

    currentAudioFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = `${(file.size / (1024 * 1024)).toFixed(2)} MB`;

    dropzone.style.display = "none";
    fileCard.style.display = "flex";
    reviewBox.style.display = "none";

    showToast(`Ready to transcribe: ${file.name}`, "info");
  }

  removeBtn.addEventListener("click", () => {
    currentAudioFile = null;
    fileInput.value = "";
    fileCard.style.display = "none";
    dropzone.style.display = "block";
    reviewBox.style.display = "none";
  });

  transcribeBtn.addEventListener("click", async () => {
    if (!currentAudioFile) {
      showToast("Please select an audio file first.", "warning");
      return;
    }

    transcribeBtn.disabled = true;
    progressBox.style.display = "block";
    stepMsg.textContent = "Uploading audio file to server...";

    const formData = new FormData();
    formData.append("audio_file", currentAudioFile);

    try {
      stepMsg.textContent = "Transcribing with Gemini Speech Model...";
      const response = await fetch("/api/transcribe", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || "Audio transcription failed.");
      }

      // Success
      progressBox.style.display = "none";
      reviewBox.style.display = "block";
      reviewText.value = data.transcript;
      reviewMeta.textContent = `Transcribed via ${data.model_used} • ${data.word_count.toLocaleString()} words`;

      // Pre-fill lecture title from audio file name if empty
      const titleInput = document.getElementById("lectureTitle");
      if (!titleInput.value) {
        titleInput.value = data.original_filename.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
      }

      showToast("Audio successfully transcribed! Review below.", "success");

    } catch (err) {
      progressBox.style.display = "none";
      showToast(err.message, "error");
    } finally {
      transcribeBtn.disabled = false;
    }
  });

  useTranscriptBtn.addEventListener("click", () => {
    const text = reviewText.value.trim();
    if (!text) {
      showToast("Transcript is empty.", "warning");
      return;
    }

    // Set transcript in textarea & state
    textarea.value = text;
    textarea.dispatchEvent(new Event("input"));

    // Switch to paste tab to view
    const pasteTabBtn = document.querySelector('[data-input-tab="tab-paste"]');
    if (pasteTabBtn) pasteTabBtn.click();

    showToast("Transcript copied to workspace. You can now generate notes!", "success");
  });
}

/* ==========================================================================
   Notes Generation Controller
   ========================================================================== */
function initNotesGenerator() {
  const generateBtn = document.getElementById("generateNotesBtn");
  const generateBtnText = document.getElementById("generateBtnText");
  const progressBox = document.getElementById("notesGenerationProgress");
  const stepMsg = document.getElementById("notesStepMsg");
  const resetBtn = document.getElementById("resetWorkspaceBtn");

  generateBtn.addEventListener("click", async () => {
    const transcript = currentTranscript.trim();
    if (!transcript) {
      showToast("Please paste a transcript, upload a .txt file, or transcribe audio first.", "warning");
      document.getElementById("transcriptText").focus();
      return;
    }

    if (transcript.length < 20) {
      showToast("Transcript is too short. Please provide at least 20 characters.", "warning");
      return;
    }

    // Read preferences
    const title = document.getElementById("lectureTitle").value.trim();
    const subject = document.getElementById("lectureSubject").value.trim();
    const language = document.getElementById("outputLanguage").value;
    const detailLevel = document.querySelector('input[name="detailLevel"]:checked')?.value || "standard";

    const preferences = {
      include_key_terms: document.getElementById("prefKeyTerms").checked,
      include_examples_formulas: document.getElementById("prefExamples").checked,
      include_questions: document.getElementById("prefQuestions").checked,
      include_flashcards: document.getElementById("prefFlashcards").checked,
    };

    // UI Loading State
    isGenerating = true;
    generateBtn.disabled = true;
    generateBtnText.textContent = "Synthesizing Notes...";
    progressBox.style.display = "block";
    stepMsg.textContent = "Sending transcript to Gemini 2.5 Flash...";

    // Dynamic step messages
    const stepInterval = setInterval(() => {
      const msgs = [
        "Analyzing lecture structure and key themes...",
        "Synthesizing hierarchical headings & concepts...",
        "Formulating exam questions & flashcards...",
        "Finalizing structured study notes..."
      ];
      const randomMsg = msgs[Math.floor(Math.random() * msgs.length)];
      stepMsg.textContent = randomMsg;
    }, 2500);

    try {
      const response = await fetch("/api/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript,
          title,
          subject,
          language,
          detail_level: detailLevel,
          preferences,
        }),
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || "Failed to generate study notes.");
      }

      currentNotes = data.notes;
      renderNotes(data.notes);

      showToast("Study notes generated successfully!", "success");

      // Scroll to results
      const resultsContainer = document.getElementById("notesContainer");
      if (resultsContainer) {
        resultsContainer.scrollIntoView({ behavior: "smooth" });
      }

    } catch (err) {
      showToast(err.message, "error");
    } finally {
      clearInterval(stepInterval);
      isGenerating = false;
      generateBtn.disabled = false;
      generateBtnText.textContent = "Generate Smart Notes";
      progressBox.style.display = "none";
    }
  });

  resetBtn.addEventListener("click", () => {
    if (currentNotes || currentTranscript) {
      showConfirmModal(
        "Reset Workspace?",
        "This will clear the current transcript, preferences, and generated notes.",
        () => {
          document.getElementById("transcriptText").value = "";
          document.getElementById("transcriptText").dispatchEvent(new Event("input"));
          document.getElementById("lectureTitle").value = "";
          document.getElementById("lectureSubject").value = "";
          document.getElementById("outputLanguage").value = "auto";
          document.querySelector('input[name="detailLevel"][value="standard"]').checked = true;
          document.getElementById("prefKeyTerms").checked = true;
          document.getElementById("prefExamples").checked = true;
          document.getElementById("prefQuestions").checked = true;
          document.getElementById("prefFlashcards").checked = true;

          const notesContainer = document.getElementById("notesContainer");
          if (notesContainer) notesContainer.style.display = "none";
          currentNotes = null;

          showToast("Workspace reset to initial state.", "info");
        }
      );
    } else {
      showToast("Workspace is already empty.", "info");
    }
  });
}

/* ==========================================================================
   Render Generated Notes
   ========================================================================== */
function renderNotes(notes) {
  const container = document.getElementById("notesContainer");
  if (!container) return;

  // Header badges & Title
  document.getElementById("resultTitle").textContent = notes.title || "Lecture Study Notes";
  document.getElementById("resultSubjectBadge").textContent = notes.subject || "General Studies";
  
  const meta = notes.metadata || {};
  document.getElementById("resultLangBadge").textContent = `Language: ${(meta.language || "Auto").toUpperCase()}`;
  document.getElementById("resultDetailBadge").textContent = `${(meta.detail_level || "Standard").toUpperCase()} DETAIL`;
  document.getElementById("resultWordCountBadge").textContent = `${(meta.transcript_word_count || 0).toLocaleString()} words processed`;

  // Overview & Executive Summary
  const overviewCard = document.getElementById("overviewCard");
  const overviewText = document.getElementById("overviewText");
  if (notes.overview) {
    overviewText.textContent = notes.overview;
    overviewCard.style.display = "block";
  } else {
    overviewCard.style.display = "none";
  }

  const execSummaryCard = document.getElementById("execSummaryCard");
  const execSummaryText = document.getElementById("execSummaryText");
  if (notes.executive_summary) {
    execSummaryText.textContent = notes.executive_summary;
    execSummaryCard.style.display = "block";
  } else {
    execSummaryCard.style.display = "none";
  }

  // Structured Notes
  const structuredList = document.getElementById("structuredNotesList");
  structuredList.innerHTML = "";
  const structuredSection = document.getElementById("structuredNotesSection");

  if (notes.structured_notes && notes.structured_notes.length > 0) {
    structuredSection.style.display = "block";
    notes.structured_notes.forEach((sec, idx) => {
      const card = document.createElement("div");
      card.className = "note-topic-card open"; // Default open

      const bulletsHtml = (sec.bullet_points || [])
        .map(b => `<li>${escapeHtml(b)}</li>`)
        .join("");

      card.innerHTML = `
        <div class="note-topic-header" tabindex="0" role="button" aria-expanded="true">
          <div class="note-topic-title-group">
            <h4>${escapeHtml(sec.heading || `Topic ${idx + 1}`)}</h4>
            ${sec.subheading ? `<div class="note-topic-sub">${escapeHtml(sec.subheading)}</div>` : ""}
          </div>
          <svg class="chevron-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
        <div class="note-topic-body">
          ${sec.content ? `<p class="note-topic-content">${escapeHtml(sec.content)}</p>` : ""}
          ${bulletsHtml ? `<ul class="note-bullets-list">${bulletsHtml}</ul>` : ""}
        </div>
      `;

      // Accordion click handler
      const header = card.querySelector(".note-topic-header");
      header.addEventListener("click", () => {
        card.classList.toggle("open");
        header.setAttribute("aria-expanded", card.classList.contains("open"));
      });
      header.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          header.click();
        }
      });

      structuredList.appendChild(card);
    });
  } else {
    structuredSection.style.display = "none";
  }

  // Key Concepts
  const conceptsSection = document.getElementById("keyConceptsSection");
  const conceptsList = document.getElementById("keyConceptsList");
  conceptsList.innerHTML = "";

  if (notes.key_concepts && notes.key_concepts.length > 0) {
    conceptsSection.style.display = "block";
    notes.key_concepts.forEach(item => {
      const card = document.createElement("div");
      card.className = "concept-card";
      card.innerHTML = `
        <div class="concept-title">${escapeHtml(item.concept)}</div>
        <div class="concept-desc">${escapeHtml(item.simple_explanation)}</div>
      `;
      conceptsList.appendChild(card);
    });
  } else {
    conceptsSection.style.display = "none";
  }

  // Key Terms
  const termsSection = document.getElementById("keyTermsSection");
  const termsBody = document.getElementById("keyTermsTableBody");
  termsBody.innerHTML = "";

  if (notes.key_terms && notes.key_terms.length > 0) {
    termsSection.style.display = "block";
    notes.key_terms.forEach(t => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><span class="term-highlight">${escapeHtml(t.term)}</span></td>
        <td>${escapeHtml(t.definition)}</td>
      `;
      termsBody.appendChild(tr);
    });
  } else {
    termsSection.style.display = "none";
  }

  // Examples & Formulas
  const examplesSection = document.getElementById("examplesSection");
  const examplesList = document.getElementById("examplesList");
  examplesList.innerHTML = "";

  if (notes.examples_and_formulas && notes.examples_and_formulas.length > 0) {
    examplesSection.style.display = "block";
    notes.examples_and_formulas.forEach(ex => {
      const card = document.createElement("div");
      card.className = "example-card";
      card.innerHTML = `
        <div class="example-header">
          <span class="badge badge-accent">${escapeHtml((ex.type || "Example").toUpperCase())}</span>
          <strong>${escapeHtml(ex.title || "Example")}</strong>
        </div>
        ${ex.content ? `<pre class="example-code-block"><code>${escapeHtml(ex.content)}</code></pre>` : ""}
        ${ex.explanation ? `<div class="example-explanation">${escapeHtml(ex.explanation)}</div>` : ""}
      `;
      examplesList.appendChild(card);
    });
  } else {
    examplesSection.style.display = "none";
  }

  // Facts
  const factsSection = document.getElementById("factsSection");
  const factsList = document.getElementById("factsList");
  factsList.innerHTML = "";

  if (notes.important_facts && notes.important_facts.length > 0) {
    factsSection.style.display = "block";
    notes.important_facts.forEach((fact, idx) => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="fact-index">[${idx + 1}]</span> ${escapeHtml(fact)}`;
      factsList.appendChild(li);
    });
  } else {
    factsSection.style.display = "none";
  }

  // Revision Summary
  const revisionSection = document.getElementById("revisionSection");
  const revisionText = document.getElementById("revisionText");
  if (notes.revision_summary) {
    revisionSection.style.display = "block";
    revisionText.textContent = notes.revision_summary;
  } else {
    revisionSection.style.display = "none";
  }

  // Flashcards Setup
  renderFlashcards(notes.flashcards || []);

  // Questions Setup
  renderQuestions(notes.exam_questions || []);

  // Display container
  container.style.display = "block";

  // Default to study notes tab
  const defaultTab = document.querySelector('.study-tab-btn[data-tab="tab-study-notes"]');
  if (defaultTab) defaultTab.click();
}

/* ==========================================================================
   Toggle All Sections Accordion
   ========================================================================== */
document.addEventListener("DOMContentLoaded", () => {
  const toggleBtn = document.getElementById("toggleAllSectionsBtn");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const cards = document.querySelectorAll(".note-topic-card");
      const anyOpen = Array.from(cards).some(c => c.classList.contains("open"));

      cards.forEach(c => {
        if (anyOpen) {
          c.classList.remove("open");
        } else {
          c.classList.add("open");
        }
      });

      toggleBtn.textContent = anyOpen ? "Expand All" : "Collapse All";
    });
  }
});

/* ==========================================================================
   Study Tabs Switching (Notes vs Flashcards vs Questions)
   ========================================================================== */
function initStudyTabs() {
  const studyTabs = document.querySelectorAll(".study-tab-btn");
  const tabContents = document.querySelectorAll(".study-tab-content");

  studyTabs.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-tab");

      studyTabs.forEach(b => b.classList.remove("active"));
      tabContents.forEach(c => c.classList.remove("active"));

      btn.classList.add("active");
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add("active");
    });
  });
}

/* ==========================================================================
   Interactive 3D Flashcards Controller
   ========================================================================== */
function initFlashcards() {
  const flipCard = document.getElementById("activeFlipCard");
  const flipBtn = document.getElementById("flipCardBtn");
  const prevBtn = document.getElementById("prevCardBtn");
  const nextBtn = document.getElementById("nextCardBtn");

  const modeCarouselBtn = document.getElementById("fcModeCarouselBtn");
  const modeGridBtn = document.getElementById("fcModeGridBtn");
  const carouselContainer = document.getElementById("fcCarouselContainer");
  const gridContainer = document.getElementById("fcGridContainer");

  function toggleFlip() {
    if (flipCard) flipCard.classList.toggle("flipped");
  }

  if (flipCard) {
    flipCard.addEventListener("click", toggleFlip);
    flipCard.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleFlip();
      }
    });
  }

  if (flipBtn) flipBtn.addEventListener("click", toggleFlip);

  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      if (!currentNotes || !currentNotes.flashcards || currentNotes.flashcards.length === 0) return;
      if (activeFlashcardIndex > 0) {
        activeFlashcardIndex--;
        updateActiveCard();
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      if (!currentNotes || !currentNotes.flashcards || currentNotes.flashcards.length === 0) return;
      if (activeFlashcardIndex < currentNotes.flashcards.length - 1) {
        activeFlashcardIndex++;
        updateActiveCard();
      }
    });
  }

  // View Mode Switching
  modeCarouselBtn.addEventListener("click", () => {
    modeCarouselBtn.classList.add("active");
    modeGridBtn.classList.remove("active");
    carouselContainer.style.display = "block";
    gridContainer.style.display = "none";
  });

  modeGridBtn.addEventListener("click", () => {
    modeGridBtn.classList.add("active");
    modeCarouselBtn.classList.remove("active");
    carouselContainer.style.display = "none";
    gridContainer.style.display = "grid";
  });
}

function renderFlashcards(cards) {
  const countBadge = document.getElementById("flashcardsCount");
  const totalCount = document.getElementById("totalCardsCount");
  const gridContainer = document.getElementById("fcGridContainer");
  const tabBtn = document.getElementById("tabFlashcardsBtn");

  countBadge.textContent = cards.length;
  totalCount.textContent = cards.length;

  if (cards.length === 0) {
    tabBtn.style.display = "none";
    return;
  }
  tabBtn.style.display = "inline-flex";

  activeFlashcardIndex = 0;
  updateActiveCard();

  // Populate Grid
  gridContainer.innerHTML = "";
  cards.forEach((card, idx) => {
    const item = document.createElement("div");
    item.className = "fc-grid-item";
    item.innerHTML = `
      <div class="card-category-pill" style="margin-bottom: 0.5rem;">${escapeHtml(card.category || `Card ${idx + 1}`)}</div>
      <div class="fc-grid-front">${escapeHtml(card.front)}</div>
      <div class="fc-grid-back">${escapeHtml(card.back)}</div>
    `;
    gridContainer.appendChild(item);
  });
}

function updateActiveCard() {
  const flipCard = document.getElementById("activeFlipCard");
  const catPill = document.getElementById("cardCategory");
  const frontText = document.getElementById("cardFrontText");
  const backText = document.getElementById("cardBackText");
  const currentIndex = document.getElementById("currentCardIndex");
  const prevBtn = document.getElementById("prevCardBtn");
  const nextBtn = document.getElementById("nextCardBtn");

  if (!currentNotes || !currentNotes.flashcards || currentNotes.flashcards.length === 0) return;

  const card = currentNotes.flashcards[activeFlashcardIndex];
  if (!card) return;

  // Reset flip
  if (flipCard) flipCard.classList.remove("flipped");

  catPill.textContent = card.category || "General";
  frontText.textContent = card.front || "";
  backText.textContent = card.back || "";
  currentIndex.textContent = activeFlashcardIndex + 1;

  if (prevBtn) prevBtn.disabled = activeFlashcardIndex === 0;
  if (nextBtn) nextBtn.disabled = activeFlashcardIndex === currentNotes.flashcards.length - 1;
}

/* ==========================================================================
   Exam Questions Controller
   ========================================================================== */
function initExamQuestions() {
  const revealAllBtn = document.getElementById("revealAllAnswersBtn");
  if (revealAllBtn) {
    revealAllBtn.addEventListener("click", () => {
      const cards = document.querySelectorAll(".question-accordion-card");
      const anyOpen = Array.from(cards).some(c => c.classList.contains("open"));

      cards.forEach(c => {
        if (anyOpen) {
          c.classList.remove("open");
        } else {
          c.classList.add("open");
        }
      });

      revealAllBtn.textContent = anyOpen ? "Reveal All Answers" : "Hide All Answers";
    });
  }
}

function renderQuestions(questions) {
  const countBadge = document.getElementById("questionsCount");
  const list = document.getElementById("questionsList");
  const tabBtn = document.getElementById("tabQuestionsBtn");

  countBadge.textContent = questions.length;
  list.innerHTML = "";

  if (questions.length === 0) {
    tabBtn.style.display = "none";
    return;
  }
  tabBtn.style.display = "inline-flex";

  questions.forEach((q, idx) => {
    const card = document.createElement("div");
    card.className = "question-accordion-card";

    const diff = q.difficulty || "Standard";
    const badgeColor = diff.toLowerCase() === "hard" ? "badge-warning" : "badge-accent";

    card.innerHTML = `
      <div class="question-header" tabindex="0" role="button" aria-expanded="false">
        <div class="question-title-group">
          <span class="badge ${badgeColor}">${escapeHtml(diff)}</span>
          <h4>Q${idx + 1}: ${escapeHtml(q.question)}</h4>
        </div>
        <svg class="chevron-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </div>
      <div class="question-body">
        <div class="question-answer-box">
          <strong>Model Answer:</strong><br>
          ${escapeHtml(q.answer)}
        </div>
      </div>
    `;

    const header = card.querySelector(".question-header");
    header.addEventListener("click", () => {
      card.classList.toggle("open");
      header.setAttribute("aria-expanded", card.classList.contains("open"));
    });
    header.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        header.click();
      }
    });

    list.appendChild(card);
  });
}

/* ==========================================================================
   Export Handlers (.md, .txt, .pdf)
   ========================================================================== */
function initExports() {
  const exportMdBtn = document.getElementById("exportMdBtn");
  const exportTxtBtn = document.getElementById("exportTxtBtn");
  const exportPdfBtn = document.getElementById("exportPdfBtn");
  const editTranscriptBtn = document.getElementById("editTranscriptBtn");
  const clearNotesBtn = document.getElementById("clearNotesBtn");

  async function triggerExport(format, btn) {
    if (!currentNotes) {
      showToast("No notes available to export.", "warning");
      return;
    }

    const origText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-sm"></span> Exporting...`;

    try {
      const response = await fetch("/api/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          notes: currentNotes,
          format: format,
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || `Failed to export ${format.toUpperCase()}`);
      }

      // Extract filename from Content-Disposition header if available
      let filename = `lecture_notes.${format}`;
      const disposition = response.headers.get("Content-Disposition");
      if (disposition && disposition.indexOf("filename=") !== -1) {
        const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
        if (matches != null && matches[1]) {
          filename = matches[1].replace(/['"]/g, "");
        }
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);

      showToast(`Exported ${filename} successfully.`, "success");

    } catch (err) {
      showToast(err.message, "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }

  if (exportMdBtn) {
    exportMdBtn.addEventListener("click", () => triggerExport("md", exportMdBtn));
  }

  if (exportTxtBtn) {
    exportTxtBtn.addEventListener("click", () => triggerExport("txt", exportTxtBtn));
  }

  if (exportPdfBtn) {
    exportPdfBtn.addEventListener("click", () => triggerExport("pdf", exportPdfBtn));
  }

  if (editTranscriptBtn) {
    editTranscriptBtn.addEventListener("click", () => {
      const studio = document.getElementById("studio");
      if (studio) studio.scrollIntoView({ behavior: "smooth" });
      document.getElementById("transcriptText").focus();
    });
  }

  if (clearNotesBtn) {
    clearNotesBtn.addEventListener("click", () => {
      showConfirmModal(
        "Clear Study Notes?",
        "This will remove the currently generated notes and flashcards from your screen. You will need to regenerate them if needed.",
        () => {
          const container = document.getElementById("notesContainer");
          if (container) container.style.display = "none";
          currentNotes = null;
          showToast("Study notes cleared.", "info");
        }
      );
    });
  }
}

/* ==========================================================================
   Confirmation Modal Controller
   ========================================================================== */
let confirmCallback = null;

function initModal() {
  const modal = document.getElementById("confirmModal");
  const cancelBtn = document.getElementById("modalCancelBtn");
  const confirmBtn = document.getElementById("modalConfirmBtn");

  function closeModal() {
    modal.style.display = "none";
    confirmCallback = null;
  }

  if (cancelBtn) cancelBtn.addEventListener("click", closeModal);

  if (confirmBtn) {
    confirmBtn.addEventListener("click", () => {
      if (confirmCallback) confirmCallback();
      closeModal();
    });
  }

  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });
}

function showConfirmModal(title, message, onConfirm) {
  const modal = document.getElementById("confirmModal");
  const titleEl = document.getElementById("modalTitle");
  const msgEl = document.getElementById("modalMessage");

  titleEl.textContent = title;
  msgEl.textContent = message;
  confirmCallback = onConfirm;
  modal.style.display = "flex";
}
