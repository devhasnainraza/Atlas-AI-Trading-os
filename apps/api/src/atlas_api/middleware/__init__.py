"""Cross-cutting HTTP middleware. Order (outermost first): correlation → security headers
→ rate limit → routing; error handlers are registered on the app."""
