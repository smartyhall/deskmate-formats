"use strict";
/** Minimal static server so a qualification run needs no external process. */
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".xml": "application/xml; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".webp": "image/webp",
  ".svg": "image/svg+xml",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".otf": "font/otf",
  ".ttf": "font/ttf",
  ".ico": "image/x-icon",
};

function resolveTarget(root, pathname) {
  const decoded = decodeURIComponent(pathname.split("?")[0]);
  if (decoded.includes("\0")) return null;
  const relative = path.normalize(decoded).replace(/^(\.\.[/\\])+/, "");
  let target = path.join(root, relative);
  if (!target.startsWith(root)) return null;
  if (fs.existsSync(target) && fs.statSync(target).isDirectory()) target = path.join(target, "index.html");
  return target;
}

function serve(rootDirectory, { port = 0, host = "127.0.0.1" } = {}) {
  const root = path.resolve(rootDirectory);
  if (!fs.existsSync(root)) throw new Error(`serve directory does not exist: ${root}`);
  const server = http.createServer((request, response) => {
    const target = resolveTarget(root, request.url || "/");
    if (!target || !fs.existsSync(target) || !fs.statSync(target).isFile()) {
      response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
      response.end("not found");
      return;
    }
    response.writeHead(200, {
      "content-type": TYPES[path.extname(target).toLowerCase()] || "application/octet-stream",
      "cache-control": "no-store",
    });
    fs.createReadStream(target).pipe(response);
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, host, () => {
      const address = server.address();
      resolve({
        url: `http://${host}:${address.port}`,
        port: address.port,
        close: () => new Promise((done) => server.close(() => done())),
      });
    });
  });
}

module.exports = { serve, resolveTarget, TYPES };
