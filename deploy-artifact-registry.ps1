<#
.SYNOPSIS
    Builds the Soundboard Docker container, pushes to Google Artifact Registry,
    and deploys to Cloud Run under a new service name (soundboard-app-auth).

.DESCRIPTION
    Ensures the live 'soundboard-app-git' service remains untouched.
#>

param(
    [string]$ProjectId = "p-np-adt-de",
    [string]$Region = "us-west1",
    [string]$RepoName = "soundboard-repo",
    [string]$ServiceName = "soundboard-app-auth",
    [string]$ImageName = "soundboard-app-auth",
    [string]$AllowedUserGroup = "soundboard-app-users-adt@yourdomain.com",
    [string]$DiscordBotToken = ""
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "🚀 DEPLOYING SOUNDBOARD APP TO GOOGLE ARTIFACT REGISTRY & CLOUD RUN" -ForegroundColor Cyan
Write-Host "Project: $ProjectId | Region: $Region" -ForegroundColor Cyan
Write-Host "Service: $ServiceName (Independent of soundboard-app-git)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Ensure required Google Cloud APIs are enabled
Write-Host "`n[1/4] Checking & enabling required GCP APIs..." -ForegroundColor Yellow
gcloud services enable artifactregistry.googleapis.com cloudbuild.googleapis.com run.googleapis.com cloudidentity.googleapis.com --project=$ProjectId

# 2. Ensure Artifact Registry Docker repository exists
Write-Host "`n[2/4] Verifying Artifact Registry repository '$RepoName'..." -ForegroundColor Yellow
$repoExists = gcloud artifacts repositories describe $RepoName --location=$Region --project=$ProjectId 2>$null
if (-not $repoExists) {
    Write-Host "Creating Artifact Registry repository '$RepoName' in $Region..." -ForegroundColor Green
    gcloud artifacts repositories create $RepoName `
        --repository-format=docker `
        --location=$Region `
        --description="Docker repository for Soundboard App containers" `
        --project=$ProjectId
} else {
    Write-Host "Repository '$RepoName' already exists." -ForegroundColor Green
}

# 3. Build & Push Image via Cloud Build
$FullImageTag = "$Region-docker.pkg.dev/$ProjectId/$RepoName/${ImageName}:latest"
Write-Host "`n[3/4] Building container and pushing to Artifact Registry ($FullImageTag)..." -ForegroundColor Yellow
gcloud builds submit --tag $FullImageTag --project=$ProjectId .

# 4. Deploy New Independent Cloud Run Service from Artifact Registry Image
Write-Host "`n[4/4] Deploying Cloud Run service '$ServiceName' from Artifact Registry image..." -ForegroundColor Yellow

$envVars = "ALLOWED_USER_GROUP=$AllowedUserGroup,FIREBASE_PROJECT_ID=$ProjectId"
if ($DiscordBotToken -and $DiscordBotToken.Trim() -ne "") {
    $envVars += ",DISCORD_BOT_TOKEN=$DiscordBotToken"
}

gcloud run deploy $ServiceName `
    --image=$FullImageTag `
    --project=$ProjectId `
    --region=$Region `
    --port=8080 `
    --min-instances=0 `
    --max-instances=1 `
    --memory=512Mi `
    --cpu=1 `
    --allow-unauthenticated `
    --set-env-vars=$envVars

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "✅ DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "Artifact Registry Image: $FullImageTag" -ForegroundColor Green
Write-Host "Cloud Run Service: $ServiceName" -ForegroundColor Green
Write-Host "Your original 'soundboard-app-git' service is safe and untouched." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
