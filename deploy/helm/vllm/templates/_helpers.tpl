{{- define "vllm.labels" -}}
app.kubernetes.io/name: vllm
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{- define "vllm.selector" -}}
app.kubernetes.io/name: vllm
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
