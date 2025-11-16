#!/usr/bin/env powershell
<#
.SYNOPSIS
    Automated GCP deployment completion script for hahaphoto Django app
.DESCRIPTION
    This script completes the deployment to GCP Cloud Run after Cloud SQL is ready.
    It sets up the database, creates the application user, and deploys to Cloud Run.
#>

Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

# Configuration
$PROJECT_ID = "hahaphoto-prod-33000"
$REGION = "asia-east1"
$DB_INSTANCE = "hahaphoto-postgres"
$DB_NAME = "photoalbumdb"
$DB_USER = "postgres"
$SERVICE_NAME = "hahaphoto"
$APP_NAME = "hahaphoto"
$IMAGE_NAME = "gcr.io/$PROJECT_ID/$APP_NAME"
$SA_EMAIL = "hahaphoto-sa@$PROJECT_ID.iam.gserviceaccount.com"
$BUCKET_NAME = "$PROJECT_ID-hahaphoto-media"

# Retrieve secrets from temp files
$SECRET_KEY = Get-Content "$env:TEMP\django_secret_key.txt"
$DB_PASSWORD = Get-Content "$env:TEMP\db_password.txt"

Write-Output @"
================================
GCP Deployment Completion Script
================================
Project ID: $PROJECT_ID
Database Instance: $DB_INSTANCE
Image: $IMAGE_NAME
Service Account: $SA_EMAIL
================================
"@

# Step 1: Check if Cloud SQL is ready
Write-Output "Step 1: Checking Cloud SQL status..."
$status = gcloud sql instances describe $DB_INSTANCE --project=$PROJECT_ID --format='value(state)' 2>&1
Write-Output "Current status: $status"

if ($status -ne "RUNNABLE") {
    Write-Output "WARNING: Cloud SQL is not yet RUNNABLE. Waiting..."
    $timeout = 0
    while ($timeout -lt 300) {  # 5 minute timeout
        Start-Sleep -Seconds 10
        $status = gcloud sql instances describe $DB_INSTANCE --project=$PROJECT_ID --format='value(state)' 2>&1
        Write-Output "Status: $status"
        if ($status -eq "RUNNABLE") {
            Write-Output "Cloud SQL is now READY!"
            break
        }
        $timeout += 10
    }
}

if ($status -ne "RUNNABLE") {
    Write-Output "ERROR: Cloud SQL failed to become RUNNABLE within timeout. Exiting."
    exit 1
}

# Step 2: Get Cloud SQL connection name
Write-Output "Step 2: Getting Cloud SQL connection details..."
$SQL_CONNECTION_NAME = gcloud sql instances describe $DB_INSTANCE --format='value(connectionName)' --project=$PROJECT_ID
Write-Output "Connection Name: $SQL_CONNECTION_NAME"

# Step 3: Create database and set password
Write-Output "Step 3: Setting up database..."
gcloud sql users set-password postgres --instance=$DB_INSTANCE --password=$DB_PASSWORD --project=$PROJECT_ID
gcloud sql databases create $DB_NAME --instance=$DB_INSTANCE --project=$PROJECT_ID 2>&1 | Out-Null

Write-Output "Database '$DB_NAME' created (or already exists)"

# Step 4: Deploy to Cloud Run
Write-Output "Step 4: Deploying to Cloud Run..."
Write-Output "This may take 2-3 minutes..."

$DATABASE_URL = "postgresql+psycopg2://postgres:$DB_PASSWORD@/photoalbumdb?host=/cloudsql/$SQL_CONNECTION_NAME"
$ALLOWED_HOSTS = "hahaphoto.run.app,localhost"

gcloud run deploy $SERVICE_NAME `
    --image=$IMAGE_NAME `
    --platform=managed `
    --region=$REGION `
    --allow-unauthenticated `
    --memory=512Mi `
    --timeout=3600 `
    --set-env-vars @"
DJANGO_DEBUG=0,`
DJANGO_SECRET_KEY=$SECRET_KEY,`
DJANGO_ALLOWED_HOSTS=$ALLOWED_HOSTS,`
DATABASE_URL=$DATABASE_URL,`
GS_BUCKET_NAME=$BUCKET_NAME,`
GS_PROJECT_ID=$PROJECT_ID
"@ `
    --add-cloudsql-instances=$SQL_CONNECTION_NAME `
    --service-account=$SA_EMAIL `
    --no-gen2 `
    --project=$PROJECT_ID

Write-Output ""
Write-Output "======================================"
Write-Output "Deployment Complete!"
Write-Output "======================================"

# Get service URL
$SERVICE_URL = gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)' --project=$PROJECT_ID
Write-Output "Service URL: $SERVICE_URL"
Write-Output ""
Write-Output "Next steps:"
Write-Output "1. Run database migrations (see GCP_DEPLOYMENT_GUIDE.md Step 8)"
Write-Output "2. Open the service URL in your browser to verify deployment"
Write-Output "3. Check logs: gcloud run services logs read $SERVICE_NAME --region=$REGION"
Write-Output ""
