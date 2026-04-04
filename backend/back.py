import os
import json
import time
import threading
import subprocess
import google.generativeai as genai
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
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
USER_POOL_ID = os.environ.get('USER_POOL_ID')
FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
FLASK_PORT = os.environ.get('FLASK_PORT', 5000)

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY, transport='rest')
model = genai.GenerativeModel('models/gemini-1.5-flash')

def process_video_gemini(video_path, video_id, user_id, video_name, user_email):
    """Background task to process video using Gemini AI"""
    try:
        print(f"Starting Gemini processing for {video_id}")
        
        # 1. Upload to Gemini for analysis
        video_file = genai.upload_file(path=video_path)
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)

        # 2. Ask Gemini for SRT subtitles
        prompt = "Transcribe this video and provide professional subtitles in SRT format. If the audio is not in Portuguese, translate it to Portuguese. Only return the SRT content."
        response = model.generate_content([video_file, prompt])
        srt_content = response.text

        # 3. Save SRT locally
        srt_path = f"/tmp/{video_id}.srt"
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        # 4. Burn subtitles using FFmpeg
        output_video_path = f"/tmp/{video_id}_captioned.mp4"
        # Command: ffmpeg -i input.mp4 -vf "subtitles=subs.srt" output.mp4
        subprocess.run([
            'ffmpeg', '-y', '-i', video_path, 
            '-vf', f"subtitles={srt_path}", 
            '-c:a', 'copy', output_video_path
        ], check=True)

        # 5. Upload captioned video to S3
        with open(output_video_path, 'rb') as f:
            upload_file(user_id, video_name, f, VIDEOS_BUCKET, 'captioned')

        # 6. Update DynamoDB to finished
        video_uri = f"https://{VIDEOS_BUCKET}.s3.ap-south-1.amazonaws.com/captioned/{video_id}.mp4"
        updated_item = {
            'video_id': {'S': video_id},
            'video_name': {'S': video_name},
            'user_id': {'S': user_id},
            'user_email': {'S': user_email},
            'finished': {'BOOL': True},
            'video_uri': {'S': video_uri},
            'duration': {'N': '0'}, # Placeholder
            'transcription_words': {'N': str(len(srt_content.split()))},
            'translation_words': {'N': str(len(srt_content.split()))}
        }
        save_item(VIDEOS_TABLE, updated_item, 'video_id', {'S': video_id})
        
        print(f"Processing complete for {video_id}!")
        
        # Cleanup
        os.remove(video_path)
        os.remove(srt_path)
        os.remove(output_video_path)
        genai.delete_file(video_file.name)

    except Exception as e:
        print(f"Error in Gemini Processing: {e}")

@app.route('/send', methods=['POST'])
def send_videos():
    user_id = request.form.get('user_id')
    user_email = request.form.get('user_email')
    file_name = request.form.get('file_name')
    file_video = request.files.get('file')

    if not verify_user(USER_POOL_ID, user_id):
        return jsonify("UserNotFound"), 401

    # Save locally temporarily
    temp_id = str(int(time.time()))
    temp_path = f"/tmp/{temp_id}.mp4"
    file_video.save(temp_path)

    # Upload original to S3
    with open(temp_path, 'rb') as f:
        video_id = upload_file(user_id, file_name, f, VIDEOS_BUCKET, 'original')

    # Initial DynamoDB entry
    video_info = {
        "video_id": {"S": video_id},
        "user_id": {"S": user_id},
        "user_email": {"S": user_email},
        "video_name": {"S": file_name},
        "finished": {"BOOL": False},
    }
    save_item(VIDEOS_TABLE, video_info, 'video_id', {'S': video_id})

    # Start Gemini processing in background
    thread = threading.可靠_thread = threading.Thread(target=process_video_gemini, args=(temp_path, video_id, user_id, file_name, user_email))
    thread.start()

    return jsonify("Job started with Gemini AI!"), 200

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
