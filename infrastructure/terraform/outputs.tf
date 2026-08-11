output "cluster_name" {
  description = "Name of the created GKE cluster."
  value       = google_container_cluster.platform.name
}

output "cluster_location" {
  description = "Region containing the GKE cluster."
  value       = google_container_cluster.platform.location
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository path without an image name."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.platform.repository_id}"
}

output "database_private_ip" {
  description = "Private Cloud SQL address; reachable only from connected networks."
  value       = google_sql_database_instance.platform.private_ip_address
}

output "runtime_secret_ids" {
  description = "Secret Manager IDs that operators must populate outside Terraform."
  value       = { for key, secret in google_secret_manager_secret.runtime : key => secret.secret_id }
}
