output "cloud_run_job_name" {
  description = "Name of the Cloud Run Job that runs the daily extraction."
  value       = google_cloud_run_v2_job.extract.name
}

output "service_account_email" {
  description = "Email of the psx-warehouse-runner service account."
  value       = google_service_account.runner.email
}

output "bigquery_dataset_id" {
  description = "BigQuery raw dataset ID."
  value       = google_bigquery_dataset.raw.dataset_id
}

output "workload_identity_provider" {
  description = "Full resource name for the GCP_WORKLOAD_IDENTITY_PROVIDER GitHub repo variable."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "deployer_service_account_email" {
  description = "Value for the GCP_DEPLOYER_SA_EMAIL GitHub repo variable."
  value       = google_service_account.deployer.email
}
