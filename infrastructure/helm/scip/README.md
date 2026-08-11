# Helm chart

The chart deploys the API and a pre-install/pre-upgrade migration Job. It
requires an image pinned by digest and an existing Kubernetes Secret named by
`runtimeSecretName`; it never templates credential values into a release.

```bash
helm lint . \
  --set image.repository=asia-south1-docker.pkg.dev/example/scip/api \
  --set image.digest=sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

helm template scip . \
  --namespace scip \
  --set image.repository=asia-south1-docker.pkg.dev/example/scip/api \
  --set image.digest=sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```

Before installation, create `Secret/scip-runtime` through an approved secret
controller with `SCIP_DATABASE_URL` and `SCIP_JWT_SIGNING_KEY`. The default
NetworkPolicy CIDRs are examples for private RFC1918 networks; narrow them to the
actual Cloud SQL and collector ranges. Configure an ingress controller and a
real TLS certificate secret before exposing the service.
