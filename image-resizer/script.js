const uploadForm = document.getElementById('uploadForm');
const imageFile = document.getElementById('imageFile');
const statusDiv = document.getElementById('status');
const downloadLink = document.getElementById('downloadLink');
const progressBar = document.getElementById('progressBar');
const progressBarInner = document.getElementById('progressBarInner');

// IMPORTANT: Replace with your API Gateway Invoke URL for the *new* endpoint
const apiUrl = 'https://555lumuotj.execute-api.us-east-1.amazonaws.com/v1/generate-upload-url'; // Your actual API endpoint

uploadForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const file = imageFile.files[0];
    if (!file) {
        statusDiv.textContent = 'Please select a file first.';
        statusDiv.style.color = 'red';
        return;
    }

    // Basic validation
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif']; // Add gif if needed
    if (!allowedTypes.includes(file.type)) {
        statusDiv.textContent = `Please select a supported image type (${allowedTypes.join(', ')}).`;
        statusDiv.style.color = 'red';
        return;
    }

    statusDiv.textContent = 'Requesting upload URL...';
    statusDiv.style.color = 'black';
    downloadLink.style.display = 'none';
    progressBar.style.display = 'none';
    progressBarInner.style.width = '0%';
    progressBarInner.textContent = '';

    try {
        // 1. Get Presigned URLs from your API
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                filename: file.name,
                contentType: file.type // Send content type to Lambda
            }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Failed to get upload URL. Server responded badly.' }));
            throw new Error(`Failed to get upload URL: ${response.status} ${response.statusText} - ${errorData.error || ''}`);
        }

        const { uploadUrl, downloadUrl } = await response.json();
        console.log("Received upload URL:", uploadUrl);
        console.log("Received download URL:", downloadUrl);

        statusDiv.textContent = 'Uploading image directly to S3...';
        progressBar.style.display = 'block';
        progressBarInner.textContent = '0%';

        // 2. Upload the file DIRECTLY to S3 using the presigned PUT URL
        const xhr = new XMLHttpRequest();
        xhr.open('PUT', uploadUrl, true); // Use PUT for presigned upload URL

        xhr.setRequestHeader('Content-Type', file.type); // Set correct Content-Type for S3

        xhr.upload.addEventListener('progress', (event) => {
            if (event.lengthComputable) {
                const percentComplete = Math.round((event.loaded / event.total) * 100);
                progressBarInner.style.width = percentComplete + '%';
                progressBarInner.textContent = percentComplete + '%';
            }
        });

        xhr.onload = function () {
            progressBar.style.display = 'none'; // Hide progress bar

            if (xhr.status === 200 || xhr.status === 204) { // S3 PUT often returns 200 or 204
                // --- START: Added Timeout Logic ---
                statusDiv.textContent = 'Upload complete! Processing image... Download link will be active shortly.'; // New message
                statusDiv.style.color = 'blue'; // Use a processing color

                downloadLink.href = downloadUrl; // Set the URL
                downloadLink.setAttribute('download', 'resized-' + file.name); // Suggest a filename for download
                downloadLink.style.display = 'block'; // Show the link
                downloadLink.style.pointerEvents = 'none'; // Disable clicking initially
                downloadLink.style.opacity = '0.5';      // Make it look disabled visually

                // Enable the link after a delay (e.g., 7 seconds = 7000 milliseconds)
                // Adjust this delay based on typical resize function execution time
                const delayMilliseconds = 7000;
                setTimeout(() => {
                    statusDiv.textContent = 'Upload complete! Resized image download link is active.'; // Update status
                    statusDiv.style.color = 'green'; // Back to green
                    downloadLink.style.pointerEvents = 'auto'; // Re-enable clicking
                    downloadLink.style.opacity = '1.0';       // Make it look enabled
                    console.log(`Download link enabled after ${delayMilliseconds}ms delay.`);
                }, delayMilliseconds);
                // --- END: Added Timeout Logic ---

            } else {
                // Error handling for S3 upload failure (remains the same)
                console.error('S3 Upload failed:', xhr.status, xhr.statusText, xhr.responseText);
                let s3Error = 'Check browser console for S3 error details.';
                if (xhr.responseText) {
                    try {
                       const errorMatch = xhr.responseText.match(/<Message>(.*?)<\/Message>/);
                       if (errorMatch && errorMatch[1]) {
                           s3Error = errorMatch[1];
                       }
                    } catch (parseError) { console.error("Couldn't parse S3 error XML"); }
                }
                 statusDiv.textContent = `Direct S3 upload failed. Status: ${xhr.status}. Error: ${s3Error}`;
                 statusDiv.style.color = 'red';
            }
        };

        xhr.onerror = function () {
             progressBar.style.display = 'none';
            console.error('Network error during S3 upload:', xhr.statusText);
            statusDiv.textContent = 'S3 Upload failed due to network error or CORS issue on S3 bucket (check S3 CORS config for PUT).';
            statusDiv.style.color = 'red';
        };

        // Send the raw file data
        xhr.send(file);

    } catch (error) {
        console.error('Error during process:', error);
        statusDiv.textContent = `An error occurred: ${error.message}`;
        statusDiv.style.color = 'red';
        progressBar.style.display = 'none';
    }
});