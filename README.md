# Global Subtitles (Shark Subtitles)

An automatic video subtitling platform that leverages OpenAI Whisper to transcribe and generate subtitles for videos.

## Project Overview

- **Automatic Transcription**: Uses OpenAI Whisper to convert speech to text with high accuracy.
- **SRT Generation**: Automatically generates SRT subtitle files for uploaded videos.
- **Simplified Architecture**: Direct integration in the Flask backend, removing the need for AWS Lambda, Transcribe, and Translate for a more streamlined pipeline.

## Documentation

Detailed instructions for setting up and using the project:

1. [Backend Setup](backend/README.md) - Learn how to configure the Flask API and OpenAI Key.
2. [User Interface](docs/06_interface.md) - Overview of the frontend.
3. [Amazon Cognito](docs/07_cognito.md) - User authentication setup.
4. [S3 Buckets](docs/02_buckets.md) - Storage configuration.
5. [DynamoDB Setup](docs/04_dynamo.md) - Database configuration.


