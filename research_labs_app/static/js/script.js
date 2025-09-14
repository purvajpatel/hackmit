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

  // Check if search term matches any professor names closely
  const professorMatches = findProfessorMatches(searchTerm);
  
  if (searchTerm && professorMatches.length > 0 && !selectedSchool && !selectedProfessor) {
    // Only show professor options if no other filters are applied
    // and we have professor matches
    const hasExactLabMatch = allLabs.some(lab => {
      const name = (lab.name || '').toLowerCase();
      return name.includes(searchTerm);
    });
    
    // Prioritize professor matches over partial lab name matches
    if (!hasExactLabMatch || professorMatches.some(p => p.name.toLowerCase().includes(searchTerm))) {
      displayProfessorOptions(professorMatches, searchTerm);
      return;
    }
  }

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

// -------------------- Professor Search Functions --------------------
function findProfessorMatches(searchTerm) {
  if (!searchTerm || searchTerm.length < 2) return [];
  
  const professors = new Map();
  
  allLabs.forEach(lab => {
    const prof = (lab.professor || '').trim();
    if (!prof || prof === 'Unknown') return;
    
    const profLower = prof.toLowerCase();
    const searchLower = searchTerm.toLowerCase();
    
    // Check if search term matches professor name (partial match)
    if (profLower.includes(searchLower) || 
        prof.split(' ').some(part => part.toLowerCase().startsWith(searchLower))) {
      
      if (!professors.has(prof)) {
        professors.set(prof, {
          name: prof,
          labs: [],
          school: lab.school
        });
      }
      professors.get(prof).labs.push(lab);
    }
  });
  
  return Array.from(professors.values());
}

function displayProfessorOptions(professorMatches, searchTerm) {
  if (!labsGrid) return;
  
  labsGrid.innerHTML = '';
  
  // Add a header explaining the results
  const header = document.createElement('div');
  header.className = 'search-results-header';
  header.style.cssText = 'grid-column: 1 / -1; text-align: center; padding: 20px; margin-bottom: 20px; background: var(--card-bg); border-radius: 12px; border: 1px solid var(--border-color);';
  header.innerHTML = `
    <h3 style="margin: 0 0 10px 0; color: var(--text-primary);">Found ${professorMatches.length} professor(s) matching "${escapeHtml(searchTerm)}"</h3>
    <p style="margin: 0; color: var(--text-secondary);">Click on a professor to see their labs</p>
  `;
  labsGrid.appendChild(header);
  
  professorMatches.forEach(professor => {
    const card = createProfessorCard(professor);
    labsGrid.appendChild(card);
  });
  
  // Hide load more button
  if (loadMoreBtn) {
    loadMoreBtn.style.display = 'none';
  }
}

function createProfessorCard(professor) {
  const card = document.createElement('div');
  card.className = 'professor-card lab-card'; // Reuse lab-card styling
  card.style.cursor = 'pointer';
  
  card.innerHTML = `
    <div class="lab-header">
      <div>
        <h3 class="lab-name"><i class="fas fa-user-tie" style="margin-right: 8px; color: var(--primary-color);"></i>${escapeHtml(professor.name)}</h3>
        <p class="lab-professor" style="color: var(--text-secondary);">Professor</p>
      </div>
    </div>
    <p class="lab-school">${escapeHtml(professor.school || '')}</p>
    <p class="lab-description">Click to view ${professor.labs.length} lab${professor.labs.length !== 1 ? 's' : ''} associated with this professor</p>
    <div class="lab-actions">
      <button class="btn btn-primary btn-small">
        <i class="fas fa-flask"></i>
        View Labs (${professor.labs.length})
      </button>
    </div>
  `;
  
  card.addEventListener('click', () => {
    showProfessorLabs(professor);
  });
  
  return card;
}

function showProfessorLabs(professor) {
  // Use the same modal system as RAG recommendations
  const recommendations = professor.labs.map(lab => ({
    name: lab.name,
    professor: lab.professor,
    school: lab.school,
    url: lab.url,
    description: lab.description,
    professor_email: lab.professor_email || '',
    relevance_score: null // No scoring for professor lab listings
  }));
  
  // Store the recommendations globally for modal navigation
  ragRecs = recommendations;
  ragRecIndex = 0;
  
  // Render the modal with professor's labs
  renderProfessorLabsModal(professor, recommendations);
  openRagModal();
}

function renderProfessorLabsModal(professor, labs) {
  const body = document.getElementById('rag-modal-body');
  if (!body) return;
  
  // Update modal header to show professor info
  const modalHeader = document.querySelector('#rag-modal .modal-header h3');
  if (modalHeader) {
    modalHeader.innerHTML = `<i class="fas fa-user-tie"></i> ${escapeHtml(professor.name)} - Research Labs`;
  }
  
  if (labs.length === 1) {
    // Single lab - show directly
    const cardHtml = renderRAGCard(labs[0], 0);
    body.innerHTML = `
      <div class="rag-slide">
        ${cardHtml}
      </div>
    `;
  } else {
    // Multiple labs - show with navigation
    renderRAGModalSlide(0);
  }
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

  // Set up the draft email button
  const draftBtn = $('#modal-draft-email-btn');
  if (draftBtn) {
    draftBtn.onclick = () => {
      if (!currentStudentData) {
        alert('Please complete the AI Analysis form first to draft an email.');
        return;
      }
      draftEmail(lab.professor || '', lab.name || '');
    };
  }

  labModal.style.display = 'block';
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  if (!labModal) return;
  labModal.style.display = 'none';
  document.body.style.overflow = 'auto';
}

// -------------------- Contact (removed - replaced with draft email) --------------------

// -------------------- Basic Recommendations --------------------
async function getRecommendations() {
  // Get data from the AI Analysis form instead of separate form
  let major = ($('#rag-major')?.value || '').trim();
  let interests = $$('#rag-form .interest-tag input[type="checkbox"]:checked').map(cb => cb.value);

  // Use stored student data from AI Analysis if available and form is empty
  if (currentStudentData && (!major || interests.length === 0)) {
    if (!major && currentStudentData.academic?.major) {
      major = currentStudentData.academic.major;
      const majorInput = $('#rag-major');
      if (majorInput) majorInput.value = major;
    }
    if (interests.length === 0 && currentStudentData.goals?.interests) {
      interests = currentStudentData.goals.interests;
      // Check the corresponding checkboxes in the AI Analysis form
      interests.forEach(interest => {
        const checkbox = $(`#rag-form input[value="${interest}"]`);
        if (checkbox) checkbox.checked = true;
      });
    }
  }

  if (!major) { alert('Please enter your major or complete the AI Analysis first to get recommendations.'); return; }
  if (interests.length === 0) { alert('Please select at least one research interest or complete the AI Analysis first.'); return; }

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
    // Show the recommendations section
    const recommendationsSection = $('#recommendations');
    if (recommendationsSection) {
      recommendationsSection.style.display = 'block';
      recommendationsSection.scrollIntoView({ behavior: 'smooth' });
    }
    
    // Show a notice if we used stored data
    if (currentStudentData && (currentStudentData.academic?.major === major || 
        (currentStudentData.goals?.interests && currentStudentData.goals.interests.some(i => interests.includes(i))))) {
      const notice = document.createElement('div');
      notice.style.cssText = 'background: var(--surface); border: 1px solid var(--accent); border-radius: var(--radius); padding: 15px; margin-bottom: 20px; text-align: center;';
      notice.innerHTML = '<i class="fas fa-info-circle" style="color: var(--accent); margin-right: 8px;"></i>Used information from your AI Analysis to enhance recommendations.';
      recommendationsGrid.parentNode.insertBefore(notice, recommendationsGrid);
      setTimeout(() => notice.remove(), 5000);
    }
  } catch (err) {
    console.error('Error getting recommendations:', err);
    showError('Failed to get recommendations. Please try again.');
  } finally {
    if (getRecommendationsBtn) {
      getRecommendationsBtn.innerHTML = '<i class="fas fa-magic"></i> Get Basic Recommendations';
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

      // Extract transcript text for later use
      let transcript_text = '';
      if (hasTranscript) {
        // Note: We can't extract PDF text on the frontend, but we'll store the file info
        transcript_text = 'Transcript uploaded - content will be parsed on backend';
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

      // Store student data and transcript text for email drafting
      storeStudentData(studentData);
      storeTranscriptText(transcript_text);

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
      <div class="recommendation-content">
        <h3>${escapeHtml(name)}</h3>
        ${professor ? `<p><strong>Professor:</strong> ${escapeHtml(professor)}</p>` : ''}
        ${school ? `<p><strong>School:</strong> ${escapeHtml(school)}</p>` : ''}
        ${email ? `<p><strong>Email:</strong> <a href="mailto:${escapeHtml(email)}">${escapeHtml(email)}</a></p>` : ''}
        ${url && url !== '#' ? `<p><a href="${escapeHtml(url)}" target="_blank">Visit lab website</a></p>` : ''}
        <div class="rag-card-description">${descriptionHTML}</div>
        ${skillsHtml}
        ${courseworkHtml}
        <div class="rag-card-actions" style="margin-top: 15px;">
          <button class="btn btn-primary btn-small" onclick="draftEmail('${escapeHtml(professor)}', '${escapeHtml(name)}')">
            <i class="fas fa-envelope"></i>
            Draft an Email
          </button>
        </div>
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
        ${ragRecs.length > 1 ? `
        <div class="rag-controls" style="margin-top:20px;display:flex;justify-content:space-between;gap:10px;">
          <button class="btn btn-secondary" onclick="prevRagRec()" ${index === 0 ? 'disabled' : ''}>← Prev</button>
          <button class="btn btn-primary" onclick="nextRagRec()" ${index === ragRecs.length-1 ? 'disabled' : ''}>Next →</button>
        </div>
        <p style="margin-top:10px;text-align:center;color:var(--text-secondary);">
          ${index+1} of ${ragRecs.length}
        </p>` : ''}
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
  
  // Reset modal header to default
  const modalHeader = document.querySelector('#rag-modal .modal-header h3');
  if (modalHeader) {
    modalHeader.innerHTML = '<i class="fas fa-magic"></i> AI Analysis Results';
  }
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

// -------------------- Email Drafting Functions --------------------
let currentStudentData = null;
let currentTranscriptText = null;

function draftEmail(professorName, labName) {
  console.log('Current student data:', currentStudentData);
  if (!currentStudentData) {
    alert('No student data available. Please complete the AI Analysis form first.');
    return;
  }

  // Show loading state
  const button = event.target;
  const originalText = button.innerHTML;
  button.innerHTML = '<div class="spinner"></div> Drafting Email...';
  button.disabled = true;

  // Call the backend to generate email
  fetch('/api/draft-email', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      professor_name: professorName,
      lab_name: labName,
      student_data: currentStudentData
    })
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      showEmailModal(data.email, professorName, labName);
    } else {
      alert('Failed to generate email: ' + data.error);
    }
  })
  .catch(error => {
    console.error('Error:', error);
    alert('Failed to generate email. Please try again.');
  })
  .finally(() => {
    // Restore button state
    button.innerHTML = originalText;
    button.disabled = false;
  });
}

function showEmailModal(emailText, professorName, labName) {
  const modal = document.getElementById('email-modal');
  const professorEl = document.getElementById('email-professor-name');
  const labEl = document.getElementById('email-lab-name');
  const emailEl = document.getElementById('email-text');

  if (modal && professorEl && labEl && emailEl) {
    professorEl.textContent = professorName;
    labEl.textContent = labName;
    emailEl.textContent = emailText;
    modal.style.display = 'grid';
    document.body.style.overflow = 'hidden';
  }
}

function closeEmailModal() {
  const modal = document.getElementById('email-modal');
  if (modal) {
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
  }
}

function copyEmail() {
  const emailText = document.getElementById('email-text');
  if (emailText) {
    navigator.clipboard.writeText(emailText.textContent).then(() => {
      alert('Email copied to clipboard!');
    }).catch(err => {
      console.error('Failed to copy: ', err);
      alert('Failed to copy email to clipboard.');
    });
  }
}

// Store student data when RAG form is submitted
function storeStudentData(studentData) {
  console.log('Storing student data:', studentData);
  currentStudentData = studentData;
}

// Store transcript text when RAG form is submitted
function storeTranscriptText(transcriptText) {
  console.log('Storing transcript text:', transcriptText);
  currentTranscriptText = transcriptText;
}

// Expose functions globally
window.draftEmail = draftEmail;
window.closeEmailModal = closeEmailModal;
window.copyEmail = copyEmail;
window.storeStudentData = storeStudentData;

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