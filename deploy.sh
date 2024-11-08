#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    # Load variables without exporting them
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        if [[ $key =~ ^#.*$ ]] || [[ -z $key ]]; then
            continue
        fi
        # Remove any quotes and spaces from the value
        value=$(echo $value | tr -d '"' | tr -d "'")
        case "$key" in
            GCP_PROJECT) GCP_PROJECT=$value ;;
            GCS_BUCKET) GCS_BUCKET=$value ;;
            DEFAULT_REGION) DEFAULT_REGION=$value ;;
        esac
    done < .env
else
    echo "Error: .env file not found"
    exit 1
fi

# Deploy to Cloud Run
gcloud run deploy video-friction-analysis \
  --source . \
  --platform managed \
  --region ${DEFAULT_REGION} \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 3600 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${GCP_PROJECT},BUCKET_NAME=${GCS_BUCKET}"

# Check if deployment was successful
if [ $? -eq 0 ]; then
    echo "Deployment successful!"
else
    echo "Deployment failed!"
    exit 1
fi