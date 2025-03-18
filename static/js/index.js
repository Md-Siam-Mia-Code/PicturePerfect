// DOM Elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const uploadForm = document.getElementById('upload-form');
const enhanceBtn = document.getElementById('enhance-btn');
const clearBtn = document.getElementById('clear-btn');
const downloadAllBtn = document.getElementById('download-all-btn');
const progressContainer = document.getElementById('progress-container');
const originalGrid = document.getElementById('original-grid');
const enhancedGrid = document.getElementById('enhanced-grid');
const noOriginals = document.getElementById('no-originals');
const noEnhanced = document.getElementById('no-enhanced');
const themeToggle = document.getElementById('theme-toggle');
const themeMenu = document.getElementById('theme-menu');
const downloadNotification = document.getElementById('download-notification');
const downloadProgressFill = document.getElementById('download-progress-fill');
const downloadProgressPercentage = document.getElementById('download-progress-percentage');
const downloadSpeed = document.getElementById('download-speed');
const downloadingModelName = document.getElementById('downloading-model-name');
const errorNotification = document.getElementById('error-notification');
const errorMessage = document.getElementById('error-message');
const gpuNameElement = document.getElementById('gpu-name');
const halfPrecisionElement = document.getElementById('half-precision');
const gridTabs = document.querySelectorAll('.grid-tab');

// Theme functions
function toggleThemeMenu() {
    themeMenu.classList.toggle('active');
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('gfpgan-theme', theme);
    themeMenu.classList.remove('active');
}

// Load saved theme
const savedTheme = localStorage.getItem('gfpgan-theme');
if (savedTheme) {
    setTheme(savedTheme);
}

// Theme toggle event listeners
themeToggle.addEventListener('click', toggleThemeMenu);
document.querySelectorAll('.theme-option').forEach(option => {
    option.addEventListener('click', () => {
        setTheme(option.getAttribute('data-theme'));
    });
});

// File upload handling
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    handleFiles(files);
});

fileInput.addEventListener('change', () => {
    handleFiles(fileInput.files);
});

function handleFiles(files) {
    if (files.length === 0) return;

    // Update file input using DataTransfer
    const dataTransfer = new DataTransfer();
    Array.from(files).forEach(file => dataTransfer.items.add(file));
    fileInput.files = dataTransfer.files;

    // Clear no images placeholder
    noOriginals.style.display = 'none';

    // Reset form if this is a new upload
    if (originalGrid.querySelectorAll('.image-card').length === 0) {
        originalGrid.innerHTML = '';
    }

    Array.from(files).forEach(file => {
        // Create image card
        const imageCard = document.createElement('div');
        imageCard.className = 'image-card';
        imageCard.id = `uploaded-${file.name}`;

        // Create preview image
        const previewImg = document.createElement('img');
        previewImg.src = URL.createObjectURL(file);
        previewImg.className = 'image-preview';
        previewImg.alt = file.name;

        // Create actions
        const actions = document.createElement('div');
        actions.className = 'image-actions';

        // Create remove button
        const removeBtn = document.createElement('button');
        removeBtn.className = 'action-btn';
        removeBtn.innerHTML = '<span class="material-symbols-outlined">delete</span>';
        removeBtn.onclick = () => removeImage(file.name);

        // Append elements
        actions.appendChild(removeBtn);
        imageCard.appendChild(previewImg);
        imageCard.appendChild(actions);
        originalGrid.appendChild(imageCard);
    });

    // Enable enhance button
    enhanceBtn.disabled = false;

    // Show original images tab
    gridTabs.forEach(tab => {
        if (tab.getAttribute('data-tab') === 'original') {
            tab.click();
        }
    });
}

function removeImage(filename) {
    const imageElement = document.getElementById(`uploaded-${filename}`);
    if (imageElement) {
        imageElement.remove();

        // Create a new FileList without the removed file
        const dataTransfer = new DataTransfer();
        Array.from(fileInput.files)
            .filter(file => file.name !== filename)
            .forEach(file => dataTransfer.items.add(file));
        fileInput.files = dataTransfer.files;

        // Disable enhance button if no files
        if (fileInput.files.length === 0) {
            enhanceBtn.disabled = true;
            noOriginals.style.display = 'block';
        }
    }

    // Remove enhanced version if exists
    const enhancedImage = document.getElementById(`enhanced-${filename}`);
    if (enhancedImage) {
        enhancedImage.remove();

        // Show placeholder if no enhanced images
        if (enhancedGrid.querySelectorAll('.image-card').length === 0) {
            noEnhanced.style.display = 'block';
            downloadAllBtn.disabled = true;
        }
    }
}

// Form submission and enhancement
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (fileInput.files.length === 0) {
        showError('Please select at least one image to enhance');
        return;
    }

    // Show progress
    progressContainer.style.display = 'block';
    enhanceBtn.disabled = true;

    try {
        const formData = new FormData();
        Array.from(fileInput.files).forEach(file => {
            formData.append('files[]', file);
        });
        formData.append('upscale_factor', 4);

        // Send the files to the backend
        const response = await fetch('/enhance', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to enhance image');
        }

        // Handle the response
        const result = await response.json();
        const enhancedImages = result.images;

        // Clear previous enhanced images
        enhancedGrid.innerHTML = '';
        noEnhanced.style.display = 'none';

        enhancedImages.forEach(imageName => {
            // Create enhanced image card
            const imageCard = document.createElement('div');
            imageCard.className = 'image-card';
            imageCard.id = `enhanced-${imageName}`;

            // Create enhanced image preview
            const enhancedImg = document.createElement('img');
            enhancedImg.src = `/output/${imageName}`;
            enhancedImg.className = 'image-preview';
            enhancedImg.alt = `Enhanced ${imageName}`;

            // Create actions
            const actions = document.createElement('div');
            actions.className = 'image-actions';

            // Create download button
            const downloadBtn = document.createElement('button');
            downloadBtn.className = 'action-btn';
            downloadBtn.innerHTML = '<span class="material-symbols-outlined">download</span>';
            downloadBtn.onclick = () => downloadImage(`/output/${imageName}`, `enhanced_${imageName}`);

            // Append elements
            actions.appendChild(downloadBtn);
            imageCard.appendChild(enhancedImg);
            imageCard.appendChild(actions);
            enhancedGrid.appendChild(imageCard);
        });

        // Enable download all button
        downloadAllBtn.disabled = false;

        // Switch to Enhanced Images tab
        document.querySelector('[data-tab="enhanced"]').click();

    } catch (error) {
        showError(error.message || 'An error occurred during enhancement');
    } finally {
        progressContainer.style.display = 'none';
        enhanceBtn.disabled = false;
    }
});

// Download enhanced image
function downloadImage(src, filename) {
    const a = document.createElement('a');
    a.href = src;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

// Download all enhanced images
downloadAllBtn.addEventListener('click', () => {
    fetch('/download_all', {
        method: 'POST'
    })
        .then(response => {
            if (response.ok) {
                return response.blob();
            }
            throw new Error('Network response was not ok.');
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = 'Enhanced-Images.zip';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        })
        .catch(error => {
            showError('Failed to download images: ' + error.message);
        });
});


// Clear all images
clearBtn.addEventListener('click', async () => {
    try {
        const response = await fetch('/clear_history', { method: 'POST' });
        if (!response.ok) throw new Error('Failed to clear history');

        // Clear UI elements
        fileInput.value = '';
        originalGrid.innerHTML = '';
        enhancedGrid.innerHTML = '';
        noOriginals.style.display = 'block';
        noEnhanced.style.display = 'block';
        enhanceBtn.disabled = true;
        downloadAllBtn.disabled = true;
    } catch (error) {
        showError(error.message);
    }
});

// Tab switching
gridTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        // Update active tab
        gridTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        // Show corresponding grid
        const tabName = tab.getAttribute('data-tab');
        if (tabName === 'original') {
            originalGrid.style.display = 'grid';
            enhancedGrid.style.display = 'none';
        } else {
            originalGrid.style.display = 'none';
            enhancedGrid.style.display = 'grid';
        }
    });
});

// Error handling
function showError(message) {
    errorMessage.textContent = message;
    errorNotification.style.display = 'block';

    // Hide after 5 seconds
    setTimeout(() => {
        errorNotification.style.display = 'none';
    }, 5000);
}

// Initialize
progressContainer.style.display = 'none';
downloadNotification.style.display = 'none';
errorNotification.style.display = 'none';

// Close theme menu when clicking outside
document.addEventListener('click', (e) => {
    if (!themeToggle.contains(e.target) && !themeMenu.contains(e.target)) {
        themeMenu.classList.remove('active');
    }
});

// Handle keyboard events
document.addEventListener('keydown', (e) => {
    // Close theme menu on Escape key
    if (e.key === 'Escape' && themeMenu.classList.contains('active')) {
        themeMenu.classList.remove('active');
    }
});

// Trigger model initialization when the page loads
window.addEventListener('load', () => {
    initializeModels();
});

async function initializeModels() {
    const eventSource = new EventSource('/initialize_models');

    eventSource.addEventListener('message', (event) => {
        const data = JSON.parse(event.data);
        if (data.status === 'downloading') {
            downloadingModelName.textContent = `Downloading ${data.model_name}...`;
            downloadProgressPercentage.textContent = `${data.percentage}%`;
            downloadSpeed.textContent = data.speed;
            downloadProgressFill.style.width = `${data.percentage}%`;
            downloadNotification.style.display = 'block';
        }
        else if (data.status === 'ready') {
            eventSource.close();
        }
        else if (data.status === 'info') {
            gpuNameElement.textContent = data.gpu_detected;
            halfPrecisionElement.textContent = data.half_precision ? 'Yes' : 'No';
        }
    });

    eventSource.addEventListener('error', (err) => {
        // Only show error if connection was not closed normally
        if (eventSource.readyState !== EventSource.CLOSED) {
            showError('Error connecting to the server.');
            eventSource.close();
        }
    });
}