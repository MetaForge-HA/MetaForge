/**
 * Core Web Vitals reporting via the `web-vitals` library.
 *
 * Reports CLS, INP, LCP, FCP, and TTFB through the structured logger.
 */

import { logger } from './logger';

export function initWebVitals(): void {
  import('web-vitals')
    .then(({ onCLS, onINP, onLCP, onFCP, onTTFB }) => {
      const report = (metric: { name: string; value: number; id: string }) => {
        logger.info('web-vital', {
          metric: metric.name,
          value: metric.value,
          id: metric.id,
        });
      };

      onCLS(report);
      onINP(report);
      onLCP(report);
      onFCP(report);
      onTTFB(report);
    })
    .catch((err) => {
      logger.warn('Failed to initialise web-vitals', { error: String(err) });
    });
}
