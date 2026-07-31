/**
 * Create a JSON fetch response for Web UI transport tests.
 *
 * Keep HTTP fakes at the transport boundary. Component tests should mock the
 * API client whenever they do not explicitly test fetch behavior.
 */
export function jsonResponse(data, options = {}) {
    return new Response(JSON.stringify(data), {
        status: options.status ?? 200,
        statusText: options.statusText,
        headers: { 'Content-Type': 'application/json', ...options.headers }
    });
}
