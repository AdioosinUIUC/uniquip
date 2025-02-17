import asyncio
from django.utils.deprecation import MiddlewareMixin
from opentelemetry import trace
from django.http import JsonResponse
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from uniquip.utils.s3_logger import S3Logger, LogLevel

logger = S3Logger()

class OpenTelemetryMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response
        self.tracer = trace.get_tracer(__name__)

    def __call__(self, request):
        # Start a span for the request
        with self.tracer.start_as_current_span("request") as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", request.build_absolute_uri())

            try:
                response = self.get_response(request)
                return response
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))  # Mark as error
                logger.log(f"Exception occurred: {str(e)}", LogLevel.ERROR)  # Log error
                return JsonResponse({"error": "Internal Server Error"}, status=500)
