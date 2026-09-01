// AI Resume Assistant - Modern SaaS JavaScript
// ============================================
// Client-side logic driving the entire AI Resume Assistant UI.
// Responsibilities:
//   - Smooth-scroll navigation with scroll-spy active state
//   - Resume file upload (click + drag-and-drop) to /api/upload-resume
//   - Resume ATS analysis flow with animated progress + score display
//   - RAG chat with the backend /api/rag-chat endpoint
//   - Job search via /api/job-search and one-click resume tailoring via
//     /api/tailor-resume (renders tailored resume + cover letter preview)
// All API contracts come from the shared backend and are preserved unchanged.

let currentResumeId = null;
let currentResumeName = null;

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    initializeFileUpload();
    initializeAnalyzeButton();
    initializeNavLinks();
});

// ============================================
// NAVIGATION
// ============================================

function initializeNavLinks() {
    const links = document.querySelectorAll('.nav-link[data-section]');
    const sections = [];
    links.forEach(function(link) {
        var target = document.getElementById(link.dataset.section);
        if (target) sections.push({ id: link.dataset.section, el: target, link: link });
    });

    // smooth scroll on click
    links.forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            var target = document.getElementById(link.dataset.section);
            if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });

    // scroll-spy: update active link based on which section is visible
    var observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                links.forEach(function(l) { l.classList.remove('active'); });
                var match = sections.find(function(s) { return s.el === entry.target; });
                if (match) match.link.classList.add('active');
            }
        });
    }, { rootMargin: '-80px 0px -40% 0px', threshold: 0 });

    sections.forEach(function(s) { observer.observe(s.el); });
}

// ============================================
// FILE UPLOAD
// ============================================

function initializeFileUpload() {
    const fileInput = document.getElementById('resumeFile');
    const uploadArea = document.getElementById('uploadArea');

    fileInput.addEventListener('change', function(e) {
        const file = this.files[0];
        if (file) {
            uploadResume(file);
        }
    });

    // Drag and drop handlers
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0 && files[0].type === 'application/pdf') {
            uploadResume(files[0]);
        } else {
            showStatus('uploadStatus', 'Please upload a PDF file', 'error');
        }
    });

    uploadArea.addEventListener('click', function() {
        document.getElementById('resumeFile').click();
    });
}

function initializeAnalyzeButton() {
    const analyzeBtn = document.getElementById('analyzeBtn');
    const jobDescription = document.getElementById('jobDescription');

    jobDescription.addEventListener('input', function() {
        if (currentResumeId && this.value.trim()) {
            analyzeBtn.disabled = false;
        } else {
            analyzeBtn.disabled = true;
        }
    });
}

async function uploadResume(file) {
    const statusDiv = document.getElementById('uploadStatus');
    const resumeInfo = document.getElementById('resumeInfo');

    showStatus('uploadStatus', 'Uploading your resume...', 'info');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload-resume', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            currentResumeId = data.resume_id;
            currentResumeName = data.filename;

            document.getElementById('resumeName').textContent = data.filename;
            document.getElementById('resumeId').textContent = `ID: ${data.resume_id.substring(0, 8)}`;
            resumeInfo.classList.remove('hidden');

            showStatus('uploadStatus', 'Resume uploaded successfully', 'success');

            // Enable analyze button if job description is filled
            const jobDescription = document.getElementById('jobDescription');
            if (jobDescription.value.trim()) {
                document.getElementById('analyzeBtn').disabled = false;
            }

            // Auto-hide success message
            setTimeout(() => {
                statusDiv.classList.remove('visible');
            }, 5000);
        } else {
            showStatus('uploadStatus', data.detail || 'Upload failed', 'error');
        }
    } catch (error) {
        showStatus('uploadStatus', 'Error uploading file: ' + error.message, 'error');
    }
}

// ============================================
// RESUME ANALYSIS
// ============================================

async function analyzeResume() {
    if (!currentResumeId) {
        alert('Please upload a resume first');
        return;
    }

    const jobDescription = document.getElementById('jobDescription').value.trim();
    if (!jobDescription) {
        alert('Please enter a job description');
        return;
    }

    const btn = document.getElementById('analyzeBtn');
    const progressCard = document.getElementById('analysisProgress');

    // Show progress
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Analyzing...';
    progressCard.classList.remove('hidden');

    // Animate progress messages
    const progressSteps = [
        'Extracting resume information...',
        'Analyzing ATS compatibility...',
        'Comparing skills with job requirements...',
        'Generating recommendations...',
        'Preparing interview questions...'
    ];

    let currentStep = 0;
    const progressInterval = setInterval(() => {
        if (currentStep < progressSteps.length) {
            document.getElementById('progressText').textContent = progressSteps[currentStep];
            currentStep++;
        }
    }, 1000);

    const formData = new FormData();
    formData.append('resume_id', currentResumeId);
    formData.append('job_description', jobDescription);

    try {
        const response = await fetch('/api/analyze-resume', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        clearInterval(progressInterval);
        progressCard.classList.add('hidden');

        if (data.success) {
            displayResults(data);
            document.getElementById('resultsSection').classList.remove('hidden');

            // Smooth scroll to results
            setTimeout(() => {
                document.getElementById('resultsSection').scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }, 300);
        } else {
            alert('Error: ' + (data.detail || 'Analysis failed'));
        }
    } catch (error) {
        clearInterval(progressInterval);
        progressCard.classList.add('hidden');
        alert('Error analyzing resume: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Analyze Resume';
    }
}

function displayResults(data) {
    // Animate ATS Score
    animateScore(data.ats_score);

    // Display matched and missing skills
    document.getElementById('matchedSkills').textContent = data.matched_skills.join(', ') || 'None';
    document.getElementById('missingSkills').textContent = data.missing_skills.join(', ') || 'None';
    document.getElementById('skillPercentage').textContent = data.skill_percentage + '%';

    // Display suggestions
    const suggestionList = document.getElementById('suggestionList');
    suggestionList.innerHTML = '';
    data.improvement_suggestions.forEach((suggestion, index) => {
        const li = document.createElement('li');
        li.style.cssText = 'padding: var(--space-3); margin-bottom: var(--space-2); background: var(--bg-secondary); border-left: 2px solid var(--primary-600); border-radius: var(--radius-md); font-size: var(--text-sm); color: var(--text-secondary); opacity: 0; animation: slideIn 0.3s forwards;';
        li.style.animationDelay = `${index * 0.05}s`;
        li.textContent = suggestion;
        suggestionList.appendChild(li);
    });

    // Display candidate summary
    const summary = data.candidate_summary;
    document.getElementById('profSummary').textContent = summary.professional_summary || 'Not available';
    document.getElementById('expSummary').textContent = summary.experience_summary || 'Not available';

    // Display key skills as tags
    const keySkillsDiv = document.getElementById('keySkills');
    keySkillsDiv.innerHTML = '';
    if (summary.key_technical_skills && summary.key_technical_skills.length > 0) {
        summary.key_technical_skills.forEach((skill, index) => {
            const tag = document.createElement('span');
            tag.className = 'skill-tag';
            tag.textContent = skill;
            tag.style.opacity = '0';
            tag.style.animation = 'fadeIn 0.3s forwards';
            tag.style.animationDelay = `${index * 0.03}s`;
            keySkillsDiv.appendChild(tag);
        });
    } else {
        keySkillsDiv.innerHTML = '<span style="color: var(--text-tertiary); font-size: var(--text-sm);">No key skills listed</span>';
    }

    // Display strengths
    const strengthsList = document.getElementById('strengthsList');
    strengthsList.innerHTML = '';
    if (summary.strengths && summary.strengths.length > 0) {
        summary.strengths.forEach(item => {
            const li = document.createElement('li');
            li.style.cssText = 'padding: var(--space-2) 0; font-size: var(--text-sm); color: var(--text-secondary); border-bottom: 1px solid var(--border-primary);';
            li.textContent = item;
            strengthsList.appendChild(li);
        });
    }

    // Display weaknesses
    const weaknessesList = document.getElementById('weaknessesList');
    weaknessesList.innerHTML = '';
    if (summary.weaknesses && summary.weaknesses.length > 0) {
        summary.weaknesses.forEach(item => {
            const li = document.createElement('li');
            li.style.cssText = 'padding: var(--space-2) 0; font-size: var(--text-sm); color: var(--text-secondary); border-bottom: 1px solid var(--border-primary);';
            li.textContent = item;
            weaknessesList.appendChild(li);
        });
    }

    // Display hiring recommendation
    const recommendationEl = document.getElementById('recommendation');
    const recText = summary.hiring_recommendation || 'Recommended';
    recommendationEl.textContent = recText;
    recommendationEl.style.color = recText.toLowerCase().includes('not') ? 'var(--error)' : 'var(--success)';

    // Display interview questions
    displayInterviewQuestions(data.interview_questions);
}

function animateScore(score) {
    const scoreElement = document.getElementById('atsScore');
    const scoreFill = document.getElementById('scoreFill');

    // Animate the number
    let currentScore = 0;
    const duration = 1500;
    const increment = score / (duration / 16);

    const timer = setInterval(() => {
        currentScore += increment;
        if (currentScore >= score) {
            currentScore = score;
            clearInterval(timer);
        }
        scoreElement.textContent = Math.round(currentScore);
    }, 16);

    // Animate the circle
    const circumference = 2 * Math.PI * 52;
    const offset = circumference - (score / 100) * circumference;

    setTimeout(() => {
        scoreFill.style.strokeDashoffset = offset;
    }, 100);
}

function displayInterviewQuestions(questions) {
    const techList = document.getElementById('techQuestionsList');
    techList.innerHTML = '';
    if (questions.technical_questions) {
        questions.technical_questions.forEach((q, i) => {
            const li = document.createElement('li');
            li.style.cssText = 'padding: var(--space-4); margin-bottom: var(--space-3); background: var(--bg-secondary); border: 1px solid var(--border-primary); border-radius: var(--radius-md); font-size: var(--text-sm); color: var(--text-primary);';
            li.innerHTML = `<strong style="color: var(--text-primary);">${i + 1}.</strong> ${q}`;
            techList.appendChild(li);
        });
    }

    const behavioralList = document.getElementById('behavioralQuestionsList');
    behavioralList.innerHTML = '';
    if (questions.behavioral_questions) {
        questions.behavioral_questions.forEach((q, i) => {
            const li = document.createElement('li');
            li.style.cssText = 'padding: var(--space-4); margin-bottom: var(--space-3); background: var(--bg-secondary); border: 1px solid var(--border-primary); border-radius: var(--radius-md); font-size: var(--text-sm); color: var(--text-primary);';
            li.innerHTML = `<strong style="color: var(--text-primary);">${i + 1}.</strong> ${q}`;
            behavioralList.appendChild(li);
        });
    }

    const scenarioList = document.getElementById('scenarioQuestionsList');
    scenarioList.innerHTML = '';
    if (questions.scenario_questions) {
        questions.scenario_questions.forEach((q, i) => {
            const li = document.createElement('li');
            li.style.cssText = 'padding: var(--space-4); margin-bottom: var(--space-3); background: var(--bg-secondary); border: 1px solid var(--border-primary); border-radius: var(--radius-md); font-size: var(--text-sm); color: var(--text-primary);';
            li.innerHTML = `<strong style="color: var(--text-primary);">${i + 1}.</strong> ${q}`;
            scenarioList.appendChild(li);
        });
    }
}

// ============================================
// TABS
// ============================================

function showTab(tab) {
    // Remove active class from all buttons and panels
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));

    // Add active class to clicked button and corresponding panel
    event.target.classList.add('active');
    document.getElementById(`${tab}Questions`).classList.add('active');
}

// ============================================
// CHAT
// ============================================

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const question = input.value.trim();

    if (!question) return;
    if (!currentResumeId) {
        alert('Please upload a resume first');
        return;
    }

    const messagesDiv = document.getElementById('chatMessages');

    // Add user message
    const userMsg = document.createElement('div');
    userMsg.className = 'chat-message chat-message-user';
    userMsg.innerHTML = `
        <div class="chat-message-avatar">You</div>
        <div class="chat-message-content">${escapeHtml(question)}</div>
    `;
    messagesDiv.appendChild(userMsg);

    input.value = '';
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    // Add loading message
    const loadingMsg = document.createElement('div');
    loadingMsg.className = 'chat-message chat-message-bot';
    loadingMsg.innerHTML = `
        <div class="chat-message-avatar">AI</div>
        <div class="chat-message-content">
            <span class="spinner"></span> Thinking...
        </div>
    `;
    messagesDiv.appendChild(loadingMsg);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    try {
        const response = await fetch('/api/rag-chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: question,
                resume_id: currentResumeId
            })
        });

        const data = await response.json();

        messagesDiv.removeChild(loadingMsg);

        if (!response.ok) {
            const botMsg = document.createElement('div');
            botMsg.className = 'chat-message chat-message-bot';
            botMsg.innerHTML = `
                <div class="chat-message-avatar">AI</div>
                <div class="chat-message-content">Sorry, something went wrong: ${escapeHtml(data.detail || 'Unknown error')}</div>
            `;
            messagesDiv.appendChild(botMsg);
        } else {
            const botMsg = document.createElement('div');
            botMsg.className = 'chat-message chat-message-bot';
            botMsg.innerHTML = `
                <div class="chat-message-avatar">AI</div>
                <div class="chat-message-content">${escapeHtml(data.answer)}</div>
            `;
            messagesDiv.appendChild(botMsg);
        }

        messagesDiv.scrollTop = messagesDiv.scrollHeight;

    } catch (error) {
        messagesDiv.removeChild(loadingMsg);
        const errorMsg = document.createElement('div');
        errorMsg.className = 'chat-message chat-message-bot';
        errorMsg.innerHTML = `
            <div class="chat-message-avatar">AI</div>
            <div class="chat-message-content">Error: ${escapeHtml(error.message)}</div>
        `;
        messagesDiv.appendChild(errorMsg);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
}

// ============================================
// JOB SEARCH
// ============================================

async function searchJobs() {
    if (!currentResumeId) {
        alert('Please upload a resume first');
        return;
    }

    const keywords = document.getElementById('jobKeywords').value.trim();
    if (!keywords) {
        alert('Please enter role or keywords to search for');
        return;
    }

    const location = document.getElementById('jobLocation').value.trim();
    const minAtsScore = parseFloat(document.getElementById('minAtsScore').value) || 0;
    const greenhouseBoards = document.getElementById('greenhouseBoards').value
        .split(',').map(s => s.trim()).filter(Boolean);
    const leverCompanies = document.getElementById('leverCompanies').value
        .split(',').map(s => s.trim()).filter(Boolean);

    const btn = document.getElementById('searchJobsBtn');
    const statusDiv = document.getElementById('jobSearchStatus');
    const resultsDiv = document.getElementById('jobResults');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Searching...';
    statusDiv.classList.remove('visible');
    resultsDiv.innerHTML = '';

    try {
        const response = await fetch('/api/job-search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                resume_id: currentResumeId,
                keywords: keywords,
                location: location,
                min_ats_score: minAtsScore,
                greenhouse_boards: greenhouseBoards.length ? greenhouseBoards : null,
                lever_companies: leverCompanies.length ? leverCompanies : null,
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Job search failed');
        }

        showStatus('jobSearchStatus', `Found ${data.total_found} postings, ${data.eligible_count} meet your ATS threshold`, 'success');

        if (data.jobs.length === 0) {
            resultsDiv.innerHTML = '<p style="text-align: center; color: var(--text-tertiary); padding: var(--space-8);">No eligible jobs found. Try lowering the min ATS score or broadening keywords.</p>';
            return;
        }

        data.jobs.forEach((job, index) => {
            const jobCard = document.createElement('div');
            jobCard.className = 'job-card';
            jobCard.style.opacity = '0';
            jobCard.style.animation = 'fadeIn 0.3s forwards';
            jobCard.style.animationDelay = `${index * 0.05}s`;

            jobCard.innerHTML = `
                <div class="job-card-header">
                    <div>
                        <h3 class="job-title">${escapeHtml(job.title)}</h3>
                        <p class="job-company">${escapeHtml(job.company)}</p>
                    </div>
                    <span class="badge badge-primary" style="font-size: var(--text-base); padding: var(--space-2) var(--space-3);">${job.ats_score}/100</span>
                </div>
                <div class="job-meta">
                    <span>${escapeHtml(job.location || 'Location not specified')}</span>
                    <span>•</span>
                    <span>${escapeHtml(job.source)}</span>
                </div>
                <div class="job-skills">
                    <div style="margin-bottom: var(--space-2);">
                        <strong style="font-size: var(--text-sm); color: var(--text-primary);">Matched Skills:</strong>
                        <span style="color: var(--text-secondary);">${job.matched_skills.slice(0, 8).join(', ') || 'None'}</span>
                    </div>
                    <div>
                        <strong style="font-size: var(--text-sm); color: var(--text-primary);">Missing Skills:</strong>
                        <span style="color: var(--text-secondary);">${job.missing_skills.slice(0, 8).join(', ') || 'None'}</span>
                    </div>
                </div>
                <div class="job-actions">
                    <button class="btn btn-primary" onclick='tailorForJob(${JSON.stringify(job).replace(/'/g, "&#39;")})'>Tailor Resume</button>
                    ${job.url ? `<a class="btn btn-secondary" href="${job.url}" target="_blank" rel="noopener">View Posting</a>` : ''}
                </div>
            `;
            resultsDiv.appendChild(jobCard);
        });

    } catch (error) {
        showStatus('jobSearchStatus', 'Error: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Search Jobs';
    }
}

async function tailorForJob(job) {
    const card = document.getElementById('tailorResultCard');
    const container = document.getElementById('tailorResult');
    card.classList.remove('hidden');
    container.innerHTML = '<div style="text-align: center; padding: var(--space-8);"><span class="spinner spinner-lg"></span><p style="margin-top: var(--space-4); color: var(--text-secondary);">Generating tailored resume and cover letter...</p></div>';
    card.scrollIntoView({ behavior: 'smooth' });

    try {
        const response = await fetch('/api/tailor-resume', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                resume_id: currentResumeId,
                job_title: job.title,
                company: job.company,
                job_description: job.description,
                job_url: job.url,
            })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Tailoring failed');
        }

        const t = data.tailored_resume;
        container.innerHTML = `
            <div style="margin-bottom: var(--space-6); padding-bottom: var(--space-6); border-bottom: 1px solid var(--border-primary);">
                <h3 style="font-size: var(--text-xl); font-weight: var(--font-semibold); margin-bottom: var(--space-2);">${escapeHtml(data.job_title)} at ${escapeHtml(data.company)}</h3>
                <p style="color: var(--text-secondary);">
                    <strong>ATS Score:</strong> ${data.before_ats_score} → <strong style="color: var(--success);">${data.after_ats_score}</strong> after tailoring
                </p>
            </div>

            <div style="margin-bottom: var(--space-6);">
                <h4 style="font-size: var(--text-sm); font-weight: var(--font-semibold); text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-tertiary); margin-bottom: var(--space-3);">Professional Summary</h4>
                <p style="color: var(--text-secondary);">${escapeHtml(t.professional_summary || '')}</p>
            </div>

            <div style="margin-bottom: var(--space-6);">
                <h4 style="font-size: var(--text-sm); font-weight: var(--font-semibold); text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-tertiary); margin-bottom: var(--space-3);">Highlighted Skills</h4>
                <div class="skill-tags">
                    ${(t.highlighted_skills || []).map(skill => `<span class="skill-tag">${escapeHtml(skill)}</span>`).join('')}
                </div>
            </div>

            <div style="margin-bottom: var(--space-6);">
                <h4 style="font-size: var(--text-sm); font-weight: var(--font-semibold); text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-tertiary); margin-bottom: var(--space-3);">Tailored Experience</h4>
                <ul style="list-style: none; padding: 0;">
                    ${(t.tailored_experience_bullets || []).map(b => `<li style="padding: var(--space-2) 0; font-size: var(--text-sm); color: var(--text-secondary); border-bottom: 1px solid var(--border-primary);">${escapeHtml(b)}</li>`).join('')}
                </ul>
            </div>

            ${t.honesty_notes ? `<div class="status warning visible" style="margin-bottom: var(--space-6);"><strong>Note:</strong> ${escapeHtml(t.honesty_notes)}</div>` : ''}

            <div style="margin-bottom: var(--space-6);">
                <h4 style="font-size: var(--text-sm); font-weight: var(--font-semibold); text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-tertiary); margin-bottom: var(--space-3);">Cover Letter</h4>
                <p style="white-space: pre-wrap; color: var(--text-secondary); line-height: var(--leading-relaxed);">${escapeHtml(data.cover_letter || '')}</p>
            </div>

            <div class="job-actions">
                <a class="btn btn-success" href="${data.resume_download_url}">Download Resume (.docx)</a>
                <a class="btn btn-success" href="${data.cover_letter_download_url}">Download Cover Letter (.docx)</a>
                ${data.job_url ? `<a class="btn btn-secondary" href="${data.job_url}" target="_blank" rel="noopener">View Job Posting</a>` : ''}
            </div>

            <p style="margin-top: var(--space-4); font-size: var(--text-sm); color: var(--text-tertiary); text-align: center;">Review everything before submitting — nothing has been sent automatically.</p>
        `;
    } catch (error) {
        container.innerHTML = `<div class="status error visible">Error: ${escapeHtml(error.message)}</div>`;
    }
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

function showStatus(elementId, message, type) {
    const statusDiv = document.getElementById(elementId);
    statusDiv.textContent = message;
    statusDiv.className = `status ${type} visible`;

    // Auto-hide success messages
    if (type === 'success') {
        setTimeout(() => {
            statusDiv.classList.remove('visible');
        }, 5000);
    }
}

function escapeHtml(str) {
    if (str === undefined || str === null) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
