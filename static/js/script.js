// DOM Elements
const form = document.getElementById('moodForm');
const resultsSection = document.getElementById('results');
const submitBtn = document.querySelector('.submit-btn');
const btnText = document.querySelector('.btn-text');
const loadingSpinner = document.querySelector('.loading-spinner');

// Form submission handler
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Show loading state
    showLoading();
    
    // Collect form data
    const formData = new FormData(form);
    const data = {
        name: formData.get('name'),
        mood: formData.get('mood'),
        feelings: formData.get('feelings'),
        time_of_day: formData.get('time_of_day'),
        language: formData.get('language'),
        genres: formData.get('genres'),
        artists: formData.get('artists')
    };
    
    try {
        // Send data to backend
        const response = await fetch('/analyze_mood', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayResults(result);
        } else {
            showError(result.error || 'Something went wrong. Please try again.');
        }
        
    } catch (error) {
        console.error('Error:', error);
        showError('Network error. Please check your connection and try again.');
    } finally {
        hideLoading();
    }
});

// Show loading state
function showLoading() {
    btnText.style.display = 'none';
    loadingSpinner.style.display = 'block';
    submitBtn.disabled = true;
}

// Hide loading state
function hideLoading() {
    btnText.style.display = 'block';
    loadingSpinner.style.display = 'none';
    submitBtn.disabled = false;
}

// Display results
function displayResults(data) {
    // Update playlist name and analysis
    document.getElementById('playlistName').textContent = data.playlist_name;
    document.getElementById('moodAnalysis').textContent = data.mood_analysis;
    
    // Create playlist container
    const playlistContainer = document.getElementById('playlist');
    playlistContainer.innerHTML = '';
    
    // Add Spotify embeds
    data.embed_urls.forEach((embedUrl, index) => {
        const embedDiv = document.createElement('div');
        embedDiv.className = 'spotify-embed';
        embedDiv.innerHTML = `
            <iframe 
                src="${embedUrl}?utm_source=generator&theme=0" 
                width="100%" 
                height="152" 
                frameborder="0" 
                allowfullscreen="" 
                allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" 
                loading="lazy">
            </iframe>
        `;
        playlistContainer.appendChild(embedDiv);
    });
    
    // Show results section
    resultsSection.style.display = 'block';
    
    // Smooth scroll to results
    resultsSection.scrollIntoView({ 
        behavior: 'smooth',
        block: 'start'
    });
}

// Show error message
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.style.cssText = `
        background: rgba(255, 107, 107, 0.1);
        border: 1px solid rgba(255, 107, 107, 0.3);
        color: #ff6b6b;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
        backdrop-filter: blur(10px);
    `;
    errorDiv.textContent = message;
    
    // Remove existing error messages
    const existingError = document.querySelector('.error-message');
    if (existingError) {
        existingError.remove();
    }
    
    // Insert error message after form
    form.parentNode.insertBefore(errorDiv, form.nextSibling);
    
    // Auto-remove error after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.remove();
        }
    }, 5000);
}

// Form validation
function validateForm() {
    const requiredFields = ['name', 'mood', 'time_of_day', 'language'];
    let isValid = true;
    
    requiredFields.forEach(field => {
        const element = document.getElementById(field);
        if (!element.value.trim()) {
            element.style.borderColor = '#ff6b6b';
            isValid = false;
        } else {
            element.style.borderColor = 'rgba(255, 255, 255, 0.3)';
        }
    });
    
    return isValid;
}

// Add real-time validation
document.querySelectorAll('input, select, textarea').forEach(element => {
    element.addEventListener('blur', () => {
        if (element.hasAttribute('required') && !element.value.trim()) {
            element.style.borderColor = '#ff6b6b';
        } else {
            element.style.borderColor = 'rgba(255, 255, 255, 0.3)';
        }
    });
    
    element.addEventListener('input', () => {
        if (element.style.borderColor === 'rgb(255, 107, 107)') {
            element.style.borderColor = 'rgba(255, 255, 255, 0.3)';
        }
    });
});