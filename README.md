# AWS Serverless Image Upload and Resize

## Project Goal

This project demonstrates a serverless approach to handling image uploads via a static website. Users can upload an image (JPG/PNG/JPEG/GIF), which is then automatically resized by AWS backend services, and a download link for the resized version is provided.

## Technical Workflow

The process leverages several AWS services orchestrated via API Gateway and Lambda:

1.  **Static Website (AWS S3):** The user interacts with an HTML/CSS/JavaScript frontend hosted as a static website on an S3 bucket (`shayan-image-uploader-web`).
2.  **API Request (API Gateway + Lambda #1):**
    *   When the user selects a file and clicks "Upload", the JavaScript sends a request containing the filename and content type to an API Gateway endpoint (`/generate-upload-url`).
    *   This triggers the Lambda function code inside of `generate_upload_url` folder.
    *   This Lambda function **does not handle image data directly**. It generates two S3 Presigned URLs:
        *   A `PUT` URL allowing the browser to upload the original image directly to the source bucket (`shayan-image-uploads-source`) under a unique key (e.g., `uploads/...`).
        *   A `GET` URL that will allow the browser to download the resized image *later* from the destination bucket (`shayan-image-resized-destination`), using a predicted key (e.g., `resized/...`).
    *   These two URLs are returned to the browser.
3.  **Direct S3 Upload (Browser -> S3):**
    *   The JavaScript uses the received presigned `PUT` URL to upload the image file's raw data directly from the browser to the `shayan-image-uploads-source` S3 bucket. This bypasses API Gateway/Lambda for the heavy lifting of the upload.
4.  **S3 Trigger (S3 -> Lambda #2):**
    *   The successful upload of the original image into the `shayan-image-uploads-source` bucket automatically triggers the Lambda function code inside of `image_resizer_s3` folder (configured via S3 Event Notifications).
5.  **Image Resizing (Lambda #2):**
    *   The `S3TriggeredResizeFunction` downloads the original image from the source bucket.
    *   It uses the Pillow (PIL) library to resize the image to predefined dimensions (e.g., max width 256px, maintaining aspect ratio).
    *   It uploads the *resized* image file to the `shayan-image-resized-destination` S3 bucket, using the key structure predicted by the first Lambda function.
6.  **Download Link Activation (Frontend):**
    *   Once the direct S3 upload (Step 3) completes, the JavaScript displays the download link (using the presigned `GET` URL received in Step 2).
    *   **Important:** A short delay is implemented before the download link becomes clickable. This allows time for the asynchronous resize process (Steps 4-5) to complete in the background.
7.  **Download (Browser -> S3):**
    *   When the user clicks the activated download link, the browser uses the presigned `GET` URL to fetch the resized image directly from the `shayan-image-resized-destination` bucket.

## How to Use the Static Website

1.  Navigate to the static website hosting URL: `http://shayan-image-uploader-web.s3-website.us-east-2.amazonaws.com`.
2.  Click the "Choose File" button and select a JPG/JPEG/PNG image from your local machine.
3.  Click the "Upload Image" button.
4.  Observe the status messages and the progress bar indicating the direct upload to S3.
5.  Once the upload completes, the status will indicate processing, and a download link will appear (initially greyed out/disabled).
6.  Wait a few seconds for the link to become active (the status message will update).
7.  Click the download link to save the resized image.

## Important Notes

*   **Asynchronous Processing:** The image resizing happens in the background *after* the initial upload completes. The delay before the download link activates is necessary to account for this processing time. Without the delay, clicking the link too early would result in an error as the resized file wouldn't exist yet.
*   **Ad Blockers / Browser Extensions:** Some browser extensions (particularly content/ad blockers or privacy tools like `FilterContent`) may interfere with the JavaScript execution or the direct S3 upload/download process. They can sometimes cause console errors that are unrelated to the application's core logic. If you encounter unexpected issues, try testing in an Incognito/Private window or temporarily disabling extensions.
*   **Error Handling:** Basic error handling is implemented, but a production-ready application would require more comprehensive checks and user feedback mechanisms.

---
