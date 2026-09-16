resource "google_cloud_scheduler_job" "extract_daily" {
  project   = var.gcp_project
  name      = "psx-warehouse-extract-daily"
  region    = var.region
  schedule  = var.schedule_cron
  time_zone = var.schedule_timezone

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/v2/projects/${var.gcp_project}/locations/${var.region}/jobs/${google_cloud_run_v2_job.extract.name}:run"

    oauth_token {
      service_account_email = google_service_account.runner.email
    }
  }

  depends_on = [
    google_project_service.required,
    google_cloud_run_v2_job_iam_member.scheduler_invokes,
  ]
}
