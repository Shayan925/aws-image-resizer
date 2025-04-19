import json
import boto3
import os
import uuid
import time

s3 = boto3.client('s3')

# Get bucket names from environment variables
SOURCE_BUCKET = os.environ.get('SOURCE_BUCKET')
DESTINATION_BUCKET = os.environ.get('DESTINATION_BUCKET')
# Get your website origin for CORS
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN')

def lambda_handler(event, context):
    if not SOURCE_BUCKET or not DESTINATION_BUCKET or not ALLOWED_ORIGIN:
         print("Error: Missing environment variables (SOURCE_BUCKET, DESTINATION_BUCKET, ALLOWED_ORIGIN)")
         return {
            'statusCode': 500,
            'headers': {
                 # Use '*' for errors if ALLOWED_ORIGIN isn't set, but ideally set it
                'Access-Control-Allow-Origin': ALLOWED_ORIGIN or '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps({'error': 'Server configuration error.'})
         }

    try:
        print("Received event:", json.dumps(event))

        # Expect body like: {"filename": "myimage.jpg", "contentType": "image/jpeg"}
        body = json.loads(event.get('body', '{}'))
        original_filename = body.get('filename')
        content_type = body.get('contentType') # Get content type from request

        if not original_filename or not content_type:
            raise ValueError("Missing 'filename' or 'contentType' in request body.")

        # Generate a unique identifier for this upload session
        unique_id = f"{int(time.time())}-{uuid.uuid4()}"
        file_extension = os.path.splitext(original_filename)[1].lower()

        # Define keys for source and destination
        # IMPORTANT: The structure here MUST align with what your S3-triggered function uses
        source_key = f"uploads/{unique_id}{file_extension}"
        # Assuming your resize function puts files under 'resized/' prefix and keeps the unique part
        # Example: if source is uploads/123-abc.jpg -> destination is resized/uploads/123-abc.jpg
        # Adjust destination_key if your S3 trigger function saves differently!
        # Based on your S3 function using "resized/{key}", where key includes "uploads/",
        # the destination key might look like this:
        destination_key = f"resized/{source_key}"

        print(f"Source key: {source_key}")
        print(f"Predicted destination key: {destination_key}")

        # Generate Presigned URL for Uploading to Source Bucket
        # Note: ContentType must match what the client will send in the PUT request header
        upload_params = {
            'Bucket': SOURCE_BUCKET,
            'Key': source_key,
            'ContentType': content_type # Critical: Ensure client sends this exact Content-Type
        }
        # Add ACL if your bucket requires it (usually not needed with default bucket ownership)
        # upload_params['ACL'] = 'bucket-owner-full-control'

        upload_url = s3.generate_presigned_url(
            'put_object',
            Params=upload_params,
            ExpiresIn=600  # URL expires in 10 minutes
        )
        print(f"Generated upload URL: {upload_url}")

        # Generate Presigned URL for Downloading from Destination Bucket
        # This URL will initially likely give 404 until the resize function completes
        download_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': DESTINATION_BUCKET, 'Key': destination_key},
            ExpiresIn=3600  # URL expires in 1 hour
        )
        print(f"Generated download URL: {download_url}")

        # Return URLs to the client
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
                # Optional: Expose headers if needed by client JS
                # 'Access-Control-Expose-Headers': 'Some-Custom-Header'
            },
            'body': json.dumps({
                'uploadUrl': upload_url,
                'downloadUrl': download_url,
                'destinationKey': destination_key # Send key for reference if needed
            })
        }

    except ValueError as ve:
         print(f"Value Error: {ve}")
         return {
            'statusCode': 400, # Bad Request
             'headers': { 'Access-Control-Allow-Origin': ALLOWED_ORIGIN },
            'body': json.dumps({'error': str(ve)})
         }
    except Exception as e:
        print(f"Error generating URLs: {e}")
        # import traceback
        # traceback.print_exc()
        return {
            'statusCode': 500,
             'headers': { 'Access-Control-Allow-Origin': ALLOWED_ORIGIN },
            'body': json.dumps({'error': f'Failed to process request: {str(e)}'})
        }