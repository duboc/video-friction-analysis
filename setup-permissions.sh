#!/bin/bash

# Exit on any error
set -e

# Default values
PROJECT_ID=""
SERVICE_ACCOUNT_NAME="video-analysis-app"
SERVICE_ACCOUNT_DISPLAY_NAME="Video Analysis App Service Account"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print usage
usage() {
    echo "Usage: $0 -p PROJECT_ID [-s SERVICE_ACCOUNT_NAME] [-d SERVICE_ACCOUNT_DISPLAY_NAME]"
    echo "  -p PROJECT_ID                     Your Google Cloud Project ID"
    echo "  -s SERVICE_ACCOUNT_NAME           Service account name (default: video-analysis-app)"
    echo "  -d SERVICE_ACCOUNT_DISPLAY_NAME   Service account display name (default: Video Analysis App Service Account)"
    exit 1
}

# Parse command line arguments
while getopts "p:s:d:h" opt; do
    case ${opt} in
        p )
            PROJECT_ID=$OPTARG
            ;;
        s )
            SERVICE_ACCOUNT_NAME=$OPTARG
            ;;
        d )
            SERVICE_ACCOUNT_DISPLAY_NAME=$OPTARG
            ;;
        h )
            usage
            ;;
        \? )
            usage
            ;;
    esac
done

# Validate required parameters
if [[ -z "$PROJECT_ID" ]]; then
    echo -e "${RED}Error: Project ID is required${NC}"
    usage
fi

# Full service account email
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo -e "${YELLOW}Setting up permissions for project: ${PROJECT_ID}${NC}"
echo -e "${YELLOW}Service account: ${SERVICE_ACCOUNT_EMAIL}${NC}"

# Function to check if command executed successfully
check_success() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
    else
        echo -e "${RED}✗ Failed: $1${NC}"
        exit 1
    fi
}

# Function to check if role is already assigned
check_role() {
    local project_id="$1"
    local service_account="$2"
    local role="$3"
    
    gcloud projects get-iam-policy "${project_id}" \
        --flatten="bindings[].members" \
        --format='table(bindings.role,bindings.members)' \
        --filter="bindings.members:${service_account} AND bindings.role:${role}" \
        2>/dev/null | grep -q "${role}"
    
    return $?
}

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable \
    iam.googleapis.com \
    cloudresourcemanager.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    storage-api.googleapis.com \
    storage-component.googleapis.com \
    firestore.googleapis.com \
    aiplatform.googleapis.com \
    --project "${PROJECT_ID}"
check_success "APIs enabled"

# Create service account if it doesn't exist
if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT_EMAIL}" --project "${PROJECT_ID}" &>/dev/null; then
    echo "Creating service account..."
    gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
        --display-name="${SERVICE_ACCOUNT_DISPLAY_NAME}" \
        --project="${PROJECT_ID}"
    check_success "Service account created"
else
    echo -e "${GREEN}✓ Service account already exists${NC}"
fi

# Array of roles to assign
ROLES=(
    # Cloud Storage
    "roles/storage.objectAdmin"
    
    # Firestore
    "roles/datastore.user"
    
    # Vertex AI
    "roles/aiplatform.user"
    
    # Cloud Run
    "roles/run.invoker"
    
    # Logging
    "roles/logging.logWriter"
    
    # Monitoring
    "roles/monitoring.metricWriter"
    "roles/monitoring.viewer"
)

# Assign roles to service account
echo "Assigning roles to service account..."
for role in "${ROLES[@]}"; do
    echo "Checking role: ${role}"
    if check_role "${PROJECT_ID}" "serviceAccount:${SERVICE_ACCOUNT_EMAIL}" "${role}"; then
        echo -e "${GREEN}✓ Role ${role} already assigned${NC}"
    else
        echo "Adding role: ${role}"
        gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
            --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
            --role="${role}" \
            --condition=None \
            --quiet
        check_success "Role ${role} assigned"
    fi
done

# Create and configure a new bucket if specified
read -p "Do you want to create a new Cloud Storage bucket for video storage? (y/n) " CREATE_BUCKET
if [[ $CREATE_BUCKET =~ ^[Yy]$ ]]; then
    read -p "Enter bucket name: " BUCKET_NAME
    
    # Create bucket using gcloud
    echo "Creating Cloud Storage bucket..."
    gcloud storage buckets create "gs://${BUCKET_NAME}" \
        --project="${PROJECT_ID}" \
        --location=us-central1 \
        --uniform-bucket-level-access
    check_success "Bucket created"
    
    # Set bucket permissions using gcloud
    echo "Setting bucket permissions..."
    gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
        --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
        --role="roles/storage.objectAdmin" \
        --condition=None
    check_success "Bucket permissions set"
fi

# Create Firestore database if it doesn't exist
read -p "Do you want to create a new Firestore database? (y/n) " CREATE_FIRESTORE
if [[ $CREATE_FIRESTORE =~ ^[Yy]$ ]]; then
    echo "Checking if Firestore database exists..."
    if ! gcloud firestore databases list --project="${PROJECT_ID}" 2>/dev/null | grep -q "(default)"; then
        echo "Creating Firestore database..."
        gcloud firestore databases create \
            --project="${PROJECT_ID}" \
            --region=us-central1 \
            --type=firestore-native
        check_success "Firestore database created"
    else
        echo -e "${GREEN}✓ Firestore database already exists${NC}"
    fi
fi

echo -e "${GREEN}Setup completed successfully!${NC}"
echo
echo "Next steps:"
echo "1. Update your .env file with the following values:"
echo "   GCP_PROJECT=${PROJECT_ID}"
if [[ $CREATE_BUCKET =~ ^[Yy]$ ]]; then
    echo "   GCS_BUCKET=${BUCKET_NAME}"
fi
echo "2. Build and deploy your application using the following commands:"
echo "   gcloud builds submit --tag gcr.io/${PROJECT_ID}/video-analysis-app"
echo "   gcloud run deploy video-analysis-app \\"
echo "     --image gcr.io/${PROJECT_ID}/video-analysis-app \\"
echo "     --platform managed \\"
echo "     --region us-central1 \\"
echo "     --service-account=${SERVICE_ACCOUNT_EMAIL} \\"
echo "     --allow-unauthenticated"