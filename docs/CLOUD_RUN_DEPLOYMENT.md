# GCP Cloud Run & Artifact Registry Deployment Guide (Project: `p-np-adt-de`)

This guide explains how to build the Docker image, push it directly to **Google Cloud Artifact Registry**, and deploy it to **Google Cloud Run** under a new, independent service name (`soundboard-app-auth`) while keeping your existing `soundboard-app-git` service 100% untouched.

---

## 1. Zero-Cost Guarantee & Free Tier Limits

Google Cloud Run & Artifact Registry include a generous monthly free tier:

| Free Tier Resource | Free Quota Per Month |
| :--- | :--- |
| **Cloud Run Requests** | **2 Million Requests** / month free |
| **Compute Time** | **360,000 vCPU-seconds** / month free |
| **Memory Time** | **180,000 GiB-seconds** / month free |
| **Artifact Registry Storage** | **0.5 GB** free storage / month |
| **Network Egress** | **1 GiB** free egress to North America / month |

---

## 2. One-Click Deployment Script (`deploy-artifact-registry.ps1`)

From within the `soundboard_app` folder in PowerShell, run:

```powershell
.\deploy-artifact-registry.ps1 -AllowedUserGroup "soundboard-app-users-adt@yourdomain.com"
```

### What this script automatically does:
1. Enables required GCP APIs (`artifactregistry`, `cloudbuild`, `run`, `cloudidentity`).
2. Creates the Artifact Registry Docker repository (`soundboard-repo` in `us-west1`) if it doesn't already exist.
3. Builds your Docker container using Google Cloud Build and pushes it to:
   `us-west1-docker.pkg.dev/p-np-adt-de/soundboard-repo/soundboard-app-auth:latest`
4. Deploys a new, dedicated Cloud Run service: **`soundboard-app-auth`** with your `ALLOWED_USER_GROUP` environment variable configured.

---

## 3. Manual Step-by-Step Deployment (CLI)

### Step A: Authenticate & Set Project
```bash
gcloud auth login
gcloud config set project p-np-adt-de
```

### Step B: Enable Required Services
```bash
gcloud services enable artifactregistry.googleapis.com cloudbuild.googleapis.com run.googleapis.com cloudidentity.googleapis.com
```

### Step C: Create Artifact Registry Repository (One-Time)
```bash
gcloud artifacts repositories create soundboard-repo \
  --repository-format=docker \
  --location=us-west1 \
  --description="Docker repository for Soundboard App containers" \
  --project=p-np-adt-de
```

### Step D: Build & Push Image via Cloud Build
```bash
gcloud builds submit \
  --tag=us-west1-docker.pkg.dev/p-np-adt-de/soundboard-repo/soundboard-app-auth:latest \
  --project=p-np-adt-de .
```

### Step E: Deploy to New Cloud Run Service (`soundboard-app-auth`)
```bash
gcloud run deploy soundboard-app-auth \
  --image=us-west1-docker.pkg.dev/p-np-adt-de/soundboard-repo/soundboard-app-auth:latest \
  --project=p-np-adt-de \
  --region=us-west1 \
  --port=8080 \
  --min-instances=0 \
  --max-instances=1 \
  --memory=512Mi \
  --cpu=1 \
  --allow-unauthenticated \
  --set-env-vars="ALLOWED_USERS=sina.dadvand@gmail.com,FIREBASE_PROJECT_ID=p-np-adt-de"
```

---

## 4. Terraform Infrastructure as Code

When deploying via Terraform, ensure **Public Access (`roles/run.invoker` for `allUsers`)** is enabled so the browser can load the web app and prompt for Google Sign-In:

```hcl
resource "google_cloud_run_v2_service" "soundboard_auth" {
  name     = "soundboard-app-fb-adt"
  location = "us-west1"
  project  = "p-np-adt-de"

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = "us-west1-docker.pkg.dev/p-np-adt-de/soundboard-app-adt/app:latest"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
      }

      env {
        name  = "ALLOWED_USERS"
        value = "sina.dadvand@gmail.com"
      }

      env {
        name  = "FIREBASE_PROJECT_ID"
        value = "p-np-adt-de"
      }

      ports {
        container_port = 8080
      }
    }
  }
}

# CRITICAL: Grant allUsers invoker permissions so users can reach the frontend login page
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.soundboard_auth.location
  project  = google_cloud_run_v2_service.soundboard_auth.project
  service  = google_cloud_run_v2_service.soundboard_auth.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
```
