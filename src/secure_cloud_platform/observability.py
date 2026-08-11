from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from secure_cloud_platform.config import Settings
from secure_cloud_platform.database import Database

REQUEST_COUNT = Counter(
    "scip_http_requests_total",
    "HTTP requests handled by the control plane",
    ("method", "route", "status"),
)
REQUEST_LATENCY = Histogram(
    "scip_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ("method", "route"),
)


def configure_metrics(app: FastAPI, settings: Settings) -> None:
    if not settings.metrics_enabled:
        return

    @app.middleware("http")
    async def record_metrics(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        route = request.scope.get("route")
        route_path = getattr(route, "path", "unmatched")
        REQUEST_COUNT.labels(request.method, route_path, str(response.status_code)).inc()
        REQUEST_LATENCY.labels(request.method, route_path).observe(time.perf_counter() - started)
        return response

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def configure_tracing(app: FastAPI, database: Database, settings: Settings) -> None:
    if not settings.otlp_traces_endpoint:
        return
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: settings.app_name}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otlp_traces_endpoint))
    )
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    SQLAlchemyInstrumentor().instrument(
        engine=database.engine.sync_engine,
        tracer_provider=provider,
    )
