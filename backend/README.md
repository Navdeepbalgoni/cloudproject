# Backend Setup

This backend handles video uploads, stores metadata in DynamoDB, and uses OpenAI Whisper to generate subtitles.

## Requirements

- Python 3.8+
- AWS Account (S3, DynamoDB, Cognito)
- OpenAI API Key

## Configuration

Create a `.env` file in this directory with the following variables:

```env
OPENAI_API_KEY=your_openai_api_key_here
VIDEOS_BUCKET=your-s3-bucket-name
VIDEOS_TABLE=your-dynamodb-table-name
USER_POOL_ID=your-cognito-user-pool-id
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   python back.py
   ```

## Workflow

1. **Upload**: Video is uploaded via `/send`.
2. **Storage**: Video is saved to S3 and a record is created in DynamoDB.
3. **Transcription**: A background thread sends the video to OpenAI Whisper API.
4. **Subtitles**: Whisper returns an SRT file, which is saved to S3.
5. **Update**: DynamoDB is updated with `finished=True` and the SRT key.
