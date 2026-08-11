{{- define "scip.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "scip.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name (include "scip.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "scip.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "scip.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "scip.selectorLabels" -}}
app.kubernetes.io/name: {{ include "scip.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "scip.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "scip.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- required "serviceAccount.name is required when create=false" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "scip.image" -}}
{{- printf "%s@%s" (required "image.repository is required" .Values.image.repository) (required "image.digest is required" .Values.image.digest) }}
{{- end }}
