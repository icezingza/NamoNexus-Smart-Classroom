# NamoNexus Cloud SQL Setup Script
$PROJECT_ID = "namo-classroom"
$INSTANCE   = "namo-classroom-db"
$DB_NAME    = "namo_classroom"
$DB_USER    = "namo_app"
$DB_PASS    = "zyVrvLVu7FNXpAO7MN_WYw"

Write-Host "=== Step 1: Set GCP project ===" -ForegroundColor Cyan
gcloud config set project $PROJECT_ID

Write-Host "=== Step 2: Create database ===" -ForegroundColor Cyan
gcloud sql databases create $DB_NAME --instance=$INSTANCE

Write-Host "=== Step 3: Create namo_app user ===" -ForegroundColor Cyan
gcloud sql users create $DB_USER --instance=$INSTANCE --password=$DB_PASS

Write-Host ""
Write-Host "=== Done! ===" -ForegroundColor Green
Write-Host "DB User : $DB_USER" -ForegroundColor Yellow
Write-Host "DB Pass : $DB_PASS" -ForegroundColor Yellow
