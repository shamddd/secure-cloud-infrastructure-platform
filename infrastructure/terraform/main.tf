locals {
  name = "${var.cluster_name}-${var.environment}"
  labels = merge(
    {
      application = "secure-cloud-infrastructure-platform"
      environment = var.environment
      managed_by  = "terraform"
    },
    var.labels,
  )
  required_services = toset([
    "artifactregistry.googleapis.com",
    "compute.googleapis.com",
    "container.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
    "sqladmin.googleapis.com",
  ])
}

resource "google_project_service" "required" {
  for_each = local.required_services

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_compute_network" "platform" {
  name                    = "${local.name}-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
  depends_on              = [google_project_service.required]
}

resource "google_compute_subnetwork" "gke" {
  name                     = "${local.name}-gke"
  ip_cidr_range            = var.network_cidr
  region                   = var.region
  network                  = google_compute_network.platform.id
  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.pods_cidr
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.services_cidr
  }
}

resource "google_compute_router" "platform" {
  name    = "${local.name}-router"
  region  = var.region
  network = google_compute_network.platform.id
}

resource "google_compute_router_nat" "platform" {
  name                               = "${local.name}-nat"
  router                             = google_compute_router.platform.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"

  subnetwork {
    name                    = google_compute_subnetwork.gke.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

resource "google_service_account" "gke_nodes" {
  account_id   = substr("${local.name}-nodes", 0, 30)
  display_name = "SCIP GKE node identity"
}

resource "google_project_iam_member" "gke_node_roles" {
  for_each = toset([
    "roles/artifactregistry.reader",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/monitoring.viewer",
    "roles/stackdriver.resourceMetadata.writer",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

resource "google_container_cluster" "platform" {
  name       = local.name
  location   = var.region
  network    = google_compute_network.platform.id
  subnetwork = google_compute_subnetwork.gke.id

  remove_default_node_pool    = true
  initial_node_count          = 1
  deletion_protection         = true
  enable_shielded_nodes       = true
  enable_intranode_visibility = true
  datapath_provider           = "ADVANCED_DATAPATH"
  networking_mode             = "VPC_NATIVE"

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = var.master_ipv4_cidr
  }

  master_authorized_networks_config {
    dynamic "cidr_blocks" {
      for_each = var.master_authorized_networks
      content {
        cidr_block   = cidr_blocks.value.cidr_block
        display_name = cidr_blocks.value.display_name
      }
    }
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  release_channel {
    channel = "REGULAR"
  }

  secret_manager_config {
    enabled = true
  }

  binary_authorization {
    evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
  }

  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS", "APISERVER"]
  }

  monitoring_config {
    enable_components = [
      "SYSTEM_COMPONENTS",
      "APISERVER",
      "SCHEDULER",
      "CONTROLLER_MANAGER",
      "STORAGE",
      "POD",
      "DEPLOYMENT",
      "STATEFULSET",
      "DAEMONSET",
      "HPA",
    ]
    managed_prometheus {
      enabled = true
    }
  }

  maintenance_policy {
    recurring_window {
      start_time = "2026-01-04T02:00:00Z"
      end_time   = "2026-01-04T06:00:00Z"
      recurrence = "FREQ=WEEKLY;BYDAY=SU"
    }
  }

  resource_labels = local.labels
  depends_on      = [google_project_service.required]
}

resource "google_container_node_pool" "platform" {
  name       = "${local.name}-general"
  location   = var.region
  cluster    = google_container_cluster.platform.name
  node_count = var.node_min_count

  autoscaling {
    min_node_count = var.node_min_count
    max_node_count = var.node_max_count
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  node_config {
    machine_type    = var.node_machine_type
    image_type      = "COS_CONTAINERD"
    service_account = google_service_account.gke_nodes.email
    oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"]
    labels          = local.labels

    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }

    kubelet_config {
      cpu_cfs_quota  = true
      pod_pids_limit = 4096
    }

    metadata = {
      disable-legacy-endpoints = "true"
    }
  }

  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }

  depends_on = [google_project_iam_member.gke_node_roles]
}

resource "google_compute_global_address" "private_services" {
  name          = "${local.name}-private-services"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.platform.id
}

resource "google_service_networking_connection" "private_services" {
  network                 = google_compute_network.platform.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_services.name]
}

resource "google_sql_database_instance" "platform" {
  name                = "${local.name}-postgres"
  region              = var.region
  database_version    = "POSTGRES_17"
  deletion_protection = true

  settings {
    tier                        = var.database_tier
    availability_type           = "REGIONAL"
    deletion_protection_enabled = true
    disk_type                   = "PD_SSD"
    disk_autoresize             = true
    disk_size                   = 20

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.platform.id
      ssl_mode                                      = "ENCRYPTED_ONLY"
      enable_private_path_for_google_cloud_services = true
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "01:00"
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 14
        retention_unit   = "COUNT"
      }
    }

    insights_config {
      query_insights_enabled  = true
      record_application_tags = true
      record_client_address   = false
    }

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }

    database_flags {
      name  = "log_temp_files"
      value = "0"
    }

    database_flags {
      name  = "log_connections"
      value = "on"
    }

    database_flags {
      name  = "log_disconnections"
      value = "on"
    }

    database_flags {
      name  = "log_lock_waits"
      value = "on"
    }

    database_flags {
      name  = "log_checkpoints"
      value = "on"
    }

    user_labels = local.labels
  }

  depends_on = [
    google_project_service.required,
    google_service_networking_connection.private_services,
  ]
}

resource "google_sql_database" "platform" {
  name     = "scip"
  instance = google_sql_database_instance.platform.name
}

resource "google_artifact_registry_repository" "platform" {
  location      = var.region
  repository_id = local.name
  description   = "Container images for the secure cloud infrastructure platform"
  format        = "DOCKER"
  labels        = local.labels
  depends_on    = [google_project_service.required]
}

resource "google_secret_manager_secret" "runtime" {
  for_each = toset(["database-url", "jwt-signing-key"])

  secret_id = "${local.name}-${each.value}"
  labels    = local.labels
  replication {
    auto {}
  }
  depends_on = [google_project_service.required]
}
