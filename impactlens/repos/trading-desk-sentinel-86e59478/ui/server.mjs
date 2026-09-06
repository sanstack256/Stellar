/* global Buffer, Headers, URL, console, fetch, process */

import { createReadStream } from "node:fs";
import { promises as fs } from "node:fs";
import { createServer } from "node:http";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { Readable } from "node:stream";

const PORT = Number(process.env.PORT || 10000);
const HOST = process.env.HOST || "0.0.0.0";
const PROXY_PREFIX = "/truforge-api";
const DIST_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "dist");

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

const CONTENT_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".gif": "image/gif",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".webp": "image/webp",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

let upstreamBase;
let upstreamConfigError;

try {
  const configured = process.env.TRUEFORGE_BASE_URL?.trim();
  if (!configured) {
    throw new Error("TRUEFORGE_BASE_URL is not configured");
  }
  upstreamBase = new URL(configured);
  if (upstreamBase.protocol !== "http:" && upstreamBase.protocol !== "https:") {
    throw new Error("TRUEFORGE_BASE_URL must use http:// or https://");
  }
} catch (error) {
  upstreamConfigError = error instanceof Error ? error.message : String(error);
  console.error(`TrueForge proxy is not configured: ${upstreamConfigError}`);
}

function json(res, status, body) {
  const payload = JSON.stringify(body);
  res.statusCode = status;
  res.setHeader("content-type", "application/json; charset=utf-8");
  res.setHeader("content-length", Buffer.byteLength(payload));
  res.end(payload);
}

function requestHeaders(req) {
  const headers = new Headers();
  for (const [name, value] of Object.entries(req.headers)) {
    if (HOP_BY_HOP_HEADERS.has(name) || name === "host" || name === "content-length" || value == null) {
      continue;
    }
    headers.set(name, Array.isArray(value) ? value.join(", ") : value);
  }
  return headers;
}

function upstreamUrl(requestUrl) {
  const incoming = new URL(requestUrl, "http://sentinel.local");
  const suffix = incoming.pathname.slice(PROXY_PREFIX.length).replace(/^\/+/, "");
  const base = new URL(upstreamBase);
  const basePath = base.pathname.endsWith("/") ? base.pathname : `${base.pathname}/`;
  base.pathname = `${basePath}${suffix}`;
  base.search = incoming.search;
  return base;
}

async function readBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  return chunks.length ? Buffer.concat(chunks) : undefined;
}

async function proxyToTrueForge(req, res) {
  if (!upstreamBase) {
    json(res, 503, {
      error: "TrueForge proxy is not configured.",
      detail: "Set TRUEFORGE_BASE_URL on the sentinel-ui Render service and redeploy.",
    });
    return;
  }

  const target = upstreamUrl(req.url || PROXY_PREFIX);
  try {
    const method = req.method || "GET";
    const response = await fetch(target, {
      method,
      headers: requestHeaders(req),
      body: method === "GET" || method === "HEAD" ? undefined : await readBody(req),
      redirect: "manual",
    });

    res.statusCode = response.status;
    response.headers.forEach((value, name) => {
      if (!HOP_BY_HOP_HEADERS.has(name)) res.setHeader(name, value);
    });

    if (!response.body) {
      res.end();
      return;
    }
    Readable.fromWeb(response.body).pipe(res);
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    console.error(`TrueForge request failed (${target}): ${detail}`);
    json(res, 502, { error: "Unable to reach the TrueForge server.", detail });
  }
}

function safeStaticPath(urlPath) {
  let decoded;
  try {
    decoded = decodeURIComponent(urlPath);
  } catch {
    return null;
  }
  const candidate = path.resolve(DIST_DIR, `.${decoded}`);
  return candidate === DIST_DIR || candidate.startsWith(`${DIST_DIR}${path.sep}`) ? candidate : null;
}

async function serveStatic(req, res) {
  const requestUrl = new URL(req.url || "/", "http://sentinel.local");
  const requestedPath = requestUrl.pathname === "/" ? "/index.html" : requestUrl.pathname;
  const candidate = safeStaticPath(requestedPath);
  if (!candidate) {
    json(res, 400, { error: "Invalid asset path." });
    return;
  }

  let filePath = candidate;
  try {
    const stat = await fs.stat(filePath);
    if (!stat.isFile()) throw new Error("not a file");
  } catch {
    // React Router-style client routes should receive the app shell. Missing
    // assets still become a 404 instead of returning index.html.
    if (path.extname(requestedPath)) {
      res.statusCode = 404;
      res.end("Not found");
      return;
    }
    filePath = path.join(DIST_DIR, "index.html");
  }

  try {
    const stat = await fs.stat(filePath);
    res.statusCode = 200;
    res.setHeader("content-type", CONTENT_TYPES[path.extname(filePath).toLowerCase()] || "application/octet-stream");
    res.setHeader("content-length", stat.size);
    if (path.basename(filePath) === "index.html") {
      res.setHeader("cache-control", "no-cache");
    } else {
      res.setHeader("cache-control", "public, max-age=31536000, immutable");
    }
    if (req.method === "HEAD") {
      res.end();
      return;
    }
    createReadStream(filePath).pipe(res);
  } catch {
    json(res, 500, { error: "Static application files are unavailable. Run the UI build first." });
  }
}

const server = createServer(async (req, res) => {
  const pathname = new URL(req.url || "/", "http://sentinel.local").pathname;

  if (pathname === "/health") {
    json(res, upstreamConfigError ? 503 : 200, {
      status: upstreamConfigError ? "error" : "ok",
      trueforgeConfigured: !upstreamConfigError,
      ...(upstreamConfigError ? { detail: upstreamConfigError } : {}),
    });
    return;
  }

  if (pathname === PROXY_PREFIX || pathname.startsWith(`${PROXY_PREFIX}/`)) {
    await proxyToTrueForge(req, res);
    return;
  }

  if (req.method !== "GET" && req.method !== "HEAD") {
    json(res, 405, { error: "Method not allowed." });
    return;
  }
  await serveStatic(req, res);
});

server.listen(PORT, HOST, () => {
  console.log(`sentinel-ui listening on http://${HOST}:${PORT}`);
  if (upstreamBase) console.log(`TrueForge proxy target: ${upstreamBase.origin}`);
});