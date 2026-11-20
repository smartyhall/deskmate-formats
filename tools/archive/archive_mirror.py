"""Polite, resumable HTTP directory-index archiver; no third-party dependencies."""
import argparse
import datetime as dt
import email.utils
import hashlib
import html.parser
import http.client
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import time
import tomllib
import urllib.error
import urllib.parse as url
import urllib.request as request

AGENT = "DeskMatePreservationMirror/1.0 (private research; single connection)"
CHUNK = 16384


class Stop(Exception):
    pass


class Invalid(Exception):
    pass


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Listing(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.title, self.in_title = [], [], False

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.extend(v for k, v in attrs if k == "href" and v is not None)
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)


class Robots:
    """Specific user-agent groups, longest rules, Allow wins ties."""
    def __init__(self, text):
        groups, agents, rules = [], [], []
        for line in text.splitlines():
            key, sep, value = line.split("#", 1)[0].partition(":")
            if not sep:
                continue
            key, value = key.strip().lower(), value.strip()
            if key == "user-agent":
                if rules:
                    groups.append((agents, rules))
                    agents, rules = [], []
                agents.append(value.lower())
            elif agents:
                rules.append((key, value))
        groups.append((agents, rules))
        product = AGENT.split("/")[0].lower()
        matched = [(max((len(a) if a != "*" else 0 for a in aa
                         if a == "*" or (a and a in product)), default=-1), rr)
                   for aa, rr in groups]
        best = max((n for n, _ in matched), default=-1)
        self.rules, self.delay = [], 0.0
        for n, rr in matched:
            if n < 0 or n != best:
                continue
            for key, value in rr:
                if key in ("allow", "disallow") and value:
                    end = value.endswith("$")
                    pattern = self.norm(value[:-1] if end else value)
                    regex = "^" + ".*".join(re.escape(x) for x in pattern.split("*"))
                    self.rules.append((len(pattern.replace("*", "")), key == "allow",
                                       re.compile(regex + ("$" if end else ""))))
                elif key in ("crawl-delay", "request-rate"):
                    try:
                        if key == "request-rate":
                            count, seconds = value.split("/")
                            delay = float(seconds) / float(count)
                        else:
                            delay = float(value)
                        if math.isfinite(delay):
                            self.delay = max(self.delay, delay)
                    except (ValueError, ZeroDivisionError):
                        pass

    @staticmethod
    def norm(s):
        unreserved = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
        return re.sub(r"%([0-9a-fA-F]{2})",
                      lambda m: chr(int(m[1], 16)) if chr(int(m[1], 16)) in unreserved
                      else m[0].upper(), s)

    def allowed(self, address):
        path = self.norm(url.urlsplit(address).path)
        return max(((n, a) for n, a, r in self.rules if r.match(path)),
                   default=(0, True))[1]


def load_config(path, name=None):
    with Path(path).open("rb") as f:
        data = tomllib.load(f)
    targets = data.get("targets", {})
    if not isinstance(targets, dict) or not targets:
        raise Invalid("Configuration needs at least one [targets.NAME] table.")
    if name is None:
        if len(targets) != 1:
            raise Invalid("Choose a named target with --target.")
        name = next(iter(targets))
    if name not in targets:
        raise Invalid("Unknown target: " + name)
    opts = dict(targets[name])
    known = {"root", "destination", "rate_kib", "delay_seconds", "reserve_gib",
             "timeout_seconds", "priority_prefixes"}
    if set(opts) - known:
        raise Invalid("Unknown configuration keys: " + ", ".join(sorted(set(opts)-known)))
    if not isinstance(opts.get("destination"), str) or not opts["destination"]:
        raise Invalid("destination must be a nonempty path.")
    dest = Path(opts["destination"]).expanduser()
    opts["destination"] = dest if dest.is_absolute() else Path(path).resolve().parent / dest
    return opts


class Mirror:
    """The original TVDog database schema and relative local paths are retained."""
    def __init__(self, root, destination, rate_kib=128, delay_seconds=2,
                 reserve_gib=5, timeout_seconds=60, priority_prefixes=()):
        origin = url.urlsplit(root)
        if (origin.scheme not in ("http", "https") or not origin.hostname
                or origin.username is not None or origin.password is not None
                or origin.query or origin.fragment or not origin.path.endswith("/")
                or any(x in (".", "..") for x in url.unquote(origin.path).split("/"))
                or "\\" in url.unquote(origin.path)):
            raise Invalid("root must be an absolute HTTP(S) directory URL ending in /.")
        if (not isinstance(rate_kib, int) or not 1 <= rate_kib <= 1024
                or not math.isfinite(delay_seconds) or not 1 <= delay_seconds <= 86400
                or not math.isfinite(reserve_gib) or reserve_gib < 0
                or not math.isfinite(timeout_seconds) or not 1 <= timeout_seconds <= 300):
            raise Invalid("Invalid rate, delay, free-space reserve or timeout.")
        if (not isinstance(priority_prefixes, (list, tuple))
                or any(not isinstance(x, str) or not x for x in priority_prefixes)):
            raise Invalid("priority_prefixes must be an array of nonempty strings.")
        self.root, self.origin = root, origin
        self.dest = Path(destination).resolve()
        self.rate, self.delay = rate_kib * 1024, delay_seconds
        self.reserve, self.timeout = int(reserve_gib * 1024**3), timeout_seconds
        self.priorities = priority_prefixes
        self.stop_file = self.dest / "STOP"
        for name in ("originals", "listings", "manifests", "transfer-state", "mapped"):
            (self.dest / name).mkdir(parents=True, exist_ok=True)
        self.state = self.dest / "transfer-state"
        self.db = sqlite3.connect(self.state / "mirror.sqlite3", timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""CREATE TABLE IF NOT EXISTS entries (
          rel TEXT PRIMARY KEY, url TEXT NOT NULL, kind TEXT NOT NULL,
          local TEXT COLLATE NOCASE UNIQUE NOT NULL, status TEXT DEFAULT 'pending',
          bytes INTEGER, sha256 TEXT, etag TEXT, modified TEXT, expected INTEGER,
          attempts INTEGER DEFAULT 0, observed TEXT, error TEXT);
          CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);""")
        old = self.meta("root")
        if old and old != root:
            self.db.close()
            raise Invalid("Destination belongs to a different URL; use the exact original root.")
        self.setmeta("root", root)
        self.add("", "dir", root)
        self.db.commit()
        self.last = 0.0
        self.robots = None
        self.opener = request.build_opener(NoRedirect())

    def meta(self, key, default=None):
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def setmeta(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, str(value)))
        self.db.commit()

    def check_stop(self):
        if self.stop_file.exists():
            raise Stop("STOP file present; remove it explicitly before resuming.")

    def wait(self, seconds):
        deadline = time.monotonic() + max(0, seconds)
        while True:
            self.check_stop()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(0.25, remaining))

    def space(self, extra=0):
        if shutil.disk_usage(self.dest).free < self.reserve + extra:
            raise Stop("Free-space reserve reached.")

    def add(self, rel, kind, address):
        if self.db.execute("SELECT 1 FROM entries WHERE rel=?", (rel,)).fetchone():
            return
        if not rel:
            local = "originals"
        else:
            parent, _, name = rel.rstrip("/").rpartition("/")
            parent = parent + "/" if parent else ""
            row = self.db.execute("SELECT local FROM entries WHERE rel=?", (parent,)).fetchone()
            if row is None:
                raise Invalid("Missing parent directory.")
            local = row[0] + "/" + name
            unsafe = (not name.isascii() or re.search(r'[<>:"/\\|?*\x00-\x1f]', name)
                      or name.endswith((".", " "))
                      or re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", name, re.I))
            if (unsafe or len(str(self.dest / local)) > 220 or
                    self.db.execute("SELECT 1 FROM entries WHERE local=? COLLATE NOCASE",
                                    (local,)).fetchone() or (self.dest / local).exists()):
                local = "mapped/" + hashlib.sha256(rel.encode()).hexdigest()
        self.db.execute("INSERT INTO entries(rel,url,kind,local) VALUES(?,?,?,?)",
                        (rel, address, kind, local))

    def update(self, rel, **values):
        self.db.execute("UPDATE entries SET " + ",".join(k + "=?" for k in values)
                        + " WHERE rel=?", (*values.values(), rel))
        self.db.commit()

    def cooldown(self):
        self.check_stop()
        remaining = float(self.meta("not_before", "0")) - time.time()
        if remaining > 0:
            raise Stop("Host cooldown remains active until " +
                       dt.datetime.fromtimestamp(time.time()+remaining, dt.timezone.utc).isoformat())

    def pause(self, reason, retry=None):
        count = int(self.meta("host_failures", "0")) + 1
        seconds = [60, 300, 900, 3600][min(count-1, 3)]
        if retry:
            try:
                seconds = max(seconds, int(retry))
            except ValueError:
                try:
                    seconds = max(seconds, email.utils.parsedate_to_datetime(retry).timestamp()-time.time())
                except (ValueError, TypeError, OverflowError):
                    pass
        self.setmeta("host_failures", count)
        self.setmeta("not_before", time.time()+seconds)
        raise Stop(reason + "; host paused for at least " + str(int(seconds)) + " seconds.")

    def open(self, address, headers=None, policy=False):
        self.cooldown()
        self.space()
        if not policy and not self.robots.allowed(address):
            raise Invalid("robots.txt disallows this path")
        self.wait(self.delay - (time.monotonic()-self.last))
        req = request.Request(address, headers={"User-Agent": AGENT, "Accept-Encoding": "identity",
                                                **(headers or {})})
        try:
            return self.opener.open(req, timeout=self.timeout)
        except urllib.error.HTTPError as e:
            self.last = time.monotonic()
            if e.code in (301, 302, 303, 307, 308):
                target = url.urljoin(address, e.headers.get("Location", ""))
                e.close()
                a, b = url.urlsplit(address), url.urlsplit(target)
                if (a.scheme == "http" and b.scheme == "https" and a.netloc == b.netloc
                        and a.path == b.path and not b.query and not b.fragment):
                    return self.open(target, headers, policy)
                raise Invalid("Unapproved redirect: " + target)
            if e.code == 429 or e.code >= 500:
                code, retry = e.code, e.headers.get("Retry-After")
                e.close()
                self.pause("HTTP " + str(code), retry)
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            self.last = time.monotonic()
            self.pause(str(e))

    def stream(self, response, output, limit=None, existing=0):
        start, total = time.monotonic(), 0
        while True:
            self.check_stop()
            self.space(CHUNK)
            try:
                # read1 returns available buffered bytes rather than filling a full chunk.
                data = response.read1(CHUNK)
            except (OSError, http.client.HTTPException) as e:
                self.pause("Read failure: " + str(e))
            if not data:
                break
            total += len(data)
            if limit is not None and total > limit:
                raise Invalid("Response exceeds its declared or configured size.")
            output.write(data)
            self.wait(total/self.rate-(time.monotonic()-start))
        return existing+total

    @staticmethod
    def encoding(response):
        if response.headers.get("Content-Encoding", "identity").lower() not in ("", "identity"):
            raise Invalid("Unexpected response encoding.")

    def metadata(self, address, maximum, policy=False):
        import io
        response = self.open(address, policy=policy)
        try:
            with response:
                self.encoding(response)
                buf = io.BytesIO()
                size = self.stream(response, buf, maximum)
                expected = response.headers.get("Content-Length")
                if expected is not None and size != int(expected):
                    self.pause("Incomplete metadata response")
                return buf.getvalue(), response.headers.get("Content-Type", "")
        finally:
            self.last = time.monotonic()

    def load_robots(self):
        address = url.urlunsplit((self.origin.scheme, self.origin.netloc, "/robots.txt", "", ""))
        try:
            raw, _ = self.metadata(address, 512*1024, policy=True)
        except urllib.error.HTTPError as e:
            code = e.code
            e.close()
            if code not in (404, 410):
                raise Stop("Unable to verify robots.txt: HTTP " + str(code))
            raw = b""
        except Invalid as e:
            raise Stop("Unable to verify robots.txt: " + str(e))
        text = raw.decode("utf-8-sig", errors="strict")
        if text.lstrip().startswith("<"):
            raise Stop("Unexpected markup in robots.txt; inspect source policy.")
        (self.dest/"listings"/"robots.txt").write_bytes(raw)
        self.robots = Robots(text)
        self.delay = max(self.delay, self.robots.delay)

    def child(self, base, href):
        u, b = url.urlsplit(url.urljoin(base, href)), url.urlsplit(base)
        if (u.scheme not in ("http", "https") or u.netloc != self.origin.netloc
                or u.query or u.fragment):
            return None
        path, bp, root = (url.unquote(x, errors="strict")
                          for x in (u.path, b.path, self.origin.path))
        if not path.startswith(bp) or path == bp or not path.startswith(root):
            return None
        tail = path[len(bp):]
        kind = "dir" if tail.endswith("/") else "file"
        leaf = tail.rstrip("/")
        if (not leaf or "/" in leaf or "\\" in leaf or leaf in (".", "..")
                or any(ord(c) < 32 for c in leaf)):
            return None
        canonical = url.urlunsplit((self.origin.scheme, self.origin.netloc,
                                    url.quote(path, safe="/"), "", ""))
        return path[len(root):], kind, canonical

    def directory(self, row):
        raw, ctype = self.metadata(row["url"], 16*1024**2)
        key = hashlib.sha256(row["rel"].encode()).hexdigest()
        sha = hashlib.sha256(raw).hexdigest()
        listing = self.dest/"listings"/(key+"-"+sha+".html")
        if not listing.exists():
            listing.write_bytes(raw)
        parser = Listing()
        parser.feed(raw.decode("utf-8", errors="strict"))
        title = " ".join(parser.title).strip().lower()
        if ("text/html" not in ctype.lower()
                or not title.startswith(("index of ", "directory listing"))):
            raise Invalid("Unrecognized HTML directory index; saved for inspection.")
        children = {child for href in parser.links if (child := self.child(row["url"], href))}
        (self.dest/row["local"]).mkdir(parents=True, exist_ok=True)
        for rel, kind, address in sorted(children):
            self.add(rel, kind, address)
        self.update(row["rel"], status="verified", bytes=len(raw), sha256=sha,
                    observed=now(), error=None)

    def file(self, row):
        dest = self.dest/row["local"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = self.state/(hashlib.sha256(row["rel"].encode()).hexdigest()+".part")
        if dest.exists():
            if row["sha256"] and dest.stat().st_size == row["expected"] and digest(dest) == row["sha256"]:
                self.update(row["rel"], status="verified", bytes=row["expected"], observed=now(), error=None)
                return
            raise Invalid("Unexpected existing file; refusing to overwrite.")
        n = part.stat().st_size if part.exists() else 0
        if part.exists() and row["sha256"] and n == row["expected"] and digest(part) == row["sha256"]:
            os.replace(part, dest)
            self.update(row["rel"], status="verified", bytes=n, observed=now(), error=None)
            return
        etag = row["etag"]
        strong = etag and not etag.startswith("W/")
        validator = etag if strong else row["modified"]
        headers = {}
        if n and validator and row["expected"] is not None and n < row["expected"]:
            headers = {"Range": "bytes="+str(n)+"-", "If-Range": validator}
        response = self.open(row["url"], headers)
        try:
            with response:
                self.encoding(response)
                html = row["rel"].lower().endswith((".html", ".htm", ".shtml"))
                if not html and "text/html" in response.headers.get("Content-Type", "").lower():
                    raise Invalid("Unexpected HTML for a non-HTML file.")
                length = response.headers.get("Content-Length")
                length = int(length) if length is not None else None
                new_etag, modified = response.headers.get("ETag"), response.headers.get("Last-Modified")
                if response.status == 206:
                    m = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
                    if (not headers or not m or int(m[1]) != n or int(m[3]) != row["expected"]
                            or int(m[2]) != int(m[3])-1
                            or (length is not None and length != int(m[3])-n)
                            or (strong and new_etag != etag) or (not strong and modified != validator)):
                        raise Invalid("Range or validator mismatch; partial retained.")
                    expected, mode = int(m[3]), "ab"
                elif response.status == 200:
                    n, expected, mode = 0, length, "wb"
                else:
                    raise Invalid("Unexpected HTTP response status.")
                if expected is not None and expected < n:
                    raise Invalid("Invalid response length.")
                self.space(max(0, (expected or n)-n))
                if mode == "wb":
                    part.unlink(missing_ok=True)
                self.update(row["rel"], status="partial", etag=new_etag, modified=modified,
                            expected=expected, sha256=None, error=None)
                with part.open(mode) as f:
                    try:
                        size = self.stream(response, f, None if expected is None else expected-n, n)
                    finally:
                        f.flush()
                        os.fsync(f.fileno())
                if expected is not None and size != expected:
                    self.pause("Incomplete file response")
                if expected is None and response.headers.get("Transfer-Encoding", "").lower() != "chunked":
                    raise Invalid("No verified length or chunked framing; partial retained.")
                with part.open("rb") as f:
                    prefix = f.read(512).lstrip().lower()
                if not html and prefix.startswith((b"<!doctype html", b"<html")):
                    raise Invalid("HTML-looking non-HTML file; partial retained.")
                sha = digest(part)
                self.update(row["rel"], sha256=sha, expected=size, bytes=size)
                os.replace(part, dest)
                self.update(row["rel"], status="verified", bytes=size, sha256=sha,
                            observed=now(), error=None)
        finally:
            self.last = time.monotonic()

    def next_row(self):
        # Prioritize ancestors of configured paths so those paths become discoverable.
        def order(row):
            rel = row["rel"]
            for i, prefix in enumerate(self.priorities):
                if rel.startswith(prefix) or (row["kind"] == "dir" and prefix.startswith(rel)):
                    return i, rel
            return len(self.priorities) + (row["kind"] != "dir"), rel
        return min(self.db.execute("SELECT * FROM entries WHERE status IN "
                                   "('pending','partial','deferred')"), key=order, default=None)

    def run(self, limit=0, retry=False):
        self.cooldown()
        self.load_robots()
        if retry:
            self.db.execute("UPDATE entries SET status='pending',error=NULL "
                            "WHERE status IN ('invalid','unavailable')")
            self.db.commit()
        count = 0
        while not limit or count < limit:
            self.check_stop()
            row = self.next_row()
            if row is None:
                break
            self.update(row["rel"], attempts=row["attempts"]+1)
            print(f"[{now()}] {row['kind']} {row['rel'] or '/'}", flush=True)
            try:
                (self.directory if row["kind"] == "dir" else self.file)(row)
                self.setmeta("host_failures", 0)
                self.setmeta("not_before", 0)
            except urllib.error.HTTPError as e:
                code = e.code
                e.close()
                status = "blocked" if code in (401, 403) else "unavailable" if code in (404, 410) else "invalid"
                self.update(row["rel"], status=status, observed=now(), error="HTTP "+str(code))
                if status == "blocked":
                    raise Stop("Access denied; examine source policy before continuing.")
            except (Invalid, UnicodeError) as e:
                self.update(row["rel"], status="blocked" if str(e).startswith("robots.txt") else "invalid",
                            error=str(e), observed=now())
            except Stop as e:
                current = self.db.execute("SELECT status FROM entries WHERE rel=?", (row["rel"],)).fetchone()[0]
                self.update(row["rel"], status="partial" if current == "partial" else "deferred",
                            error=str(e), observed=now())
                raise
            count += 1
            if count % 25 == 0:
                self.export()

    def export(self):
        target = self.dest/"manifests"/"inventory.jsonl"
        tmp = target.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8", newline="\n") as f:
            for row in self.db.execute("SELECT * FROM entries ORDER BY rel"):
                f.write(json.dumps(dict(row), ensure_ascii=True)+"\n")
        os.replace(tmp, target)
        result = summary(self.db)
        target = self.dest/"manifests"/"summary.json"
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
        os.replace(tmp, target)
        print(json.dumps(result, indent=2), flush=True)


def summary(db):
    counts = dict(db.execute("SELECT status,COUNT(*) FROM entries GROUP BY status"))
    files, size = db.execute("SELECT COUNT(*),COALESCE(SUM(bytes),0) FROM entries "
                             "WHERE kind='file' AND status='verified'").fetchone()
    meta = dict(db.execute("SELECT key,value FROM meta"))
    return {"source": meta.get("root"), "observed_utc": now(), "status_counts": counts,
            "verified_files": files, "verified_file_bytes": size,
            "complete_for_discovered_tree": bool(counts) and counts.get("verified", 0) == sum(counts.values()),
            "host_not_before_epoch": float(meta.get("not_before", 0))}


def acquire_lock(dest):
    # Same lock path and first-byte Windows lock as original Mirror-TVDog.ps1.
    lock = (dest/"mirror.lock").open("a+b")
    try:
        lock.seek(0, 2)
        if lock.tell() == 0:
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close()
        raise Stop("Another downloader owns this destination.")
    return lock


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--target")
    p.add_argument("--policy-checked", action="store_true")
    modes = p.add_mutually_exclusive_group()
    modes.add_argument("--status", action="store_true")
    modes.add_argument("--stop", action="store_true")
    modes.add_argument("--clear-stop", action="store_true")
    p.add_argument("--max-items", type=int, default=0)
    p.add_argument("--retry-unavailable", action="store_true")
    args = p.parse_args(argv)
    if args.max_items < 0:
        p.error("--max-items must be nonnegative")
    mirror = lock = None
    code = 0
    try:
        opts = load_config(args.config, args.target)
        dest = Path(opts["destination"]).resolve()
        if args.status:
            # Live status is read-only and does not take the writer's lock.
            dbpath = dest/"transfer-state"/"mirror.sqlite3"
            with sqlite3.connect(dbpath.as_uri()+"?mode=ro", uri=True, timeout=5) as db:
                print(json.dumps({**summary(db), "stop_requested": (dest/"STOP").exists()}, indent=2))
            db.close()
            return 0
        if args.stop:
            if not dest.is_dir():
                raise Invalid("Destination does not exist.")
            (dest/"STOP").touch()
            print("Stop requested: " + str(dest/"STOP"))
            return 0
        if args.clear_stop:
            # Do not clear another process's stop request while it owns the lock.
            with acquire_lock(dest):
                (dest/"STOP").unlink(missing_ok=True)
            print("Stop cleared.")
            return 0
        if not args.policy_checked:
            p.error("Review source mirroring policy first; pass --policy-checked.")
        dest.mkdir(parents=True, exist_ok=True)
        lock = acquire_lock(dest)
        mirror = Mirror(**opts)
        mirror.run(args.max_items, args.retry_unavailable)
        code = 3 if mirror.db.execute("SELECT 1 FROM entries WHERE status!='verified' LIMIT 1").fetchone() else 0
    except KeyboardInterrupt:
        print("Interrupted; run again to resume.", file=sys.stderr)
        code = 130
    except (Stop, Invalid, OSError, ValueError, TypeError, sqlite3.Error) as e:
        print("Stopped: "+str(e), file=sys.stderr)
        code = 2
    finally:
        try:
            if mirror:
                try:
                    mirror.export()
                finally:
                    mirror.db.close()
        finally:
            if lock:
                lock.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
