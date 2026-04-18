// Main JavaScript for Legal Document Analyzer

// Global function to toggle hidden issues (must be outside DOMContentLoaded)
function toggleIssues(event, targetId) {
    event.preventDefault();
    const hiddenDiv = document.getElementById(targetId);
    const link = event.currentTarget;
    
    if (hiddenDiv.style.display === 'none') {
        hiddenDiv.style.display = 'block';
        link.textContent = 'Show less \u25B2';
    } else {
        hiddenDiv.style.display = 'none';
        const count = hiddenDiv.querySelectorAll('.issue-item').length;
        link.textContent = `Show ${count} more issue${count > 1 ? 's' : ''} \u25BC`;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Form elements
    const uploadForm = document.getElementById('uploadForm');
    const textForm = document.getElementById('textForm');
    const compareForm = document.getElementById('compareForm');
    const fileInput = document.getElementById('fileInput');
    const textInput = document.getElementById('textInput');
    const compareFile1 = document.getElementById('compareFile1');
    const compareFile2 = document.getElementById('compareFile2');
    
    // Result elements
    const resultsSummary = document.getElementById('resultsSummary');
    const clausesContainer = document.getElementById('clausesContainer');
    const clausesList = document.getElementById('clausesList');
    const errorAlert = document.getElementById('errorAlert');
    const comparisonResults = document.getElementById('comparisonResults');
    const comparisonWinner = document.getElementById('comparisonWinner');
    const comparisonDoc1 = document.getElementById('comparisonDoc1');
    const comparisonDoc2 = document.getElementById('comparisonDoc2');
    
    // Summary elements
    const totalClauses = document.getElementById('totalClauses');
    const overallScore = document.getElementById('overallScore');
    const highRisk = document.getElementById('highRisk');
    const mediumRisk = document.getElementById('mediumRisk');
    const lowRisk = document.getElementById('lowRisk');

    // Store current results for filtering
    let currentResults = null;

    // Handle file upload
    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const file = fileInput.files[0];
        if (!file) {
            showError('Please select a file to upload.');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        setLoading('upload', true);
        hideError();

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                displayResults(data);
            } else {
                showError(data.error || 'An error occurred during analysis.');
            }
        } catch (error) {
            showError('Failed to connect to server. Please try again.');
            console.error('Upload error:', error);
        } finally {
            setLoading('upload', false);
        }
    });

    // Handle text analysis
    textForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const text = textInput.value.trim();
        if (!text) {
            showError('Please enter some text to analyze.');
            return;
        }

        setLoading('text', true);
        hideError();

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ text: text })
            });

            const data = await response.json();

            if (response.ok) {
                displayResults(data);
            } else {
                showError(data.error || 'An error occurred during analysis.');
            }
        } catch (error) {
            showError('Failed to connect to server. Please try again.');
            console.error('Analysis error:', error);
        } finally {
            setLoading('text', false);
        }
    });

    // Handle document comparison
    compareForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const file1 = compareFile1.files[0];
        const file2 = compareFile2.files[0];

        if (!file1 || !file2) {
            showError('Please upload both documents for comparison.');
            return;
        }

        const formData = new FormData();
        formData.append('file1', file1);
        formData.append('file2', file2);

        setLoading('compare', true);
        hideError();

        try {
            const response = await fetch('/compare-documents', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                displayComparisonResults(data);
            } else {
                showError(data.error || 'An error occurred during document comparison.');
            }
        } catch (error) {
            showError('Failed to connect to server. Please try again.');
            console.error('Comparison error:', error);
        } finally {
            setLoading('compare', false);
        }
    });

    // Display analysis results
    function displayResults(data) {
        currentResults = data;

        comparisonResults.classList.add('d-none');

        // Update summary
        const summaryOverallScore = Number(data.overall_risk_score || 0);
        const summaryOverallRiskLevel = data.overall_risk_level || (
            summaryOverallScore >= 70 ? 'high' : summaryOverallScore >= 40 ? 'medium' : 'low'
        );

        overallScore.textContent = `${summaryOverallScore.toFixed(2)}%`;
        overallScore.classList.remove('summary-overall-high', 'summary-overall-medium', 'summary-overall-low');
        overallScore.classList.add(`summary-overall-${summaryOverallRiskLevel}`);
        totalClauses.textContent = data.total_clauses;
        highRisk.textContent = data.high_risk_count;
        mediumRisk.textContent = data.medium_risk_count;
        lowRisk.textContent = data.low_risk_count;

        // Show summary section
        resultsSummary.classList.remove('d-none');
        clausesContainer.classList.remove('d-none');

        // Display clauses
        displayClauses(data.clauses);

        // Scroll to results
        resultsSummary.scrollIntoView({ behavior: 'smooth' });
    }

    function displayComparisonResults(data) {
        resultsSummary.classList.add('d-none');
        clausesContainer.classList.add('d-none');

        const doc1 = data.document_1;
        const doc2 = data.document_2;
        const doc1IsWinner = data.higher_risk_document === 'document_1';
        const doc2IsWinner = data.higher_risk_document === 'document_2';
        const isTie = data.higher_risk_document === 'tie';

        if (isTie) {
            comparisonWinner.innerHTML = `
                <span class="comparison-banner-title">Comparison Result</span>
                <span class="comparison-banner-file">Both documents are equal risk. No winner panel highlighted.</span>
            `;
            comparisonWinner.className = 'comparison-banner tie';
        } else {
            comparisonWinner.innerHTML = `
                <span class="comparison-banner-title">Comparison Complete</span>
                <span class="comparison-banner-file">Highlighted panel shows the higher-risk document: ${data.higher_risk_filename}</span>
            `;
            comparisonWinner.className = 'comparison-banner risk';
        }

        comparisonDoc1.className = `comparison-doc-card ${doc1IsWinner ? 'winner-panel' : ''} ${isTie ? 'tie-panel' : 'loser-panel'}`.trim();
        comparisonDoc2.className = `comparison-doc-card ${doc2IsWinner ? 'winner-panel' : ''} ${isTie ? 'tie-panel' : 'loser-panel'}`.trim();

        comparisonDoc1.innerHTML = createComparisonCard('Document 1', doc1, doc1IsWinner);
        comparisonDoc2.innerHTML = createComparisonCard('Document 2', doc2, doc2IsWinner);

        comparisonResults.classList.remove('d-none');
        comparisonResults.scrollIntoView({ behavior: 'smooth' });
    }

    function createComparisonCard(title, doc, isWinner = false) {
        const riskClassMap = {
            high: 'risk-high',
            medium: 'risk-medium',
            low: 'risk-low'
        };

        const winnerPill = isWinner
            ? '<span class="panel-winner-pill">Higher Risk</span>'
            : '';

        const topClauses = (doc.clauses || []).slice(0, 3);
        const topClausesHtml = topClauses.length > 0
            ? `
                <div class="comparison-top-clauses mt-3">
                    <p class="comparison-section-label mb-2">Top Risky Clauses</p>
                    ${topClauses.map(c => `
                        <div class="comparison-clause-item">
                            <div class="d-flex justify-content-between gap-2">
                                <span class="comparison-clause-label">Clause ${c.label}</span>
                                <span class="comparison-clause-score">${c.combined_score}%</span>
                            </div>
                            <p class="comparison-clause-text mb-0">${highlightComparisonTerms(c)}</p>
                        </div>
                    `).join('')}
                </div>
            `
            : '<p class="text-muted small mt-3 mb-0">No clauses detected.</p>';

        return `
            <div class="comparison-doc-head">
                <div class="d-flex justify-content-between align-items-center gap-2 mb-1">
                    <p class="comparison-doc-title mb-0">${title}</p>
                    ${winnerPill}
                </div>
                <p class="comparison-filename mb-2">${doc.filename}</p>
                <span class="risk-badge ${riskClassMap[doc.overall_risk_level]}">${doc.overall_risk_level} Risk</span>
            </div>
            <div class="comparison-metric-grid mt-3">
                <div class="comparison-metric-item metric-overall-${doc.overall_risk_level}">
                    <small>Overall Score</small>
                    <strong>${doc.overall_risk_score}%</strong>
                </div>
                <div class="comparison-metric-item metric-neutral">
                    <small>Total Clauses</small>
                    <strong>${doc.total_clauses}</strong>
                </div>
                <div class="comparison-metric-item metric-high">
                    <small>High Risk</small>
                    <strong>${doc.high_risk_count}</strong>
                </div>
                <div class="comparison-metric-item metric-medium">
                    <small>Medium Risk</small>
                    <strong>${doc.medium_risk_count}</strong>
                </div>
                <div class="comparison-metric-item metric-low">
                    <small>Low Risk</small>
                    <strong>${doc.low_risk_count}</strong>
                </div>
            </div>
            ${topClausesHtml}
        `;
    }

    function highlightComparisonTerms(clause) {
        if (!clause || !clause.text) {
            return '';
        }

        const findings = (clause.rule_based && clause.rule_based.findings) ? clause.rule_based.findings : [];
        if (!findings.length) {
            return clause.text;
        }

        const highlightClass = clause.final_risk_level === 'high' ? 'highlight-loophole' : 'highlight-vague';
        let highlightedText = clause.text;

        findings.forEach(finding => {
            const escapedTerm = escapeRegex(finding.term);
            const regex = new RegExp(`(${escapedTerm})`, 'gi');
            highlightedText = highlightedText.replace(regex, `<span class="${highlightClass}">$1</span>`);
        });

        return highlightedText;
    }

    // Display clause cards
    function displayClauses(clauses, filter = 'all') {
        clausesList.innerHTML = '';

        const filteredClauses = filter === 'all' 
            ? clauses 
            : clauses.filter(c => c.final_risk_level === filter);

        if (filteredClauses.length === 0) {
            clausesList.innerHTML = '<p class="text-muted text-center">No clauses found for this filter.</p>';
            return;
        }

        filteredClauses.forEach(clause => {
            const card = createClauseCard(clause);
            clausesList.appendChild(card);
        });
    }

    // Create clause card element
    function createClauseCard(clause) {
        const card = document.createElement('div');
        card.className = `clause-card risk-level-${clause.final_risk_level}`;

        const riskBadgeClass = {
            'high': 'risk-high',
            'medium': 'risk-medium',
            'low': 'risk-low'
        }[clause.final_risk_level];

        const scoreClass = clause.combined_score >= 70 ? 'high' : 
                          clause.combined_score >= 40 ? 'medium' : 'low';

        // Generate unique ID for this clause's expandable section
        const clauseUniqueId = `clause-issues-${clause.id}-${Date.now()}`;

        let issuesHtml = '';
        if (clause.rule_based.findings && clause.rule_based.findings.length > 0) {
            const visibleFindings = clause.rule_based.findings.slice(0, 5);
            const hiddenFindings = clause.rule_based.findings.slice(5);
            
            issuesHtml = `
                <div class="issues-list">
                    <small class="text-muted fw-bold">Issues Found (${clause.rule_based.findings.length}):</small>
                    ${visibleFindings.map(f => `
                        <div class="issue-item">
                            <span class="issue-icon">⚠</span>
                            <span><strong>${f.term}</strong>: ${f.explanation}</span>
                        </div>
                    `).join('')}
                    ${hiddenFindings.length > 0 ? `
                        <div id="${clauseUniqueId}" class="hidden-issues" style="display: none;">
                            ${hiddenFindings.map(f => `
                                <div class="issue-item">
                                    <span class="issue-icon">⚠</span>
                                    <span><strong>${f.term}</strong>: ${f.explanation}</span>
                                </div>
                            `).join('')}
                        </div>
                        <a href="#" class="show-more-link text-primary" data-target="${clauseUniqueId}" onclick="toggleIssues(event, '${clauseUniqueId}')">
                            Show ${hiddenFindings.length} more issue${hiddenFindings.length > 1 ? 's' : ''} ▼
                        </a>
                    ` : ''}
                </div>
            `;
        } else if (clause.ml_prediction && clause.ml_prediction.is_ambiguous) {
            issuesHtml = `
                <div class="issues-list">
                    <small class="text-muted fw-bold">ML Detection:</small>
                    <div class="issue-item">
                        <span class="issue-icon">🤖</span>
                        <span>SVM classifier detected ambiguous language (confidence: ${(clause.ml_prediction.probability_ambiguous * 100).toFixed(1)}%)</span>
                    </div>
                </div>
            `;
        } else {
            issuesHtml = `
                <div class="issues-list">
                    <small class="text-success fw-bold">✓ No issues detected — clause appears clear and well-defined.</small>
                </div>
            `;
        }

        card.innerHTML = `
            <div class="d-flex justify-content-between align-items-start mb-2">
                <span class="clause-label">Clause ${clause.label}</span>
                <span class="risk-badge ${riskBadgeClass}">${clause.final_risk_level} Risk</span>
            </div>
            <p class="clause-text">${highlightTerms(clause.text, clause.rule_based.findings)}</p>
            <div class="score-display">
                <small class="text-muted">Risk Score:</small>
                <div class="score-bar">
                    <div class="score-fill ${scoreClass}" style="width: ${clause.combined_score}%"></div>
                </div>
                <small class="fw-bold">${clause.combined_score}%</small>
            </div>
            ${issuesHtml}
        `;

        return card;
    }

    // Highlight problematic terms in clause text
    function highlightTerms(text, findings) {
        if (!findings || findings.length === 0) return text;

        let highlightedText = text;
        
        // Sort findings by position (reverse) to avoid index shifting
        const sortedFindings = [...findings].sort((a, b) => b.position - a.position);

        sortedFindings.forEach(finding => {
            const highlightClass = finding.type === 'loophole' ? 'highlight-loophole' : 'highlight-vague';
            const regex = new RegExp(`(${escapeRegex(finding.term)})`, 'gi');
            highlightedText = highlightedText.replace(regex, `<span class="${highlightClass}">$1</span>`);
        });

        return highlightedText;
    }

    // Escape special regex characters
    function escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // Filter button handlers
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            // Update active state
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            // Filter clauses
            const filter = this.dataset.filter;
            if (currentResults) {
                displayClauses(currentResults.clauses, filter);
            }
        });
    });

    // Set loading state
    function setLoading(type, isLoading) {
        const btnText = document.getElementById(`${type}BtnText`);
        const spinner = document.getElementById(`${type}Spinner`);
        const formMap = {
            upload: uploadForm,
            text: textForm,
            compare: compareForm
        };
        const form = formMap[type];
        const btn = form.querySelector('button[type="submit"]');

        if (isLoading) {
            btnText.classList.add('d-none');
            spinner.classList.remove('d-none');
            btn.disabled = true;
        } else {
            btnText.classList.remove('d-none');
            spinner.classList.add('d-none');
            btn.disabled = false;
        }
    }

    // Show error message
    function showError(message) {
        errorAlert.textContent = message;
        errorAlert.classList.remove('d-none');
    }

    // Hide error message
    function hideError() {
        errorAlert.classList.add('d-none');
    }
});
