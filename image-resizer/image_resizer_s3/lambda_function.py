import boto3
import os
import uuid
from urllib.parse import unquote_plus
from PIL import Image
import io

# Initialize S3 client
s3_client = boto3.client('s3')

# Max dimension for resizing
MAX_DIMENSION = 256

# Destination bucket from environment variable
DESTINATION_BUCKET = os.environ.get('DESTINATION_BUCKET_NAME')

def resize_image(image_path, resized_path):
    """
    Resizes image if dimensions exceed MAX_DIMENSION. Maintains aspect ratio.
    """
    try:
        with Image.open(image_path) as image:
            width, height = image.size
            print(f"Original image size: {width}x{height}")

            if width <= MAX_DIMENSION and height <= MAX_DIMENSION:
                print("Image within size limits. No resize needed.")
                return False

            if width > height:
                new_width = MAX_DIMENSION
                new_height = int(height * MAX_DIMENSION / width)
            else:
                new_height = MAX_DIMENSION
                new_width = int(width * MAX_DIMENSION / height)

            image = image.resize((new_width, new_height))
            image.save(resized_path)
            print(f"Resized image saved to: {resized_path}")
            return True

    except Exception as e:
        print(f"Resize failed: {e}")
        raise

def lambda_handler(event, context):
    if not DESTINATION_BUCKET:
        print("DESTINATION_BUCKET_NAME not set")
        return {'statusCode': 500, 'body': 'Destination bucket not configured'}

    print(f"Destination bucket: {DESTINATION_BUCKET}")

    for record in event['Records']:
        try:
            source_bucket = record['s3']['bucket']['name']
            key = unquote_plus(record['s3']['object']['key'])
            print(f"Processing file: s3://{source_bucket}/{key}")

            tmpkey = key.replace('/', '_')
            download_path = f"/tmp/{uuid.uuid4()}-{tmpkey}"
            resized_path = f"/tmp/resized-{tmpkey}"

            # Download original image
            s3_client.download_file(source_bucket, key, download_path)
            print(f"Downloaded to: {download_path}")

            # Resize image
            resized = resize_image(download_path, resized_path)

            # Determine path to upload
            path_to_upload = resized_path if resized else download_path

            # Choose content type
            content_type = 'image/jpeg'
            if key.lower().endswith('.png'):
                content_type = 'image/png'
            elif key.lower().endswith('.gif'):
                content_type = 'image/gif'

            # Optional: prefix output with 'resized/'
            destination_key = f"resized/{key}"

            # Upload image
            print(f"Uploading to s3://{DESTINATION_BUCKET}/{destination_key}")
            s3_client.upload_file(
                path_to_upload,
                DESTINATION_BUCKET,
                destination_key,
                ExtraArgs={'ContentType': content_type}
            )
            print(f"Upload complete.")


        except Exception as e:
            print(f"Error processing {key}: {e}")
        finally:
            # Clean up temporary files
            if os.path.exists(download_path):
                os.remove(download_path)
            if os.path.exists(resized_path):
                os.remove(resized_path)

    return {
        'statusCode': 200,
        'body': 'Image processing complete.'
    }
