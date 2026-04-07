import os
import json
import time
import threading
import subprocess
import requests
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

WORKING_DIR = "/home/ec2-user/workdir"

def call_gemini_raw(video_path):
    """Call Gemini using Raw HTTP Requests (No SDK needed!)"""
    try:
        print(f"Uploading {video_path} to Gemini...")
        
        # 1. Upload to Gemini File API (Initiation)
        headers_init = {
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(os.path.getsize(video_path)),
            "X-Goog-Upload-Header-Content-Type": "video/mp4",
            "Content-Type": "application/json"
        }
        upload_init_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={GEMINI_API_KEY}"
        init_body = {"file": {"display_name": os.path.basename(video_path)}}
        init_res = requests.post(upload_init_url, headers=headers_init, json=init_body)
        
        if init_res.status_code != 200:
            print(f"Gemini Init Failed ({init_res.status_code}): {init_res.text}")
            return None
            
        upload_url = init_res.headers.get("X-Goog-Upload-URL")
        
        # 2. Upload the data (Finalize)
        headers_put = {
            "X-Goog-Upload-Command": "upload, finalize",
            "X-Goog-Upload-Offset": "0",
            "Content-Length": str(os.path.getsize(video_path))
        }
        with open(video_path, 'rb') as f:
            upload_res = requests.put(upload_url, headers=headers_put, data=f)
            
        if upload_res.status_code != 200:
            print(f"Gemini Put Failed ({upload_res.status_code}): {upload_res.text}")
            return None
        
        file_info = upload_res.json()
        file_uri = file_info['file']['uri']
        file_name = file_info['file']['name']
        print(f"File uploaded! URI: {file_uri}")

        # 2. Wait for processing
        while True:
            check_res = requests.get(f"https://generativelanguage.googleapis.com/v1beta/{file_name}?key={GEMINI_API_KEY}")
            state = check_res.json().get('state')
            if state == 'ACTIVE': break
            print("Processing video in Gemini cloud...")
            time.sleep(5)

        # 3. Generate Subtitles
        prompt = {
            "contents": [{
                "parts": [
                    {"text": "Transcribe this video and provide professional subtitles in SRT format. If the audio is not in Portuguese, translate it to Portuguese. Only return the SRT content."},
                    {"fileData": {"mime_type": "video/mp4", "file_uri": file_uri}}
                ]
            }]
        }
        gen_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        gen_res = requests.post(gen_url, json=prompt)
        res_data = gen_res.json()
        
        # 4. Extract text from response
        if 'candidates' in res_data:
            srt_content = res_data['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"Gemini Generation Failed. Full Response: {json.dumps(res_data, indent=2)}")
            return None
            
        # Clean markdown if present
        srt_content = srt_content.replace('```srt', '').replace('```', '').strip()
        
        # 5. Delete temp file from Gemini server
        requests.delete(f"https://generativelanguage.googleapis.com/v1beta/{file_name}?key={GEMINI_API_KEY}")
        
        return srt_content

    except Exception as e:
        print(f"Raw Gemini Error: {e}")
        return None

def process_video_cloud(video_path, video_id, user_id, video_name, user_email):
    """Background task to process video using cloud Gemini"""
    try:
        srt_content = call_gemini_raw(video_path)
        if not srt_content: return

        # Save SRT locally
        srt_path = f"{WORKING_DIR}/{video_id}.srt"
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        # Burn subtitles using FFmpeg
        output_video_path = f"{WORKING_DIR}/{video_id}_captioned.mp4"
        subprocess.run([
            'ffmpeg', '-y', '-i', video_path, 
            '-vf', f"subtitles={srt_path}", 
            '-c:a', 'copy', output_video_path
        ], check=True)

        # Upload captioned video to S3
        with open(output_video_path, 'rb') as f:
            upload_file(user_id, video_name, f, VIDEOS_BUCKET, 'captioned')

        # Update DynamoDB
        video_uri = f"https://{VIDEOS_BUCKET}.s3.ap-south-1.amazonaws.com/captioned/{video_id}.mp4"
        save_item(VIDEOS_TABLE, {
            'video_id': {'S': video_id},
            'video_name': {'S': video_name},
            'user_id': {'S': user_id},
            'user_email': {'S': user_email},
            'finished': {'BOOL': True},
            'video_uri': {'S': video_uri},
            'duration': {'N': '0'},
            'transcription_words': {'N': str(len(srt_content.split()))},
            'translation_words': {'N': str(len(srt_content.split()))}
        }, 'video_id', {'S': video_id})
        
        print(f"Cloud processing complete for {video_id}!")
        
        # Cleanup
        os.remove(video_path)
        os.remove(srt_path)
        os.remove(output_video_path)

    except Exception as e:
        print(f"Error in Cloud Processing: {e}")

@app.route('/send', methods=['POST'])
def send_videos():
    user_id = request.form.get('user_id')
    user_email = request.form.get('user_email')
    file_name = request.form.get('file_name')
    file_video = request.files.get('file')

    if not verify_user(USER_POOL_ID, user_id):
        return jsonify("UserNotFound"), 401

    temp_id = str(int(time.time()))
    temp_path = f"{WORKING_DIR}/{temp_id}.mp4"
    if not os.path.exists(WORKING_DIR): os.makedirs(WORKING_DIR)
    file_video.save(temp_path)

    with open(temp_path, 'rb') as f:
        video_id = upload_file(user_id, file_name, f, VIDEOS_BUCKET, 'original')

    save_item(VIDEOS_TABLE, {
        "video_id": {"S": video_id},
        "user_id": {"S": user_id},
        "user_email": {"S": user_email},
        "video_name": {"S": file_name},
        "finished": {"BOOL": False},
    }, 'video_id', {'S': video_id})

    threading.Thread(target=process_video_cloud, args=(temp_path, video_id, user_id, file_name, user_email)).start()

    return jsonify("Job started with Raw Gemini Cloud!"), 200

@app.route('/list', methods=['GET'])
def list_videos():
    user_id = request.args.get('id')
    if not verify_user(USER_POOL_ID, user_id):
        return jsonify("UserNotFound"), 401
    items = get_items(VIDEOS_TABLE, 'user_id', user_id)
    videos = []
    if items:
        for d in items:
            info = {k: str(list(v.values())[0]) if isinstance(v, dict) else str(v) for k, v in d.items()}
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
    app.run(host=FLASK_HOST, port=int(FLASK_PORT))
