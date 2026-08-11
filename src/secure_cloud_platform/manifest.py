from __future__ import annotations

from typing import Any

from secure_cloud_platform.models import Workload


def build_kubernetes_manifest(workload: Workload) -> dict[str, Any]:
    """Build a deterministic, least-privilege workload bundle for GitOps handoff."""
    labels = {
        "app.kubernetes.io/name": workload.name,
        "app.kubernetes.io/managed-by": "secure-cloud-infrastructure-platform",
        "scip.dev/workload-id": workload.id,
    }
    deployment: dict[str, Any] = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": workload.name,
            "labels": labels,
            "annotations": {"scip.dev/workload-version": str(workload.version)},
        },
        "spec": {
            "replicas": workload.replicas,
            "revisionHistoryLimit": 3,
            "selector": {"matchLabels": {"app.kubernetes.io/name": workload.name}},
            "template": {
                "metadata": {"labels": labels},
                "spec": {
                    "automountServiceAccountToken": False,
                    "securityContext": {
                        "runAsNonRoot": True,
                        "seccompProfile": {"type": "RuntimeDefault"},
                    },
                    "containers": [
                        {
                            "name": workload.name,
                            "image": workload.image,
                            "imagePullPolicy": "IfNotPresent",
                            "ports": [
                                {
                                    "name": "http",
                                    "containerPort": workload.container_port,
                                    "protocol": "TCP",
                                }
                            ],
                            "securityContext": {
                                "allowPrivilegeEscalation": False,
                                "readOnlyRootFilesystem": True,
                                "capabilities": {"drop": ["ALL"]},
                            },
                            "resources": {
                                "requests": {"cpu": "100m", "memory": "128Mi"},
                                "limits": {"cpu": "1", "memory": "512Mi"},
                            },
                        }
                    ],
                },
            },
        },
    }
    service: dict[str, Any] = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": workload.name, "labels": labels},
        "spec": {
            "type": "ClusterIP",
            "selector": {"app.kubernetes.io/name": workload.name},
            "ports": [
                {
                    "name": "http",
                    "port": workload.container_port,
                    "targetPort": "http",
                    "protocol": "TCP",
                }
            ],
        },
    }
    return {
        "apiVersion": "v1",
        "kind": "List",
        "metadata": {
            "annotations": {
                "scip.dev/generated-from": workload.id,
                "scip.dev/workload-version": str(workload.version),
            }
        },
        "items": [deployment, service],
    }
