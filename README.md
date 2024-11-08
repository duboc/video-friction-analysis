# Video Analysis App 🎥

A Streamlit application that enables users to upload, analyze, and manage video content using Google Cloud services and AI-powered analysis. The app uses Vertex AI for content analysis, Cloud Storage for video storage, and Firestore for data management.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Setting up Google Cloud Project](#setting-up-google-cloud-project)
  - [Environment Variables](#environment-variables)
- [Deployment](#deployment)
  - [Local Development](#local-development)
  - [Deploy to Google Cloud Run](#deploy-to-google-cloud-run)
  - [Optional Deployment Configurations](#optional-deployment-configurations)
- [Project Structure](#project-structure)
- [Features in Detail](#features-in-detail)
- [Service Components](#service-components)
- [API Documentation](#api-documentation)
- [Error Handling](#error-handling)
- [Security Considerations](#security-considerations)
- [Performance Optimization](#performance-optimization)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

## Features

- 📤 **Video Upload and Management**
  - Secure file upload with validation
  - Automatic file type detection
  - Progress tracking
  - File management interface

- 🤖 **AI-powered Video Analysis**
  - Content recognition
  - Object detection
  - Scene analysis
  - Text extraction
  - Action recognition

- 📊 **Analysis Results Visualization**
  - Interactive data tables
  - Visual analytics
  - Exportable reports
  - Custom filtering

- 📋 **Task Backlog Generation**
  - Automated task creation
  - Priority assignment
  - Effort estimation
  - Dependencies tracking

- 👥 **User Story Creation**
  - Automated story generation
  - Acceptance criteria
  - Story point estimation
  - Sprint planning support

- 📈 **Interactive Data Viewer**
  - Custom column selection
  - Sorting and filtering
  - Data export capabilities
  - Real-time updates

- 🔒 **Secure File Handling**
  - File type validation
  - Size limit enforcement
  - Content verification
  - Secure storage

## Prerequisites

- Python 3.8+
- Google Cloud Platform account with billing enabled
- Configured GCP credentials (`gcloud auth login`)
- Required system packages:
  ```bash
  sudo apt-get update
  sudo apt-get install -y \
    libmagic1 \
    build-essential \
    python3-dev
  ```
- Google Cloud CLI installed and configured
- Docker (for container deployment)
- Access to required Google Cloud APIs:
  - Vertex AI API
  - Cloud Storage API
  - Firestore API
  - Cloud Run API

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd video-analysis-app
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Install pre-commit hooks (for developers):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Configuration

### Setting up Google Cloud Project

1. Make the permissions setup script executable:
   ```bash
   chmod +x setup-permissions.sh
   ```

2. Run the setup script with your project ID:
   ```bash
   ./setup-permissions.sh -p your-project-id
   ```

   The script performs the following setup:
   - Enables required Google Cloud APIs
   - Creates a service account with necessary permissions
   - Sets up Cloud Storage bucket (optional)
   - Creates Firestore database (optional)
   - Provides deployment instructions

   Available options:
   ```bash
   Usage: ./setup-permissions.sh -p PROJECT_ID [-s SERVICE_ACCOUNT_NAME] [-d SERVICE_ACCOUNT_DISPLAY_NAME]
     -p PROJECT_ID                     Your Google Cloud Project ID
     -s SERVICE_ACCOUNT_NAME           Service account name (default: video-analysis-app)
     -d SERVICE_ACCOUNT_DISPLAY_NAME   Service account display name
   ```

### Environment Variables

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Update the following values:
   ```plaintext
   # Google Cloud Settings
   GCP_PROJECT=your-project-id
   GCS_BUCKET=your-bucket-name
   DEFAULT_REGION=us-central1
   REGIONS=us-central1,europe-west4,asia-east1

   # Application Settings
   ALLOWED_VIDEO_EXTENSIONS=mp4,avi,mov
   MAX_VIDEO_SIZE_MB=100
   VERTEX_MODEL_NAME=gemini-1.5-pro-002
   FIRESTORE_COLLECTION=video_analysis

   # Optional Settings
   DEBUG=False
   LOGGING_LEVEL=INFO
   ```

## Deployment

### Local Development

1. Ensure environment variables are set:
   ```bash
   source .env
   ```

2. Start the Streamlit application:
   ```bash
   streamlit run app.py
   ```

3. Access the application at `http://localhost:8501`

### Deploy to Google Cloud Run

1. Build and push the Docker image:
   ```bash
   # Set your project ID
   export PROJECT_ID=your-project-id

   # Build the image
   gcloud builds submit --tag gcr.io/$PROJECT_ID/video-analysis-app
   ```

2. Deploy to Cloud Run:
   ```bash
   gcloud run deploy video-analysis-app \
     --image gcr.io/$PROJECT_ID/video-analysis-app \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --service-account=video-analysis-app@$PROJECT_ID.iam.gserviceaccount.com \
     --set-env-vars="GCP_PROJECT=$PROJECT_ID,GCS_BUCKET=your-bucket-name"
   ```

### Optional Deployment Configurations

Customize your deployment with additional flags:

```bash
# Adjust memory and CPU
gcloud run deploy video-analysis-app \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  [other flags...]

# Set custom timeout for long-running processes
gcloud run deploy video-analysis-app \
  --timeout 3600 \
  [other flags...]

# Add custom domain
gcloud run domain-mappings create \
  --service video-analysis-app \
  --domain your-domain.com
```

## Project Structure

```
video-analysis-app/
├── config/
│   └── settings.py         # Application settings
├── prompts/
│   ├── video_analysis_prompt.md
│   ├── user_story.md
│   └── task_backlog.md
├── services/
│   ├── firestore_service.py
│   ├── storage_service.py
│   └── vertex_service.py
├── utils/
│   ├── firestore_viewer.py
│   ├── retry_handler.py
│   └── security.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── .env.example           # Environment variables template
├── .dockerignore         # Docker build exclusions
├── .gitignore           # Git exclusions
├── Dockerfile           # Container configuration
├── setup-permissions.sh # GCP setup script
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Features in Detail

### Video Upload and Management
- Supported formats: MP4, AVI, MOV
- Maximum file size: Configurable (default 100MB)
- Automatic duplicate detection
- Progress tracking
- Secure file handling with type verification

### Analysis Capabilities
- Scene recognition
- Object detection
- Text extraction
- Action recognition
- Sentiment analysis
- Content categorization

### Data Visualization
- Interactive tables
- Custom column selection
- Sorting and filtering
- Export to CSV
- Real-time updates

### Task Management
- Automatic task generation
- Priority assignment
- Effort estimation
- Sprint planning integration
- Dependency tracking

## Service Components

### StorageService
Handles video file storage in Google Cloud Storage:
- Secure upload management
- File listing and retrieval
- Access control
- Cleanup procedures

### FirestoreService
Manages analysis data in Firestore:
- Result storage
- Query optimization
- Real-time updates
- Data synchronization

### VertexService
Integrates with Vertex AI for analysis:
- Model management
- Request handling
- Error recovery
- Regional failover

## API Documentation

### Video Analysis API
```python
def analyze_video(video_url: str) -> Dict[str, Any]:
    """
    Analyze video content using Vertex AI.
    
    Args:
        video_url: GCS URL of the video
        
    Returns:
        Dict containing analysis results
    """
```

### Storage API
```python
def upload_video(file: UploadFile) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Upload video to Cloud Storage.
    
    Args:
        file: Video file object
        
    Returns:
        (success, url, error_message)
    """
```

## Error Handling

The application implements comprehensive error handling:
- API timeouts
- Service unavailability
- Invalid file types
- Size limit violations
- Processing failures

## Security Considerations

- File validation before processing
- Content type verification
- Secure URL generation
- Access control implementation
- Data encryption
- Regular security updates

## Performance Optimization

- Caching strategies
- Request batching
- Lazy loading
- Resource pooling
- Regional optimization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add unit tests for new features
- Update documentation
- Use type hints
- Include error handling

## License

```
Copyright 2024 Video Analysis App Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
