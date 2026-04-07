from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from s3_functions import upload_file, delete_file
from dynamo_functions import save_item, get_items, delete_item
from cognito_functions import verify_user

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)

# Environment Variables with Hardcoded Fallbacks for EC2 Stability
VIDEOS_BUCKET = os.environ.get('VIDEOS_BUCKET', 'video-subtitles-project-navdeep')
VIDEOS_TABLE = os.environ.get('VIDEOS_TABLE', 'videos-table')
FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
FLASK_PORT = os.environ.get('FLASK_PORT', 5000)
USER_POOL_ID = os.environ.get('USER_POOL_ID', 'ap-south-1_fsYQAHgQX')

@app.route('/send', methods=['POST'])
def send_videos():
    user_id = request.form.get('user_id')
    user_email = request.form.get('user_email')
    file_name = request.form.get('file_name')
    file_video = request.files.get('file')

    if not verify_user(USER_POOL_ID, user_id):
        return jsonify("UserNotFound"), 401

    video_id = upload_file(user_id, file_name, file_video, VIDEOS_BUCKET, 'original')
    save_item(VIDEOS_TABLE, {
        "video_id": {"S": video_id},
        "user_id": {"S": user_id},
        "user_email": {"S": user_email},
        "video_name": {"S": file_name},
        "finished": {"BOOL": False},
    }, 'video_id', {'S': video_id})

    return jsonify("Job started!"), 200

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
            videos.append(info)
    return jsonify(videos), 200

@app.route('/delete', methods=['DELETE'])
def delete_video():
    video_id = request.args.get('video_id')
    user_id = request.args.get('id') # Frontend uses 'id' for user_id in delete
    if not verify_user(USER_POOL_ID, user_id):
        return jsonify("UserNotFound"), 401
    
    delete_item(VIDEOS_TABLE, {'video_id': {'S': video_id}})
    delete_file(VIDEOS_BUCKET, 'original', video_id)
    delete_file(VIDEOS_BUCKET, 'captioned', video_id)
    return jsonify("Video Deleted!"), 200

@app.route('/', methods=['GET'])
def health():
    return json.dumps("Healthy!")

if __name__ == '__main__':
    app.run(host=FLASK_HOST, port=int(FLASK_PORT))
