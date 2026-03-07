/**
 * OpenTelemetry browser tracing initialisation.
 *
 * Sets up a WebTracerProvider that exports spans via OTLP/HTTP to the
 * `/otlp/v1/traces` endpoint (proxied by nginx to the OTel Collector).
 * Automatically instruments `fetch` and `XMLHttpRequest` for any request
 * targeting `/api/`.
 *
 * Wrapped in try/catch so the dashboard degrades gracefully if the OTel
 * packages fail to load.
 */

import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';
import { XMLHttpRequestInstrumentation } from '@opentelemetry/instrumentation-xml-http-request';
import { ZoneContextManager } from '@opentelemetry/context-zone';
import { resourceFromAttributes } from '@opentelemetry/resources';
import { ATTR_SERVICE_NAME } from '@opentelemetry/semantic-conventions';
import { registerInstrumentations } from '@opentelemetry/instrumentation';

export function initTelemetry(): void {
  try {
    const resource = resourceFromAttributes({
      [ATTR_SERVICE_NAME]: 'metaforge-dashboard',
    });

    const exporter = new OTLPTraceExporter({
      url: '/otlp/v1/traces',
    });

    const provider = new WebTracerProvider({
      resource,
      spanProcessors: [new BatchSpanProcessor(exporter)],
    });

    provider.register({
      contextManager: new ZoneContextManager(),
    });

    registerInstrumentations({
      instrumentations: [
        new FetchInstrumentation({
          propagateTraceHeaderCorsUrls: [/\/api\//],
        }),
        new XMLHttpRequestInstrumentation({
          propagateTraceHeaderCorsUrls: [/\/api\//],
        }),
      ],
    });

    console.info('[telemetry] OpenTelemetry initialised');
  } catch (err) {
    console.warn('[telemetry] Failed to initialise OpenTelemetry:', err);
  }
}
