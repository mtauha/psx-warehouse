resource "google_bigquery_dataset" "raw" {
  project    = var.gcp_project
  dataset_id = var.bq_dataset
  location   = var.bq_location

  depends_on = [google_project_service.required["bigquery.googleapis.com"]]
}

resource "google_bigquery_dataset" "staging" {
  project    = var.gcp_project
  dataset_id = "staging"
  location   = var.bq_location

  depends_on = [google_project_service.required["bigquery.googleapis.com"]]
}

resource "google_bigquery_dataset" "marts" {
  project    = var.gcp_project
  dataset_id = "marts"
  location   = var.bq_location

  depends_on = [google_project_service.required["bigquery.googleapis.com"]]
}
