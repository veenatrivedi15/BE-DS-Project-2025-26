// static/js/script.js

const appContent = document.getElementById('appContent');
const contractReviewBtn = document.getElementById('contractReviewBtn');
const legalQABtn = document.getElementById('legalQABtn');
const timelineBtn = document.getElementById('timelineBtn');

let activeSection = 'contractReview'; // Initial active section
let contractContentGlobal = ''; // Store contract content globally for timeline generation

// Utility function for exponential backoff (frontend)
const retryFetchFrontend = async (url, options, retries = 3, delay = 1000) => {
    for (let i = 0; i < retries; i++) {
        try {
            const response = await fetch(url, options);
            if (response.ok) {
                return response;
            } else if (response.status === 429 && i < retries - 1) { // Too Many Requests
                console.warn(`Frontend: Rate limit hit, retrying in ${delay / 1000}s...`);
                await new Promise(resolve => setTimeout(resolve, delay));
                delay *= 2; // Exponential backoff
            } else {
                const errorData = await response.json();
                throw new Error(`HTTP error! status: ${response.status}, message: ${errorData.error || 'Unknown error'}`);
            }
        } catch (error) {
            if (i < retries - 1 && error.message.includes('Failed to fetch')) { // Network error or CORS
                console.error(`Frontend: Fetch error: ${error.message}. Retrying in ${delay / 1000}s...`);
                await new Promise(resolve => setTimeout(resolve, delay));
                delay *= 2;
            } else {
                throw error;
            }
        }
    }
    throw new Error('Frontend: Max retries exceeded');
};


// --- Render Functions for each section ---

const renderContractReview = () => {
    appContent.innerHTML = `
        <div class="space-y-6">
            <h2 class="text-2xl font-semibold text-gray-800">Contract Review</h2>
            <div class="bg-white p-6 rounded-xl shadow-lg border border-gray-200">
                <label for="contractUpload" class="block text-lg font-medium text-gray-700 mb-2">Upload your contract (TXT only for demo)</label>
                <input
                    type="file"
                    id="contractUpload"
                    accept=".txt"
                    class="block w-full text-sm text-gray-500
                            file:mr-4 file:py-2 file:px-4
                            file:rounded-full file:border-0
                            file:text-sm file:font-semibold
                            file:bg-blue-50 file:text-blue-700
                            hover:file:bg-blue-100 cursor-pointer"
                />
                <p class="text-sm text-gray-500 mt-2">Note: For DOCX/PDF, a backend service is typically required for text extraction.</p>
                <div id="contractContentPreview" class="${contractContentGlobal ? 'mt-6' : 'hidden'}">
                    <h3 class="text-xl font-medium text-gray-800 mb-3">Contract Content Preview:</h3>
                    <textarea
                        id="contractPreviewTextarea"
                        readOnly
                        class="w-full h-64 p-4 border border-gray-300 rounded-lg bg-gray-50 text-gray-700 font-mono text-sm resize-none focus:outline-none"
                        placeholder="Your contract content will appear here..."
                    >${contractContentGlobal}</textarea>
                </div>
            </div>

            <div id="contractReviewLoading" class="hidden flex items-center justify-center bg-white p-6 rounded-xl shadow-lg border border-gray-200">
                <svg class="animate-spin mr-2 text-blue-500" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
                <span class="text-blue-600 font-medium">Analyzing contract with AI...</span>
            </div>

            <div id="contractReviewResults">
                </div>
        </div>
    `;

    // Attach event listener for file upload
    document.getElementById('contractUpload').addEventListener('change', handleFileUpload);

    // Update preview if content already exists
    if (contractContentGlobal) {
        document.getElementById('contractContentPreview').classList.remove('hidden');
    }
};

const renderLegalQA = () => {
    appContent.innerHTML = `
        <div class="space-y-6">
            <h2 class="text-2xl font-semibold text-gray-800">Legal Question & Answer</h2>
            <div class="bg-white p-6 rounded-xl shadow-lg border border-gray-200">
                <label for="legalQuestion" class="block text-lg font-medium text-gray-700 mb-2">Ask your legal question:</label>
                <textarea
                    id="legalQuestion"
                    rows="4"
                    class="w-full p-4 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 text-gray-700 resize-none"
                    placeholder="E.g., What are the implications of a force majeure clause?"
                ></textarea>
                <button
                    id="askQuestionBtn"
                    class="mt-4 w-full md:w-auto px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg shadow-md hover:bg-blue-700 transition duration-300 ease-in-out transform hover:scale-105"
                >
                    <span id="qaBtnText">✨ Ask Question</span>
                    <svg id="qaLoadingSpinner" class="hidden animate-spin ml-2" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
                </button>
            </div>

            <div id="legalQAResult" class="hidden bg-white p-6 rounded-xl shadow-lg border border-gray-200">
                <h3 class="text-xl font-medium text-blue-700 mb-3 flex items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-help-circle mr-2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/></svg> Answer:
                </h3>
                <p id="legalAnswerText" class="text-gray-700 text-base"></p>
            </div>
        </div>
    `;
    document.getElementById('askQuestionBtn').addEventListener('click', handleAskQuestion);
};

const renderTimeline = () => {
    appContent.innerHTML = `
        <div class="space-y-6">
            <h2 class="text-2xl font-semibold text-gray-800">Event Timeline Generation</h2>
            <div class="bg-white p-6 rounded-xl shadow-lg border border-gray-200">
                <p class="text-gray-700 text-base mb-4">Click the button below to generate a timeline of important legal events and dates from your documents. Ensure a contract is uploaded in the 'Contract Review' section first.</p>
                <button
                    id="generateTimelineBtn"
                    class="w-full md:w-auto px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg shadow-md hover:bg-blue-700 transition duration-300 ease-in-out transform hover:scale-105 ${!contractContentGlobal ? 'opacity-50 cursor-not-allowed' : ''}"
                    ${!contractContentGlobal ? 'disabled' : ''}
                >
                    <span id="timelineBtnText">✨ Generate Timeline</span>
                    <svg id="timelineLoadingSpinner" class="hidden animate-spin ml-2" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
                </button>
            </div>

            <div id="timelineResults" class="hidden bg-white p-6 rounded-xl shadow-lg border border-gray-200">
                <h3 class="text-xl font-medium text-purple-700 mb-3 flex items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-calendar mr-2"><path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/></svg> Important Legal Events Timeline:
                </h3>
                <ol id="timelineList" class="relative border-l border-gray-200 dark:border-gray-700 ml-4"></ol>
            </div>
        </div>
    `;
    document.getElementById('generateTimelineBtn').addEventListener('click', handleGenerateTimeline);
};

// --- Event Handlers (calling Flask backend) ---

const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    const loadingDiv = document.getElementById('contractReviewLoading');
    const resultsDiv = document.getElementById('contractReviewResults');
    loadingDiv.classList.remove('hidden');
    resultsDiv.innerHTML = ''; // Clear previous results

    try {
        const response = await retryFetchFrontend('/contract-review', {
            method: 'POST',
            body: formData,
        });
        const data = await response.json();

        if (data.error) {
            resultsDiv.innerHTML = `
                <div class="bg-red-50 border border-red-300 text-red-700 p-4 rounded-xl shadow-lg">
                    <p>Error: ${data.error}</p>
                </div>
            `;
            contractContentGlobal = ''; // Clear content on error
            document.getElementById('contractContentPreview').classList.add('hidden');
        } else {
            contractContentGlobal = data.contractContent;
            document.getElementById('contractPreviewTextarea').value = contractContentGlobal;
            document.getElementById('contractContentPreview').classList.remove('hidden');

            let issuesHtml = '';
            if (data.issues && data.issues.length > 0) {
                issuesHtml = `
                    <div class="bg-white p-6 rounded-xl shadow-lg border border-gray-200">
                        <h3 class="text-xl font-medium text-red-600 mb-3 flex items-center">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-file-text mr-2"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/></svg> Identified Legal & Risk Issues:
                        </h3>
                        <ul class="list-disc list-inside space-y-2 text-gray-700">
                            ${data.issues.map(issue => `<li class="text-base">${issue}</li>`).join('')}
                        </ul>
                    </div>
                `;
            } else {
                 issuesHtml = `
                    <div class="bg-white p-6 rounded-xl shadow-lg border border-gray-200">
                        <h3 class="text-xl font-medium text-green-600 mb-3 flex items-center">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-check-circle mr-2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg> No significant issues identified.
                        </h3>
                    </div>
                 `;
            }

            const solutionsHtml = `
                <div class="bg-white p-6 rounded-xl shadow-lg border border-gray-200 mt-6">
                    <h3 class="text-xl font-medium text-green-700 mb-3 flex items-center">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-help-circle mr-2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/></svg> Explanations & Practical Solutions:
                    </h3>
                    <p class="whitespace-pre-wrap text-gray-700 text-base">${data.solutions}</p>
                </div>
            `;
            resultsDiv.innerHTML = issuesHtml + solutionsHtml;
        }
    } catch (error) {
        console.error("Error during contract review:", error);
        resultsDiv.innerHTML = `
            <div class="bg-red-50 border border-red-300 text-red-700 p-4 rounded-xl shadow-lg">
                <p>Failed to analyze contract. Details: ${error.message}</p>
            </div>
        `;
        contractContentGlobal = ''; // Clear content on error
        document.getElementById('contractContentPreview').classList.add('hidden');
    } finally {
        loadingDiv.classList.add('hidden');
    }
};

const handleAskQuestion = async () => {
    const questionInput = document.getElementById('legalQuestion');
    const question = questionInput.value.trim();
    if (question === '') {
        alert('Please enter a question.');
        return;
    }

    const askQuestionBtn = document.getElementById('askQuestionBtn');
    const qaBtnText = document.getElementById('qaBtnText');
    const qaLoadingSpinner = document.getElementById('qaLoadingSpinner');
    const legalQAResult = document.getElementById('legalQAResult');
    const legalAnswerText = document.getElementById('legalAnswerText');

    askQuestionBtn.disabled = true;
    qaBtnText.classList.add('hidden');
    qaLoadingSpinner.classList.remove('hidden');
    legalQAResult.classList.add('hidden'); // Hide previous result
    legalAnswerText.textContent = '';

    try {
        const response = await retryFetchFrontend('/legal-qa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question })
        });
        const data = await response.json();

        if (data.error) {
            legalAnswerText.textContent = `Error: ${data.error}`;
            legalQAResult.classList.remove('hidden');
            legalQAResult.classList.add('bg-red-50', 'border-red-300', 'text-red-700'); // Style for error
            legalQAResult.classList.remove('bg-white', 'border-gray-200');
        } else {
            legalAnswerText.textContent = data.answer;
            legalQAResult.classList.remove('hidden');
            legalQAResult.classList.remove('bg-red-50', 'border-red-300', 'text-red-700'); // Remove error style
            legalQAResult.classList.add('bg-white', 'border-gray-200');
        }
    } catch (error) {
        console.error("Error during legal Q&A:", error);
        legalAnswerText.textContent = `Failed to get an answer. Details: ${error.message}`;
        legalQAResult.classList.remove('hidden');
        legalQAResult.classList.add('bg-red-50', 'border-red-300', 'text-red-700'); // Style for error
        legalQAResult.classList.remove('bg-white', 'border-gray-200');
    } finally {
        askQuestionBtn.disabled = false;
        qaBtnText.classList.remove('hidden');
        qaLoadingSpinner.classList.add('hidden');
    }
};

const handleGenerateTimeline = async () => {
    if (!contractContentGlobal) {
        alert('Please upload a contract in the "Contract Review" section first to generate a timeline.');
        return;
    }

    const generateTimelineBtn = document.getElementById('generateTimelineBtn');
    const timelineBtnText = document.getElementById('timelineBtnText');
    const timelineLoadingSpinner = document.getElementById('timelineLoadingSpinner');
    const timelineResultsDiv = document.getElementById('timelineResults');
    const timelineList = document.getElementById('timelineList');

    generateTimelineBtn.disabled = true;
    timelineBtnText.classList.add('hidden');
    timelineLoadingSpinner.classList.remove('hidden');
    timelineResultsDiv.classList.add('hidden'); // Hide previous results
    timelineList.innerHTML = '';

    try {
        const response = await retryFetchFrontend('/generate-timeline', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ contractContent: contractContentGlobal })
        });
        const data = await response.json();

        if (data.error) {
            timelineList.innerHTML = `
                <li class="mb-6 ml-6 text-red-700">
                    <span class="absolute flex items-center justify-center w-3 h-3 bg-red-100 rounded-full -left-1.5 ring-8 ring-white dark:ring-gray-900"></span>
                    <h4 class="text-lg font-semibold text-red-900">Error generating timeline:</h4>
                    <p class="text-sm font-normal leading-none text-red-500 mt-1">${data.error}</p>
                </li>
            `;
            timelineResultsDiv.classList.remove('hidden');
            timelineResultsDiv.classList.add('bg-red-50', 'border-red-300'); // Style for error
            timelineResultsDiv.classList.remove('bg-white', 'border-gray-200');
        } else {
            if (data.timelineEvents && data.timelineEvents.length > 0) {
                timelineList.innerHTML = data.timelineEvents.map(event => `
                    <li class="mb-6 ml-6">
                        <span class="absolute flex items-center justify-center w-3 h-3 bg-blue-100 rounded-full -left-1.5 ring-8 ring-white dark:ring-gray-900"></span>
                        <h4 class="flex items-center mb-1 text-lg font-semibold text-gray-900">
                            ${event.event}
                        </h4>
                        <time class="block mb-2 text-sm font-normal leading-none text-gray-500">
                            Date: ${event.date}
                        </time>
                    </li>
                `).join('');
                timelineResultsDiv.classList.remove('hidden');
                timelineResultsDiv.classList.remove('bg-red-50', 'border-red-300'); // Remove error style
                timelineResultsDiv.classList.add('bg-white', 'border-gray-200');
            } else {
                timelineList.innerHTML = `
                    <li class="mb-6 ml-6 text-gray-700">
                        <span class="absolute flex items-center justify-center w-3 h-3 bg-gray-100 rounded-full -left-1.5 ring-8 ring-white dark:ring-gray-900"></span>
                        <h4 class="text-lg font-semibold text-gray-900">No events found in the contract.</h4>
                    </li>
                `;
                timelineResultsDiv.classList.remove('hidden');
                timelineResultsDiv.classList.remove('bg-red-50', 'border-red-300'); // Remove error style
                timelineResultsDiv.classList.add('bg-white', 'border-gray-200');
            }
        }
    } catch (error) {
        console.error("Error during timeline generation:", error);
        timelineList.innerHTML = `
            <li class="mb-6 ml-6 text-red-700">
                <span class="absolute flex items-center justify-center w-3 h-3 bg-red-100 rounded-full -left-1.5 ring-8 ring-white dark:ring-gray-900"></span>
                <h4 class="text-lg font-semibold text-red-900">Failed to generate timeline:</h4>
                <p class="text-sm font-normal leading-none text-red-500 mt-1">${error.message}</p>
            </li>
        `;
        timelineResultsDiv.classList.remove('hidden');
        timelineResultsDiv.classList.add('bg-red-50', 'border-red-300'); // Style for error
        timelineResultsDiv.classList.remove('bg-white', 'border-gray-200');
    } finally {
        generateTimelineBtn.disabled = false;
        timelineBtnText.classList.remove('hidden');
        timelineLoadingSpinner.classList.add('hidden');
    }
};


// --- Navigation Logic ---

const updateActiveButton = () => {
    [contractReviewBtn, legalQABtn, timelineBtn].forEach(btn => {
        btn.classList.remove('active-nav-btn'); // Remove custom class
        btn.classList.remove('bg-blue-800', 'shadow-lg', 'scale-105'); // Remove Tailwind classes
        btn.classList.add('hover:bg-blue-600');
    });

    if (activeSection === 'contractReview') {
        contractReviewBtn.classList.add('active-nav-btn', 'bg-blue-800', 'shadow-lg', 'scale-105');
    } else if (activeSection === 'legalQA') {
        legalQABtn.classList.add('active-nav-btn', 'bg-blue-800', 'shadow-lg', 'scale-105');
    } else if (activeSection === 'timeline') {
        timelineBtn.classList.add('active-nav-btn', 'bg-blue-800', 'shadow-lg', 'scale-105');
    }
};

const renderActiveSection = () => {
    if (activeSection === 'contractReview') {
        renderContractReview();
    } else if (activeSection === 'legalQA') {
        renderLegalQA();
    } else if (activeSection === 'timeline') {
        renderTimeline();
    }
    updateActiveButton();
};

// Initial render
document.addEventListener('DOMContentLoaded', () => {
    renderActiveSection();

    // Attach navigation button listeners
    contractReviewBtn.addEventListener('click', () => {
        activeSection = 'contractReview';
        renderActiveSection();
    });
    legalQABtn.addEventListener('click', () => {
        activeSection = 'legalQA';
        renderActiveSection();
    });
    timelineBtn.addEventListener('click', () => {
        activeSection = 'timeline';
        renderActiveSection();
    });
});