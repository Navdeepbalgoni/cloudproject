import os
import json
import time
import threading
import subprocess
import whisper
from flask import Flask, request, jsonify
from flask_cors import CORS
from s3_functions import upload_file, delete_file
from dynamo_functions import save_item, get_items, delete_item
from cognito_functions import verify_user
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Environment Variables
VIDEOS_BUCKET = os.environ.get('VIDEOS_BUCKET')
VIDEOS_TABLE = os.environ.get('VIDEOS_TABLE')
USER_POOL_ID = os.environ.get('USER_POOL_ID')
FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
FLASK_PORT = os.environ.get('FLASK_PORT', 5000)

# Initialize Whisper (using 'tiny' model for EC2 performance)
print("Loading Whisper AI...")
whisper_model = whisper.load_model("tiny")
print("Whisper Loaded!")

def seconds_to_srt_time(seconds):
    """Helper to convert seconds to SRT timestamp format"""
    td = time.gmtime(seconds)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{time.strftime('%H:%M:%S', td)},{ms:03d}"

def process_video_whisper(video_path, video_id, user_id, video_name, user_email):
    """Background task to process video using local Whisper AI"""
    try:
        print(f"Starting local AI processing for {video_id}")
        
        # 1. Transcribe using local Whisper
        result = whisper_model.transcribe(video_path)
        segments = result['segments']
        
        # 2. Format into SRT
        srt_content = ""
        for i, segment in enumerate(segments):
            start = seconds_to_srt_time(segment['start'])
            end = seconds_to_srt_time(segment['end'])
            text = segment['text'].strip()
            srt_content += f"{i+1}\n{start} --> {end}\n{text}\n\n"

        # 3. Save SRT locally
        srt_path = f"/tmp/{video_id}.srt"
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        # 4. Burn subtitles using FFmpeg
        output_video_path = f"/tmp/{video_id}_captioned.mp4"
        subprocess.run([
            'ffmpeg', '-y', '-i', video_path, 
            '-vf', f"subtitles={srt_path}", 
            '-c:a', 'copy', output_video_path
        ], check=True)

        # 5. Upload captioned video to S3
        with open(output_video_path, 'rb') as f:
            upload_file(user_id, video_name, f, VIDEOS_BUCKET, 'captioned')

        # 6. Update DynamoDB
        video_uri = f"https://{VIDEOS_BUCKET}.s3.ap-south-1.amazonaws.com/captioned/{video_id}.mp4"
        updated_item = {
            'video_id': {'S': video_id},
            'video_name': {'S': video_name},
            'user_id': {'S': user_id},
            'user_email': {'S': user_email},
            'finished': {'BOOL': True},
            'video_uri': {'S': video_uri},
            'duration': {'N': str(int(result.get('duration', 0)))},
            'transcription_words': {'N': str(len(result['text'].split()))},
            'translation_words': {'N': str(len(result['text'].split()))} # Identical for now
        }
        save_item(VIDEOS_TABLE, updated_item, 'video_id', {'S': video_id})
        
        print(f"Local processing complete for {video_id}!")
        
        # Cleanup
        os.remove(video_path)
        os.remove(srt_path)
        os.remove(output_video_path)

    except Exception as e:
        print(f"Error in Local Whisper Processing: {e}")

@app.route('/send', methods=['POST'])
def send_videos():
    user_id = request.form.get('user_id')
    user_email = request.form.get('user_email')
    file_name = request.form.get('file_name')
    file_video = request.files.get('file')

    if not verify_user(USER_POOL_ID, user_id):
        return jsonify("UserNotFound"), 401

    temp_id = str(int(time.time()))
    temp_path = f"/tmp/{temp_id}.mp4"
    file_video.save(temp_path)

    with open(temp_path, 'rb') as f:
        video_id = upload_file(user_id, file_name, f, VIDEOS_BUCKET, 'original')

    video_info = {
        "video_id": {"S": video_id},
        "user_id": {"S": user_id},
        "user_email": {"S": user_email},
        "video_name": {"S": file_name},
        "finished": {"BOOL": False},
    }
    save_item(VIDEOS_TABLE, video_info, 'video_id', {'S': video_id})

    thread = threading.Thread(target=process_video_whisper, args=(temp_path, video_id, user_id, file_name, user_email))
    thread.start()

    return jsonify("Job started with Local Whisper AI!"), 200

@app.route('/list', methods=['GET'])
def list_videos():
    user_id = request.args.get('id')
    if not verify_user(USER_POOL_ID, user_id):
        return jsonify("UserNotFound"), 401
    items = get_items(VIDEOS_TABLE, 'user_id', user_id)
    videos = []
    if items:
        for d in items:
            info = {}
            for k, v in d.items():
                info[k] = str(v)
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
    return jsonify("Deleted!"), 200

@app.route('/', methods=['GET'])
def health():
    return json.dumps("Healthy!")

if __name__ == '__main__':
    app.run(host=FLASK_HOST, port=FLASK_PORT)
