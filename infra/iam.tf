resource "google_service_account" "runner" {
  project      = var.gcp_project
  account_id   = "psx-warehouse-runner"
  display_name = "psx-warehouse Cloud Run Job identity"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "runner_bigquery_data_editor" {
  project = var.gcp_project
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.runner.email}"
}

resource "google_project_iam_member" "runner_bigquery_job_user" {
  project = var.gcp_project
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.runner.email}"
}
