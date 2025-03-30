// Function to enable editing of fields
function enableEditing(fieldId) {
    document.getElementById(fieldId).removeAttribute('readonly');
    document.getElementById(fieldId).focus();
}

// Function to format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Function to handle file selection
document.getElementById('uploadImage').addEventListener('change', function() {
    const file = this.files[0];
    const submitButton = document.getElementById('submitUpload');
    const fileInfo = document.getElementById('fileInfo');
    
    if (file) {
        // Check file size (max 5MB)
        const maxSize = 5 * 1024 * 1024; // 5MB in bytes
        if (file.size > maxSize) {
            showFlashMessage('File size too large. Maximum size is 5MB', 'danger');
            fileInfo.textContent = 'No file chosen';
            submitButton.setAttribute('disabled', 'disabled');
            return;
        }

        // Show file information
        fileInfo.textContent = `${file.name} (${formatFileSize(file.size)})`;
        submitButton.removeAttribute('disabled');
        
        // Preview image
        const reader = new FileReader();
        reader.onload = function(event) {
            document.getElementById('profileImage').src = event.target.result;
        };
        reader.onerror = function(error) {
            console.error('Error reading file:', error);
            showFlashMessage('Error reading file. Please try again.', 'danger');
            fileInfo.textContent = 'No file chosen';
            submitButton.setAttribute('disabled', 'disabled');
        };
        reader.readAsDataURL(file);
    } else {
        fileInfo.textContent = 'No file chosen';
        submitButton.setAttribute('disabled', 'disabled');
    }
});

// Function to handle image upload
document.getElementById('submitUpload').addEventListener('click', function() {
    const fileInput = document.getElementById('uploadImage');
    const file = fileInput.files[0];
    
    if (!file) {
        showFlashMessage('Please select a file first', 'danger');
        return;
    }

    // Show loading state
    const submitButton = this;
    const originalText = submitButton.innerHTML;
    submitButton.innerHTML = '<i class="ri-loader-4-line"></i> Uploading...';
    submitButton.setAttribute('disabled', 'disabled');
    document.getElementById('profileImage').style.opacity = '0.5';

    const reader = new FileReader();
    reader.onload = function(event) {
        saveImageToDB(event.target.result, submitButton, originalText);
    };
    reader.onerror = function(error) {
        console.error('Error reading file:', error);
        showFlashMessage('Error reading file. Please try again.', 'danger');
        submitButton.innerHTML = originalText;
        submitButton.removeAttribute('disabled');
        document.getElementById('profileImage').style.opacity = '1';
    };
    reader.readAsDataURL(file);
});

// Function to save image to MySQL
function saveImageToDB(imgData, submitButton, originalButtonText) {
    // Validate image data
    if (!imgData) {
        console.error('No image data provided');
        showFlashMessage('Error: No image data provided', 'danger');
        return;
    }

    // Log the size of the data being sent
    console.log('Image data size:', (imgData.length * 0.75) / 1024 / 1024, 'MB');

    fetch('/auth/save-profile-image', {  // Updated URL with /auth prefix
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imgData })
    })
    .then(response => {
        if (!response.ok) {
            return response.text().then(text => {
                throw new Error(`Server responded with ${response.status}: ${text}`);
            });
        }
        return response.json();
    })
    .then(data => {
        // Reset UI state
        document.getElementById('profileImage').style.opacity = '1';
        submitButton.innerHTML = originalButtonText;
        submitButton.setAttribute('disabled', 'disabled');
        document.getElementById('fileInfo').textContent = 'No file chosen';
        document.getElementById('uploadImage').value = '';

        if (data.success) {
            showFlashMessage('Image uploaded successfully!', 'success');
            // Reload the profile image to show the new one
            const profileImage = document.getElementById('profileImage');
            profileImage.src = '/auth/get_profile_image?' + new Date().getTime();
        } else {
            console.error('Server error:', data.message);
            showFlashMessage('Failed to upload image: ' + data.message, 'danger');
            // Reset image to previous state
            const profileImage = document.getElementById('profileImage');
            profileImage.src = profileImage.getAttribute('data-original-src') || profileImage.src;
        }
    })
    .catch(error => {
        console.error('Upload error:', error);
        document.getElementById('profileImage').style.opacity = '1';
        submitButton.innerHTML = originalButtonText;
        submitButton.removeAttribute('disabled');
        showFlashMessage('Error uploading image: ' + error.message, 'danger');
        // Reset image to previous state
        const profileImage = document.getElementById('profileImage');
        profileImage.src = profileImage.getAttribute('data-original-src') || profileImage.src;
    });
}

// Function to save profile data to the server and local storage
document.querySelector('.save-button').addEventListener('click', function(event) {
    event.preventDefault(); // Prevent default form submission

    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;

    // Prepare FormData
    const formData = new FormData();
    formData.append('name', name);
    formData.append('email', email);

    // Send data to server
    fetch('/profile', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Save data in local storage
            localStorage.setItem('profileName', name);
            localStorage.setItem('profileEmail', email);
            showFlashMessage('Profile updated successfully!', 'success');
        } else {
            showFlashMessage('Failed to update profile. Please try again.', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showFlashMessage('An error occurred. Please try again later.', 'danger');
    });
});

// Function to display flash messages
function showFlashMessage(message, category) {
    const flashContainer = document.createElement('div');
    flashContainer.className = `flash-message ${category}`;
    flashContainer.textContent = message;

    // Find or create flash container
    let container = document.querySelector('.flash-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'flash-container';
        document.querySelector('.profile-section').insertBefore(container, document.querySelector('.profile-header'));
    }

    // Add the new message
    container.appendChild(flashContainer);

    // Automatically hide the flash message after 3 seconds
    setTimeout(() => {
        flashContainer.style.opacity = '0';
        setTimeout(() => {
            flashContainer.remove();
            // Remove container if empty
            if (!container.children.length) {
                container.remove();
            }
        }, 500); // Delay for smooth transition
    }, 3000);
}

// Store original image source when page loads
document.addEventListener('DOMContentLoaded', function() {
    const profileImage = document.getElementById('profileImage');
    if (profileImage) {
        profileImage.setAttribute('data-original-src', profileImage.src);
    }
});