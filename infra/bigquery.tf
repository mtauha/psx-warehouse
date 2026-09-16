resource "google_bigquery_dataset" "raw" {
  project    = var.gcp_project
  dataset_id = var.bq_dataset
  location   = var.bq_location

  depends_on = [google_project_service.required]
}
