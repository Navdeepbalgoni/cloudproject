import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import threading
import tempfile
import boto3
import assemblyai as aai
from s3_functions import upload_file, delete_file
from dynamo_functions import save_item, get_items, delete_item, update_item
from cognito_functions import verify_user



app = Flask(__name__)
CORS(app)

# Environment Variables with Hardcoded Fallbacks for EC2 Stability
VIDEOS_BUCKET = os.environ.get('VIDEOS_BUCKET', 'video-subtitles-project-navdeep')
VIDEOS_TABLE = os.environ.get('VIDEOS_TABLE', 'videos-table')
FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
FLASK_PORT = os.environ.get('FLASK_PORT', 5000)
USER_POOL_ID = os.environ.get('USER_POOL_ID', 'ap-south-1_fsYQAHgQX')
ASSEMBLYAI_API_KEY = os.environ.get('ASSEMBLYAI_API_KEY')

def process_video_assemblyai(video_id, temp_path):
    try:
        print(f"Starting AssemblyAI transcription for {video_id}...")
        aai.settings.api_key = ASSEMBLYAI_API_KEY
        transcriber = aai.Transcriber()
        # Using the plural speech_models as required by the latest API
        config = aai.TranscriptionConfig(speech_models=["universal-3-pro"])
        
        # 1. Transcribe using AssemblyAI
        transcript = transcriber.transcribe(temp_path, config=config)





        
        if transcript.error:
            raise Exception(transcript.error)
            
        # 2. Export to SRT
        srt_content = transcript.export_subtitles_srt()
        
        # 3. Save SRT to S3
        srt_key = f"subtitles/{video_id}"
        s3_client = boto3.client('s3', region_name='ap-south-1')
        s3_client.put_object(
            Body=srt_content,
            Bucket=VIDEOS_BUCKET,
            Key=f"{srt_key}.srt",
            ContentType='text/plain'
        )
        
        # 4. Get duration from transcript (in seconds)
        duration = transcript.audio_duration
        
        # 5. Update DynamoDB
        update_item(VIDEOS_TABLE, {'video_id': {'S': video_id}}, 'finished', {'BOOL': True})
        update_item(VIDEOS_TABLE, {'video_id': {'S': video_id}}, 'srt_key', {'S': f"{srt_key}.srt"})
        update_item(VIDEOS_TABLE, {'video_id': {'S': video_id}}, 'duration', {'N': str(duration)})
        print(f"Finished processing {video_id} (AssemblyAI) with duration {duration}s.")

        
    except Exception as e:
        print(f"Error processing video {video_id} with AssemblyAI: {e}")
    finally:
        # Clean up local file
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.route('/send', methods=['POST'])
def send_videos():
    user_id = request.form.get('user_id')
    user_email = request.form.get('user_email')
    file_name = request.form.get('file_name')
    file_video = request.files.get('file')

    if not verify_user(USER_POOL_ID, user_id):
        return jsonify("UserNotFound"), 401

    # Save to temp for Whisper
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"temp_{os.urandom(8).hex()}.mp4")
    file_video.save(temp_path)
    
    # Reset pointer for S3 upload
    file_video.seek(0)

    video_id = upload_file(user_id, file_name, file_video, VIDEOS_BUCKET, 'original')
    
    if not video_id:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify("Upload failed"), 500

    save_item(VIDEOS_TABLE, {
        "video_id": {"S": video_id},
        "user_id": {"S": user_id},
        "user_email": {"S": user_email},
        "video_name": {"S": file_name},
        "finished": {"BOOL": False},
    }, 'video_id', {'S': video_id})

    # Start AssemblyAI process in background
    threading.Thread(target=process_video_assemblyai, args=(video_id, temp_path)).start()


    return jsonify("Job started! Subtitles are being generated."), 200

def create_presigned_url(bucket_name, file_key):
    s3_client = boto3.client('s3', region_name='ap-south-1')
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': file_key,
                'ResponseContentDisposition': 'attachment'
            },
            ExpiresIn=3600
        )
        return url
    except Exception as e:
        print(f"Error generating presigned URL for {file_key}: {e}")
        return None

@app.route('/list', methods=['GET'])
def list_videos():
    user_id = request.args.get('id')
    if not verify_user(USER_POOL_ID, user_id):
        return jsonify("UserNotFound"), 401

    items = get_items(VIDEOS_TABLE, 'user_id', user_id)
    videos = []
    if items:
        for d in items:
            # Clean up DynamoDB formatting for frontend
            info = {k: str(list(v.values())[0]) if isinstance(v, dict) else str(v) for k, v in d.items()}
            
            # Generate presigned URLs
            video_id = info.get('video_id')
            if video_id:
                # Video URL (original)
                info['video_uri'] = create_presigned_url(VIDEOS_BUCKET, f'original/{video_id}.mp4')
                # SRT URL (if finished)
                if info.get('finished') == 'True':
                    info['srt_uri'] = create_presigned_url(VIDEOS_BUCKET, f'subtitles/{video_id}.srt')
            
            videos.append(info)
    return jsonify(videos), 200


@app.route('/delete', methods=['DELETE'])
def delete_video():
    video_id = request.args.get('video_id')
    user_id = request.args.get('user_id') 
    if not verify_user(USER_POOL_ID, user_id):
        return jsonify("UserNotFound"), 401

    
    delete_item(VIDEOS_TABLE, {'video_id': {'S': video_id}})
    delete_file(VIDEOS_BUCKET, 'original', video_id)
    delete_file(VIDEOS_BUCKET, 'captioned', video_id)
    delete_file(VIDEOS_BUCKET, 'subtitles', video_id, extension='srt')
    return jsonify("Video Deleted!"), 200


@app.route('/', methods=['GET'])
def health():
    return json.dumps("Healthy!")

if __name__ == '__main__':
    app.run(host=FLASK_HOST, port=int(FLASK_PORT))

