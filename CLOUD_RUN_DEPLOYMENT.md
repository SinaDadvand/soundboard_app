# GCP Cloud Run Deployment Guide (Project: `p-np-adt-de`)

This guide explains how to deploy the containerized Virtual Soundboard to **Google Cloud Run** in project `p-np-adt-de` with **$0.00 cost** guaranteed under GCP's Free Tier.

---

## 1. Zero-Cost Guarantee & Free Tier Limits

Google Cloud Run includes a **generous free tier that renews every month** per billing account:

| Free Tier Resource | Free Quota Per Month |
| :--- | :--- |
| **Requests** | **2 Million Requests** / month free |
| **Compute Time** | **360,000 vCPU-seconds** / month free (100 hours of continuous active CPU) |
| **Memory Time** | **180,000 GiB-seconds** / month free |
| **Network Egress** | **1 GiB** free egress to North America / month |

### Why this setup stays $0.00:
1. **Scale to Zero (`--min-instances=0`)**: When nobody is using the soundboard, 0 container instances run. You pay **$0.00**.
2. **CPU Throttling (`--cpu-throttling`)**: CPU is only allocated during active HTTP requests or sound streaming, avoiding background idle compute charges.
3. **Small Resource Footprint (`512MiB RAM`, `1 vCPU`)**: Uses minimal memory.

---

## 2. Deploying via `gcloud` CLI (Source Deploy)

If you have the Google Cloud SDK (`gcloud`) installed:

### Step A: Authenticate & Set Project
```bash
gcloud auth login
gcloud config set project p-np-adt-de
```

### Step B: Enable Required Services (One-Time)
```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

### Step C: Deploy Direct from Source to Cloud Run
Run this single command from within the `soundboard_app` directory:
```bash
gcloud run deploy soundboard-app \
  --project=p-np-adt-de \
  --region=us-central1 \
  --source=. \
  --port=8080 \
  --min-instances=0 \
  --max-instances=1 \
  --memory=512Mi \
  --cpu=1 \
  --cpu-throttling \
  --allow-unauthenticated \
  --set-env-vars="DISCORD_BOT_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE"
```

---

## 3. Deploying via Google Cloud Console (Web UI)

If you prefer using the browser without installing `gcloud`:

1. Open **[Google Cloud Run Console](https://console.cloud.google.com/run?project=p-np-adt-de)**.
2. Click **Create Service**.
3. Choose **Continuously deploy from a repository** (connect your GitHub repo `SinaDadvand/soundboard_app` branch `feature/containerized` or `main`) OR upload via Cloud Shell.
4. **Service settings**:
   * Service name: `soundboard-app`
   * Region: `us-central1` (Iowa) or your preferred region.
   * Authentication: **Allow unauthenticated invocations**.
5. **Container, Networking, Security (Advanced Settings)**:
   * **Container Port**: `8080`
   * **Memory**: `512 MiB` (or `1 GiB`)
   * **CPU**: `1`
   * **Execution Environment**: Default (Second generation)
   * **CPU allocation**: *CPU is only allocated during request processing* (CPU throttling enabled)
   * **Autoscaling**: Minimum instances = `0`, Maximum instances = `1`
6. **Environment Variables**:
   * Add Name: `DISCORD_BOT_TOKEN`, Value: `your_token_here`
7. Click **Create**.
8. Once deployed, Cloud Run will provide your live HTTPS URL (e.g., `https://soundboard-app-xyz.a.run.app`).

---

## 4. Setting Up with Terraform (Future Repo)

When you are ready to manage infrastructure as code in your separate Terraform repository, here is the complete Terraform resource definition:

```hcl
resource "google_cloud_run_v2_service" "soundboard" {
  name     = "soundboard-app"
  location = "us-central1"
  project  = "p-np-adt-de"

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = "gcr.io/p-np-adt-de/soundboard-app:latest"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
      }

      env {
        name  = "DISCORD_BOT_TOKEN"
        value = var.discord_bot_token
      }

      ports {
        container_port = 8080
      }
    }
  }
}

resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.soundboard.location
  project  = google_cloud_run_v2_service.soundboard.project
  service  = google_cloud_run_v2_service.soundboard.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
```
