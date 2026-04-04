import json
import os
from urllib import request

VIDEO_BUCKET = os.environ.get('VIDEO_BUCKET')
TRANSLATE_BUCKET = os.environ.get('TRANSLATE_BUCKET')
CAPTION_API = os.environ.get('CAPTION_API')


def lambda_handler(event, context):

    response = {
        'statusCode': 200,
        'body': json.dumps('Hello from Caption Lambda!')
    }

    if event:
        file_obj = event['Records'][0]
        bucket_name = str(file_obj['s3']['bucket']['name'])
        file_name = str(file_obj['s3']['object']['key'])

        _, file_name = os.path.split(file_name)
        file_name, _ = os.path.splitext(file_name)
        region = os.environ.get('AWS_REGION', 'ap-south-1')
        target_lang = os.environ.get('TARGET_LANGUAGE', 'pt')
        source_lang = os.environ.get('SOURCE_LANGUAGE', 'en')
        video_id = file_name.replace(f'-{target_lang}', '')

        original_video = '{}/original/{}.mp4'.format(VIDEO_BUCKET, video_id)
        transcription = '{}/{}/{}-{}.vtt'.format(TRANSLATE_BUCKET, source_lang, video_id, source_lang)
        translation = '{}/{}/{}-{}.vtt'.format(TRANSLATE_BUCKET, target_lang, video_id, target_lang)
        captioned_video = '{}/captioned/{}.mp4'.format(VIDEO_BUCKET, video_id)
        job_info = '{}/info/{}.json'.format(VIDEO_BUCKET, video_id)

        data = {
            'original_video': original_video,
            'transcription': transcription,
            'translation': translation,
            'captioned_video': captioned_video,
            'job_info': job_info
        }
        url = 'http://{}:5000/video'.format(CAPTION_API)

        req = request.Request(url)
        req.add_header('Content-Type', 'application/json; charset=utf-8')
        data = json.dumps(data)
        data = data.encode('utf-8')
        req.add_header('Content-Length', len(data))
        response = request.urlopen(req, data)

    return response
