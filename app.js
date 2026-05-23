let allQuestions = [];

// DOM Elements
const topicsContainer = document.getElementById('topics-container');
const nextBtn = document.getElementById('next-btn');
const showBtn = document.getElementById('show-btn');
const questionImg = document.getElementById('question-image');
const placeholderText = document.getElementById('placeholder-text');
const answerArea = document.getElementById('answer-area');
const correctAnswerSpan = document.getElementById('correct-answer');
const explanationText = document.getElementById('explanation-text');
const qInfoSpan = document.getElementById('q-info');
const qTopicBadge = document.getElementById('q-topic');

// 1. Fetch data on load
fetch('questions.json')
    .then(response => response.json())
    .then(data => {
        allQuestions = data;
        buildTopicFilters(data);
    })
    .catch(err => {
        topicsContainer.innerHTML = '<p style="color:red;">Error loading questions.json data.</p>';
        console.error(err);
    });

// 2. Dynamically extract unique topics from "Componente" key
function buildTopicFilters(data) {
    topicsContainer.innerHTML = '';
    
    // Map to "Componente" to get the topics, filter out blanks
    const topics = [...new Set(data.map(q => q.Componente).filter(Boolean))].sort();
    
    topics.forEach(topic => {
        const label = document.createElement('label');
        label.className = 'topic-label';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = topic;
        checkbox.checked = true; // Default all checkboxes to checked
        checkbox.className = 'topic-checkbox';
        
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(topic));
        topicsContainer.appendChild(label);
    });
}

// 3. Random question selector loop
nextBtn.addEventListener('click', () => {
    // Instantly hide old expansion results
    answerArea.style.display = 'none';
    
    const checkedBoxes = document.querySelectorAll('.topic-checkbox:checked');
    const selectedTopics = Array.from(checkedBoxes).map(cb => cb.value);
    
    if (selectedTopics.length === 0) {
        alert("Please select at least one topic to practice!");
        return;
    }
    
    // Filter rows by selected "Componente" values
    const filteredQuestions = allQuestions.filter(q => selectedTopics.includes(q.Componente));
    
    if (filteredQuestions.length === 0) {
        alert("No questions found for the selected topics.");
        return;
    }
    
    const randomQ = filteredQuestions[Math.floor(Math.random() * filteredQuestions.length)];
    displayQuestion(randomQ);
});

// 4. Load components and construct exact file path name convention
function displayQuestion(q) {
    placeholderText.style.display = 'none';
    
    // Force 2-digit padding on the question sequence (e.g., 5 -> "05")
    const paddedQuestao = String(q.Questao).padStart(2, '0');
    
    // Constructs: images/{Ano}/{Ano}q{paddedQuestao}.png
    const imagePath = `images/${q.Ano}/${q.Ano}q${paddedQuestao}.png`;
    
    questionImg.src = imagePath;
    questionImg.style.display = 'block';
    
    qInfoSpan.textContent = `Year ${q.Ano} — Question ${q.Questao}`;
    qTopicBadge.textContent = q.Componente;
    qTopicBadge.style.display = 'inline-block';
    
    // Update target parameters behind visibility screens
    correctAnswerSpan.textContent = q.Resposta;
    explanationText.textContent = q.explanation;
    
    showBtn.style.display = 'inline-block';
}

// 5. Reveal actions and force MathJax compilation pass
showBtn.addEventListener('click', () => {
    answerArea.style.display = 'block';
    showBtn.style.display = 'none';
    
    // Re-render LaTeX definitions seamlessly
    if (window.MathJax) {
        MathJax.typesetPromise();
    }
});
