/* ===============================
   ResearchConnect — script.js
   Complete, fixed, and hardened
   =============================== */

// -------------------- Globals --------------------
let allLabs = [];
let filteredLabs = [];
let currentPage = 1;
const labsPerPage = 12;
let ragRecs = [];       // store all RAG recommendations
let ragRecIndex = 0;    // current index being displayed
// -------------------- DOM Utils --------------------
const $  = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

// -------------------- DOM Elements --------------------
const searchInput            = $('#search-input');
const schoolFilter           = $('#school-filter');
const professorFilter        = $('#professor-filter');
const labsGrid               = $('#labs-grid');
const loadMoreBtn            = $('#load-more-btn');

const majorInput             = $('#major');
const getRecommendationsBtn  = $('#get-recommendations-btn');
const recommendationsResults = $('#recommendations-results');
const recommendationsGrid    = $('#recommendations-grid');

const labModal               = $('#lab-modal');
const modalName              = $('#modal-lab-name');
const modalProfessor         = $('#modal-professor');
const modalSchool            = $('#modal-school');
const modalWebsite           = $('#modal-website');
const modalDescription       = $('#modal-description');

const ragModal               = $('#rag-modal');        // must exist in HTML
const ragModalBody           = $('#rag-modal-body');   // must exist in HTML

// RAG elements
const ragForm           = $('#rag-form');
const ragSubmitBtn      = $('#rag-submit-btn');
const ragResults        = $('#rag-results');
const ragContent        = $('#rag-content');
const ragUploadArea     = $('#upload-area');
const ragTranscriptFile = $('#transcript-file');
const ragFilePreview    = $('#file-preview');
const ragFileNameEl     = $('#rag-form .file-name');
const ragFileSizeEl     = $('#rag-form .file-size');

// -------------------- Boot --------------------
document.addEventListener('DOMContentLoaded', () => {
  initializeApp();
  setupEventListeners();
  initializeTheme();
  updateNavigation();

  // Fetch initial data
  loadLabs();
  loadSchools();

  // Animations
  animateStats();

  // RAG init (drag/drop + picker)
  initRAGUpload();
});

// -------------------- Init & Navigation --------------------
function initializeApp() {
  // Smooth scrolling for same-page anchors
  $$('a[href^="#"]').forEach(a => {
    a.addEventListener('click', (e) => {
      const target = $(a.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // Mobile nav toggle
  const navToggle = $('.nav-toggle');
  const navMenu   = $('.nav-menu');
  if (navToggle && navMenu) {
    navToggle.addEventListener('click', () => {
      navMenu.classList.toggle('active');
    });
  }
}

function updateNavigation() {
  const navLinks = $$('.nav-link');
  navLinks.forEach(link => {
    link.addEventListener('click', function (e) {
      const id = this.getAttribute('href');
      if (!id || !id.startsWith('#')) return;
      e.preventDefault();
      const targetId = id.slice(1);
      scrollToSection(targetId);

      navLinks.forEach(l => l.classList.remove('active'));
      this.classList.add('active');
    });
  });
}

// -------------------- Theme --------------------
function toggleTheme() {
  const body = document.body;
  const themeToggle = $('#theme-toggle');
  const themeIcon = themeToggle?.querySelector('i');
  const themeText = themeToggle?.querySelector('span');

  if (body.getAttribute('data-theme') === 'dark') {
    body.removeAttribute('data-theme');
    if (themeIcon) themeIcon.className = 'fas fa-moon';
    if (themeText) themeText.textContent = 'Dark Mode';
    localStorage.setItem('theme', 'light');
  } else {
    body.setAttribute('data-theme', 'dark');
    if (themeIcon) themeIcon.className = 'fas fa-sun';
    if (themeText) themeText.textContent = 'Light Mode';
    localStorage.setItem('theme', 'dark');
  }
}

function initializeTheme() {
  const savedTheme = localStorage.getItem('theme');
  const body = document.body;
  const themeToggle = $('#theme-toggle');
  const themeIcon = themeToggle?.querySelector('i');
  const themeText = themeToggle?.querySelector('span');

  if (savedTheme === 'dark') {
    body.setAttribute('data-theme', 'dark');
    if (themeIcon) themeIcon.className = 'fas fa-sun';
    if (themeText) themeText.textContent = 'Light Mode';
  } else {
    body.removeAttribute('data-theme');
    if (themeIcon) themeIcon.className = 'fas fa-moon';
    if (themeText) themeText.textContent = 'Dark Mode';
  }
}

// -------------------- Event Listeners --------------------
function setupEventListeners() {
  // Search
  if (searchInput) {
    searchInput.addEventListener('input', debounce(filterLabs, 300));
  }

  // Filters
  schoolFilter?.addEventListener('change', filterLabs);
  professorFilter?.addEventListener('change', filterLabs);

  // Load more
  loadMoreBtn?.addEventListener('click', loadMoreLabs);

  // Recommendations
  getRecommendationsBtn?.addEventListener('click', getRecommendations);

  // Lab modal close on backdrop click
  labModal?.addEventListener('click', (e) => {
    if (e.target === labModal) closeModal();
  });

  // Global ESC for Lab modal
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && labModal && labModal.style.display === 'block') {
      closeModal();
    }
  });

  // Delegate clicks on dynamically created lab cards
  labsGrid?.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-open-lab]');
    const card = e.target.closest('.lab-card');
    if (btn && card) {
      const idx = card.getAttribute('data-index');
      if (idx != null) openLabModal(parseInt(idx, 10));
      e.stopPropagation();
    } else if (card) {
      const idx = card.getAttribute('data-index');
      if (idx != null) openLabModal(parseInt(idx, 10));
    }
  });
}

// -------------------- Data Fetch --------------------
async function loadLabs() {
  try {
    const response = await fetch('/api/labs');
    if (!response.ok) throw new Error(`Failed to load labs (${response.status})`);
    allLabs = await response.json();
    filteredLabs = [...allLabs];

    // Build professor filter options from data
    populateProfessorFilter(allLabs);

    displayLabs();
  } catch (err) {
    console.error('Error loading labs:', err);
    showError('Failed to load labs. Please try again.');
  }
}

async function loadSchools() {
  try {
    const response = await fetch('/api/schools');
    if (!response.ok) throw new Error(`Failed to load schools (${response.status})`);
    const schools = await response.json();
    if (schoolFilter) {
      // Clear existing (except placeholder)
      schoolFilter.querySelectorAll('option:not([value=""])').forEach(o => o.remove());
      schools.forEach(school => {
        const option = document.createElement('option');
        option.value = school;
        option.textContent = school;
        schoolFilter.appendChild(option);
      });
    }
  } catch (err) {
    console.error('Error loading schools:', err);
  }
}

function populateProfessorFilter(labs) {
  if (!professorFilter) return;
  professorFilter.querySelectorAll('option:not([value=""])').forEach(o => o.remove());
  const profs = Array.from(new Set(labs.map(l => l.professor).filter(Boolean))).sort((a, b) =>
    a.localeCompare(b)
  );
  profs.forEach(p => {
    const option = document.createElement('option');
    option.value = p;
    option.textContent = p;
    professorFilter.appendChild(option);
  });
}

// -------------------- Rendering --------------------
function displayLabs() {
  if (!labsGrid) return;

  const startIndex = 0;
  const endIndex = currentPage * labsPerPage;
  const labsToShow = filteredLabs.slice(startIndex, endIndex);

  labsGrid.innerHTML = '';

  if (labsToShow.length === 0) {
    labsGrid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #64748b;">
        <i class="fas fa-search" style="font-size: 3rem; margin-bottom: 20px; opacity: 0.5;"></i>
        <h3>No labs found</h3>
        <p>Try adjusting your search criteria or filters</p>
      </div>
    `;
  } else {
    labsToShow.forEach((lab, i) => {
      const card = createLabCard(lab, i);
      labsGrid.appendChild(card);
    });
  }

  if (loadMoreBtn) {
    loadMoreBtn.style.display = endIndex >= filteredLabs.length ? 'none' : 'block';
  }
}

function createLabCard(lab, indexInSlice) {
  const card = document.createElement('div');
  card.className = 'lab-card';
  // indexInSlice maps to same index because we slice from 0 to endIndex
  card.setAttribute('data-index', String(indexInSlice));

  card.innerHTML = `
    <div class="lab-header">
      <div>
        <h3 class="lab-name">${escapeHtml(lab.name || '')}</h3>
        <p class="lab-professor">${escapeHtml(lab.professor || '')}</p>
      </div>
    </div>
    <p class="lab-school">${escapeHtml(lab.school || '')}</p>
    <p class="lab-description">${escapeHtml(truncateText(lab.description || '', 150))}</p>
    <div class="lab-actions">
      <button class="btn btn-primary btn-small" data-open-lab>
        <i class="fas fa-info-circle"></i>
        View Details
      </button>
    </div>
  `;
  return card;
}

// -------------------- Search & Filter --------------------
function filterLabs() {
  const searchTerm = (searchInput?.value || '').toLowerCase().trim();
  const selectedSchool = (schoolFilter?.value || '').toLowerCase().trim();
  const selectedProfessor = (professorFilter?.value || '').toLowerCase().trim();

  filteredLabs = allLabs.filter(lab => {
    const name   = (lab.name || '').toLowerCase();
    const desc   = (lab.description || '').toLowerCase();
    const prof   = (lab.professor || '').toLowerCase();
    const school = (lab.school || '').toLowerCase();

    const matchesSearch = !searchTerm || name.includes(searchTerm) || desc.includes(searchTerm) || prof.includes(searchTerm) || school.includes(searchTerm);
    const matchesSchool = !selectedSchool || school === selectedSchool || school.includes(selectedSchool);
    const matchesProfessor = !selectedProfessor || prof === selectedProfessor || prof.includes(selectedProfessor);

    return matchesSearch && matchesSchool && matchesProfessor;
  });

  currentPage = 1;
  displayLabs();
}

function loadMoreLabs() {
  currentPage++;
  displayLabs();
}

// -------------------- Lab Modal --------------------
function openLabModal(indexOrLab) {
  let lab = indexOrLab;
  if (typeof indexOrLab === 'number') {
    lab = filteredLabs[indexOrLab];
  }
  if (!lab || !labModal) return;

  if (modalName)        modalName.textContent = lab.name || '';
  if (modalProfessor)   modalProfessor.textContent = lab.professor || '';
  if (modalSchool)      modalSchool.textContent = lab.school || '';
  if (modalWebsite)     modalWebsite.href = lab.url || '#';
  if (modalDescription) modalDescription.textContent = lab.description || '';

  labModal.style.display = 'block';
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  if (!labModal) return;
  labModal.style.display = 'none';
  document.body.style.overflow = 'auto';
}

// -------------------- Contact (placeholder) --------------------
function contactLab() {
  alert('Contact functionality would be implemented here. This could open an email client or contact form.');
}

// -------------------- Basic Recommendations --------------------
async function getRecommendations() {
  const major = (majorInput?.value || '').trim();
  const interests = $$('input[type="checkbox"]:checked').map(cb => cb.value);

  if (!major) { alert('Please enter your major to get recommendations.'); return; }
  if (interests.length === 0) { alert('Please select at least one research interest.'); return; }

  try {
    if (getRecommendationsBtn) {
      getRecommendationsBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Finding Your Perfect Labs...';
      getRecommendationsBtn.disabled = true;
    }

    const resp = await fetch('/api/recommendations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ major, interests }),
    });

    const data = await resp.json();
    if (!resp.ok || data.error) {
      throw new Error(data.error || `Failed (${resp.status})`);
    }

    displayRecommendations(data.recommendations || []);
    if (recommendationsResults) {
      recommendationsResults.style.display = 'block';
      recommendationsResults.scrollIntoView({ behavior: 'smooth' });
    }
  } catch (err) {
    console.error('Error getting recommendations:', err);
    showError('Failed to get recommendations. Please try again.');
  } finally {
    if (getRecommendationsBtn) {
      getRecommendationsBtn.innerHTML = '<i class="fas fa-magic"></i> Find My Perfect Labs';
      getRecommendationsBtn.disabled = false;
    }
  }
}

function displayRecommendations(recommendations) {
  if (!recommendationsGrid) return;
  recommendationsGrid.innerHTML = '';

  if (!recommendations.length) {
    recommendationsGrid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #64748b;">
        <i class="fas fa-search" style="font-size: 3rem; margin-bottom: 20px; opacity: 0.5;"></i>
        <h3>No matching labs found</h3>
        <p>Try adjusting your major or interests</p>
      </div>
    `;
    return;
  }

  recommendations.forEach(rec => {
    const idx = allLabs.findIndex(l => l.name === rec.name); // best-effort match

    const card = document.createElement('div');
    card.className = 'recommendation-card';
    card.innerHTML = `
      <div class="recommendation-score">${(rec.relevance_score ?? 0)}/10</div>
      <div class="recommendation-content">
        <h3>${escapeHtml(rec.name || '')}</h3>
        <p><strong>Professor:</strong> ${escapeHtml(rec.professor || '')}</p>
        <p><strong>School:</strong> ${escapeHtml(rec.school || '')}</p>
        <p>${escapeHtml(truncateText(rec.description || '', 120))}</p>
        <button class="btn btn-secondary btn-small" data-open-lab ${idx >= 0 ? '' : 'disabled'}>
          <i class="fas fa-info-circle"></i>
          View Details
        </button>
      </div>
    `;
    if (idx >= 0) card.setAttribute('data-index', String(idx));

    recommendationsGrid.appendChild(card);
  });

  // Delegate clicks inside recommendations grid
  recommendationsGrid.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-open-lab]');
    const wrap = e.target.closest('.recommendation-card');
    if (btn && wrap && wrap.hasAttribute('data-index')) {
      const idx = parseInt(wrap.getAttribute('data-index'), 10);
      openLabModal(idx);
    }
  }, { once: true });
}

// -------------------- RAG Upload & Submit --------------------
function initRAGUpload() {
  if (ragUploadArea) {
    ragUploadArea.addEventListener('click', () => ragTranscriptFile?.click());
    ragUploadArea.addEventListener('dragover', (e) => {
      e.preventDefault();
      ragUploadArea.classList.add('dragover');
    });
    ragUploadArea.addEventListener('dragleave', () => {
      ragUploadArea.classList.remove('dragover');
    });
    ragUploadArea.addEventListener('drop', (e) => {
      e.preventDefault();
      ragUploadArea.classList.remove('dragover');
      const f = e.dataTransfer?.files?.[0];
      if (f) handleRAGFileSelect(f);
    });
  }

  ragTranscriptFile?.addEventListener('change', (e) => {
    const f = e.target.files?.[0];
    if (f) handleRAGFileSelect(f);
    updateRagFieldRequirements();
  });

  // Initialize required-state on load
  updateRagFieldRequirements();

  ragForm?.addEventListener('submit', onRAGSubmit);
}

function onRAGSubmit(e) {
  e.preventDefault();
  (async () => {
    try {
      if (ragSubmitBtn) {
        ragSubmitBtn.innerHTML = '<div class="spinner"></div> Analyzing with AI...';
        ragSubmitBtn.disabled = true;
      }

      const careerGoals = $$('#rag-form input[name="career-goals"]:checked').map(cb => cb.value);
      const interests    = $$('#rag-form .interest-tag input[type="checkbox"]:checked').map(cb => cb.value);

      const hasTranscript = !!(ragTranscriptFile?.files?.[0]);

      const studentData = {
        name: $('#rag-name')?.value || '',
        academic: {
          major: $('#rag-major')?.value || '',
          gpa: $('#rag-gpa')?.value || '',
          year: $('#rag-year')?.value || ''
        },
        goals: { careerGoals, interests }
      };

      // If transcript provided, allow empty name/major/gpa/year
      if (hasTranscript) {
        // No-op: backend can still use provided fields if present
      } else {
        // Basic client validation if no transcript
        if (!studentData.name || !studentData.academic.major || !studentData.academic.gpa || !studentData.academic.year) {
          showError('Please complete name, major, GPA, and year or upload a transcript.');
          return;
        }
      }

      const fd = new FormData();
      fd.append('student_data', JSON.stringify(studentData));
      const file = ragTranscriptFile?.files?.[0];
      if (file) fd.append('transcript', file);

      const resp = await fetch('/api/rag-recommendations', { method: 'POST', body: fd });
      const text = await resp.text();
      let data;
      try { data = JSON.parse(text); } catch { data = { error: text }; }

      if (!resp.ok || data.error) throw new Error(data.error || `Upload failed (${resp.status})`);

      // Show results in modal
      const html = renderRAGHtml(data.recommendations || []);
      ragRecs = Array.isArray(data.recommendations) ? data.recommendations : [data.recommendations];
      ragRecIndex = 0;
      renderRAGModalSlide(ragRecIndex);
      openRagModal();

      // Hide inline results panel if present
      if (ragResults) ragResults.style.display = 'none';
    } catch (err) {
      console.error('Error getting RAG recommendations:', err);
      showError(err.message || 'Failed to get AI recommendations. Please try again.');
    } finally {
      if (ragSubmitBtn) {
        ragSubmitBtn.innerHTML = '<i class="fas fa-robot"></i> Get AI Recommendations';
        ragSubmitBtn.disabled = false;
      }
    }
  })();
}

function handleRAGFileSelect(file) {
  if (!/\.pdf$/i.test(file.name || '')) {
    alert('Please select a .pdf file.');
    return;
  }
  if (file.size > 10 * 1024 * 1024) { // 10MB limit (client-side)
    alert('File size must be less than 10MB.');
    return;
  }

  if (ragTranscriptFile) {
    const dt = new DataTransfer();
    dt.items.add(file);
    ragTranscriptFile.files = dt.files;
  }

  if (ragFileNameEl) ragFileNameEl.textContent = file.name;
  if (ragFileSizeEl) ragFileSizeEl.textContent = formatFileSize(file.size);

  if (ragUploadArea) ragUploadArea.style.display = 'none';
  if (ragFilePreview) ragFilePreview.style.display = 'block';

  updateRagFieldRequirements();
}

function removeRAGFile() {
  if (ragTranscriptFile) ragTranscriptFile.value = '';
  if (ragUploadArea) ragUploadArea.style.display = 'block';
  if (ragFilePreview) ragFilePreview.style.display = 'none';
  if (ragFileNameEl) ragFileNameEl.textContent = '';
  if (ragFileSizeEl) ragFileSizeEl.textContent = '';
  updateRagFieldRequirements();
}

// Toggle required attributes if transcript is present
function updateRagFieldRequirements() {
  const hasTranscript = !!(ragTranscriptFile?.files?.length);
  const nameEl  = $('#rag-name');
  const majorEl = $('#rag-major');
  const gpaEl   = $('#rag-gpa');
  const yearEl  = $('#rag-year');

  [nameEl, majorEl, gpaEl, yearEl].forEach(el => {
    if (!el) return;
    if (hasTranscript) {
      el.removeAttribute('required');
      el.classList.add('optional-when-transcript');
    } else {
      el.setAttribute('required', 'required');
      el.classList.remove('optional-when-transcript');
    }
  });
}

// Expose for button onclick (if you use one in HTML)
window.removeRAGFile = removeRAGFile;

// -------------------- RAG Result Renderers --------------------
function renderRAGHtml(recommendations) {
    const text = String(recommendations || '');
    const processed = text
      .replace(/^# (.*$)/gim,  '<h2 style="color:#3b82f6;font-size:1.8rem;margin:30px 0 20px;display:flex;align-items:center;gap:10px;"><i class="fas fa-star"></i> $1</h2>')
      .replace(/^## (.*$)/gim, '<h3 style="color:#3b82f6;font-size:1.4rem;margin:25px 0 15px;display:flex;align-items:center;gap:8px;"><i class="fas fa-flask"></i> $1</h3>')
      .replace(/^### (.*$)/gim,'<h4 style="color:#3b82f6;font-size:1.2rem;margin:20px 0 10px;">$1</h4>')
      .replace(/\*\*(.*?)\*\*/g, '<strong style="color:#3b82f6;">$1</strong>')
      .replace(/\*(.*?)\*/g,    '<em>$1</em>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" style="color:#3b82f6;text-decoration:underline;">$1</a>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>');
    return `<p>${processed}</p>`;
  }

// Render a single recommendation as a lab-style card
function renderRAGCard(rec, indexInAll) {
  // Normalize structure: support string, or object with fields
  const isString = typeof rec === 'string';
  const name = isString ? '' : (rec.name || rec.lab_name || rec.title || 'Recommended Lab');
  const professor = isString ? '' : (rec.professor || rec.pi || rec.advisor || '');
  const school = isString ? '' : (rec.school || rec.department || '');
  const url = isString ? '' : (rec.url || rec.link || '#');
  const email = isString ? '' : (rec.professor_email || rec.email || rec.prof_email || '');
  const score = isString ? null : (rec.relevance_score ?? rec.score ?? null);
  const skills = isString ? [] : (Array.isArray(rec.skills) ? rec.skills : []);
  const coursework = isString ? [] : (Array.isArray(rec.coursework) ? rec.coursework : []);
  const descriptionRaw = isString ? rec : (rec.description || rec.text || JSON.stringify(rec));
  const descriptionHTML = renderRAGHtml(descriptionRaw);

  const skillsHtml = skills.length ? `<div class="mini-list"><strong>Skills to highlight:</strong><ul>${skills.slice(0,8).map(s => `<li>${escapeHtml(String(s))}</li>`).join('')}</ul></div>` : '';
  const courseworkHtml = coursework.length ? `<div class="mini-list"><strong>Relevant coursework:</strong><ul>${coursework.slice(0,8).map(c => `<li>${escapeHtml(String(c))}</li>`).join('')}</ul></div>` : '';

  return `
    <div class="recommendation-card" data-index="${indexInAll}">
      ${score != null ? `<div class="recommendation-score">${score}/10</div>` : ''}
      <div class="recommendation-content">
        <h3>${escapeHtml(name)}</h3>
        ${professor ? `<p><strong>Professor:</strong> ${escapeHtml(professor)}</p>` : ''}
        ${school ? `<p><strong>School:</strong> ${escapeHtml(school)}</p>` : ''}
        ${email ? `<p><strong>Email:</strong> <a href="mailto:${escapeHtml(email)}">${escapeHtml(email)}</a></p>` : ''}
        ${url && url !== '#' ? `<p><a href="${escapeHtml(url)}" target="_blank">Visit lab website</a></p>` : ''}
        <div class="rag-card-description">${descriptionHTML}</div>
        ${skillsHtml}
        ${courseworkHtml}
      </div>
    </div>
  `;
}

function displayRAGResults(recommendations) {
  if (!ragContent) return;
  ragContent.innerHTML = renderRAGHtml(recommendations);
}

// -------------------- RAG Modal Helpers (GLOBAL) --------------------
function openRagModal() {
    const modal = document.getElementById('rag-modal');
    if (!modal) return;
    modal.style.display = 'grid';
    document.body.style.overflow = 'hidden';
}

function renderRAGModalSlide(index) {
    const body = document.getElementById('rag-modal-body');
    if (!body || !ragRecs.length) return;
  
    const rec = ragRecs[index];
    const cardHtml = renderRAGCard(rec, index);
    
    body.innerHTML = `
      <div class="rag-slide">
        ${cardHtml}
        <div class="rag-controls" style="margin-top:20px;display:flex;justify-content:space-between;gap:10px;">
          <button class="btn btn-secondary" onclick="prevRagRec()" ${index === 0 ? 'disabled' : ''}>← Prev</button>
          <button class="btn btn-primary" onclick="nextRagRec()" ${index === ragRecs.length-1 ? 'disabled' : ''}>Next →</button>
        </div>
        <p style="margin-top:10px;text-align:center;color:var(--text-secondary);">
          ${index+1} of ${ragRecs.length}
        </p>
      </div>
    `;
  }

  function nextRagRec() {
    if (ragRecIndex < ragRecs.length - 1) {
      ragRecIndex++;
      renderRAGModalSlide(ragRecIndex);
    }
  }
  
  function prevRagRec() {
    if (ragRecIndex > 0) {
      ragRecIndex--;
      renderRAGModalSlide(ragRecIndex);
    }
  }

  
function closeRagModal() {
  const modal = document.getElementById('rag-modal');
  if (!modal) return;
  modal.style.display = 'none';
  document.body.style.overflow = 'auto';
}

// Backdrop click closes RAG modal
window.addEventListener('click', (e) => {
  const m = document.getElementById('rag-modal');
  if (m && e.target === m) closeRagModal();
});

// ESC closes RAG modal
document.addEventListener('keydown', (e) => {
  const m = document.getElementById('rag-modal');
  if (e.key === 'Escape' && m && m.style.display === 'grid') closeRagModal();
});

// Expose for inline handler if needed
window.openRagModal = openRagModal;
window.closeRagModal = closeRagModal;

// -------------------- Stats Animation --------------------
function animateStats() {
  const stats = $$('.stat-number');
  if (!stats.length) return;

  const io = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      const finalVal = parseInt(el.getAttribute('data-target') || '0', 10);
      animateNumber(el, 0, finalVal, 2000);
      io.unobserve(el);
    });
  });

  stats.forEach(el => io.observe(el));
}

function animateNumber(el, start, end, duration) {
  const t0 = performance.now();
  function step(t) {
    const p = Math.min((t - t0) / duration, 1);
    const cur = Math.floor(start + (end - start) * p);
    el.textContent = String(cur);
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// -------------------- Utilities --------------------
function truncateText(text, maxLength) {
  if ((text || '').length <= maxLength) return text || '';
  return (text || '').slice(0, maxLength) + '…';
}

function debounce(fn, wait = 300) {
  let to;
  return (...args) => {
    clearTimeout(to);
    to = setTimeout(() => fn(...args), wait);
  };
}

function showError(message) {
  alert(message || 'Something went wrong.');
}

function scrollToSection(sectionId) {
  const section = document.getElementById(sectionId);
  if (section) section.scrollIntoView({ behavior: 'smooth' });
}

function formatFileSize(bytes) {
  if (typeof bytes !== 'number') return '';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0, n = bytes;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  const fixed = n < 10 && i > 0 ? 1 : 0;
  return `${n.toFixed(fixed)} ${units[i]}`;
}

function escapeHtml(str) {
  return String(str)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

// Expose selected functions when HTML uses inline handlers
window.openLabModal = openLabModal;
window.closeModal   = closeModal;
window.toggleTheme  = toggleTheme;
// Optional alias if your HTML calls removeFile()
window.removeFile   = removeRAGFile;
window.nextRagRec = nextRagRec;
window.prevRagRec = prevRagRec;