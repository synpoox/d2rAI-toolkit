#!/usr/bin/env python3
"""Create (or update) a GitHub or Forgejo release for a version from its CHANGELOG.md section (docs/release.md "Release notes").

  py -3 release/github_release.py 1.0.0 [--service github|forgejo] [--commit SHA] [--downloader EXE] [--latest]
                                  [--dry-run] [--config release.toml]

The release body is the "### <version>" section of the changelog, plus the download links: the downloader and the
release's 7z on your download site (site.url). The 7z is not attached: it stays on the download host, which spares a
large upload from the developer's machine. --downloader attaches the small downloader exe to the release.

The tag `v<version>` is created on --commit (default: the current commit, `git rev-parse HEAD`). Run this only after the
version is live and promoted (release.sh does that): a release page for a version players cannot download is a bug.

It talks to the REST API of the service. The repository and the token come from the config ([repos]); the token from the
environment variable named there, else the token file. The token is never printed. Running it again updates the release
(title, body, the downloader asset) instead of failing. --dry-run prints the tag and the body and touches nothing.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_config  # noqa: E402

USER_AGENT = "modkit-github-release/1"


def changelog_section(text: str, version: str) -> str:
    """The body of the first "### <version>" heading of the changelog, without the heading. The heading may carry a date
    after the version. "### 1.0.0-rc1" is not the section of 1.0.0."""
    m = re.search(rf"^### {re.escape(version)}(?![0-9A-Za-z.+-])[^\n]*\n(.*?)(?=^### |^## |\Z)", text, re.M | re.S)
    if not m:
        raise SystemExit(f"the changelog has no '### {version}' section")
    return m.group(1).strip()


def release_body(cfg: dict, version: str, section: str, downloader_version="", docs_base="") -> str:
    """The changelog section plus the install links. Relative links into docs/ become absolute (release pages have none)."""
    site, mod, game, loader = cfg["site"]["url"], cfg["mod"], cfg["game"], cfg["d2rloader"]
    if docs_base:
        section = section.replace("](docs/", f"]({docs_base}")
    exe = cfg["downloader"]["exe_name"]
    line = f"**Install or update:** run the {mod['name']} downloader"
    if downloader_version:
        line += f" ({site}downloader/{downloader_version}/{exe})"
    line += f". It installs the newest release into your D2R folder's `mods\\{mod['folder']}`."
    archive = f"{mod['folder']}-{version}.7z"
    lines = [section, "", line, "",
             f"**Manual install:** [{archive}]({site}releases/{version}/{archive}), unpacked into your D2R `mods` folder.", "",
             f"Needs Diablo II: Resurrected build {game['build']} and D2RLoader {loader['version']}."]
    return "\n".join(lines) + "\n"


def read_token(cfg: dict, service: str) -> str:
    r = cfg["repos"]
    env, tok_file = r[f"{service}_token_env"], Path(os.path.expanduser(r[f"{service}_token_file"]))
    token = os.environ.get(env, "").strip()
    if not token and tok_file.is_file():
        token = tok_file.read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit(f"no {service} token: set ${env} or save one in {r[f'{service}_token_file']} (never in the repository)")
    return token


class Forge:
    """GitHub's and Forgejo's release APIs, which differ little. `opener(request) -> (status, bytes)` is replaceable for tests."""

    def __init__(self, service, api, uploads, token, opener=None):
        self.service, self.api, self.uploads, self.token = service, api.rstrip("/"), uploads.rstrip("/") if uploads else None, token
        self.opener = opener or self._urlopen

    @staticmethod
    def _urlopen(req):
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read()

    def headers(self, ctype):
        h = {"User-Agent": USER_AGENT, "Accept": "application/json", "Content-Type": ctype}
        if self.service == "github":
            h.update({"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
                      "X-GitHub-Api-Version": "2022-11-28"})
        else:
            h["Authorization"] = f"token {self.token}"
        return h

    def call(self, method, url, body=None, data=None, ctype="application/json"):
        payload = data if data is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(url, method=method, data=payload, headers=self.headers(ctype))
        try:
            _, raw = self.opener(req)
        except urllib.error.HTTPError as e:
            if e.code == 404 and method == "GET":
                return None
            detail = e.read().decode("utf-8", "replace")[:300] if hasattr(e, "read") else ""
            raise SystemExit(f"{self.service} {method} {url.split('?')[0]} failed: HTTP {e.code} {detail}")
        return json.loads(raw) if raw else None

    def find(self, tag):
        return self.call("GET", f"{self.api}/releases/tags/{urllib.parse.quote(tag)}")

    def upsert(self, tag, commit, title, body, prerelease=False, latest=False):
        fields = {"name": title, "body": body, "draft": False, "prerelease": prerelease}
        if self.service == "github":
            fields["make_latest"] = "true" if latest else "false"
        rel = self.find(tag)
        if rel:
            return self.call("PATCH", f"{self.api}/releases/{rel['id']}", fields)
        return self.call("POST", f"{self.api}/releases", {**fields, "tag_name": tag, "target_commitish": commit})

    def attach(self, rel, path: Path):
        """Upload `path` as an asset, replacing an asset of the same name."""
        for a in rel.get("assets") or []:
            if a["name"] == path.name:
                url = (f"{self.api}/releases/assets/{a['id']}" if self.service == "github"
                       else f"{self.api}/releases/{rel['id']}/assets/{a['id']}")
                self.call("DELETE", url)
        name = urllib.parse.quote(path.name)
        if self.service == "github":
            self.call("POST", f"{self.uploads}/releases/{rel['id']}/assets?name={name}", data=path.read_bytes(),
                      ctype="application/octet-stream")
            return
        b, crlf = uuid.uuid4().hex, "\r\n"
        head = (f"--{b}{crlf}Content-Disposition: form-data; name=\"attachment\"; filename=\"{path.name}\"{crlf}"
                f"Content-Type: application/octet-stream{crlf}{crlf}")
        data = head.encode() + path.read_bytes() + f"{crlf}--{b}--{crlf}".encode()
        self.call("POST", f"{self.api}/releases/{rel['id']}/assets?name={name}", data=data, ctype=f"multipart/form-data; boundary={b}")


def make_forge(cfg: dict, service: str, token: str, opener=None) -> Forge:
    r = cfg["repos"]
    if service == "github":
        repo = r["github"]
        return Forge("github", f"https://api.github.com/repos/{repo}", f"https://uploads.github.com/repos/{repo}", token, opener)
    return Forge("forgejo", f"{r['forgejo_url'].rstrip('/')}/api/v1/repos/{r['forgejo']}", None, token, opener)


def docs_base(cfg: dict, service: str) -> str:
    r = cfg["repos"]
    if service == "github":
        return f"https://github.com/{r['github']}/blob/main/docs/"
    return f"{r['forgejo_url'].rstrip('/')}/{r['forgejo']}/src/branch/main/docs/"


def release_url(cfg: dict, service: str, tag: str, rel: dict) -> str:
    if rel and rel.get("html_url"):
        return rel["html_url"]
    r = cfg["repos"]
    return (f"https://github.com/{r['github']}/releases/tag/{tag}" if service == "github"
            else f"{r['forgejo_url'].rstrip('/')}/{r['forgejo']}/releases/tag/{tag}")


def run(cfg, version, service="github", commit=None, downloader=None, downloader_version="", latest=False, dry_run=False,
        changelog_text=None, opener=None, token=None, log=print) -> str:
    version = version.lstrip("v")
    tag = f"v{version}"
    if changelog_text is None:
        changelog_text = Path(cfg["repos"]["changelog"]).read_text("utf-8")
    if downloader and not downloader_version:
        from publish_release import exe_version
        downloader_version = exe_version(downloader)
    body = release_body(cfg, version, changelog_section(changelog_text, version), downloader_version, docs_base(cfg, service))
    title = f"{cfg['mod']['name']} {version}"
    if dry_run:
        log(f"{service}: {tag} on {commit or '(current commit)'} titled {title!r}\n\n{body}")
        return ""
    forge = make_forge(cfg, service, token or read_token(cfg, service), opener)
    rel = forge.upsert(tag, commit, title, body, prerelease="-" in version, latest=latest)
    if downloader:
        forge.attach(rel, Path(downloader))
    url = release_url(cfg, service, tag, rel)
    log(url)
    return url


# ------------------------------------------------------------------- --assets: the launcher's release (schema 3, via gh)
VALIDATOR_ENV = "RESURRECTED_VALIDATE_RELEASE"  # optional: the launcher's validate-release <manifest> <feed> [<archive>]


class PublishFailed(SystemExit):
    pass


def read_sums(path: Path) -> dict:
    """SHA256SUMS (sha256sum format) -> {name: sha256}."""
    out = {}
    for line in path.read_text("utf-8").splitlines():
        sha, _, name = line.partition("  ")
        if name:
            out[name.lstrip("*")] = sha
    return out


def check_assets(folder: Path, archive: str, sevenzip=None, feed_path=None) -> list:
    """Problems of the release assets in `folder`: each must match SHA256SUMS, the manifest and feed must pass every
    launcher rule (the 7z's listing included), and the launcher's own validator when VALIDATOR_ENV names one.
    `feed_path`: a shared catalog feed (catalog.feed_url), which is not one of the release's assets; default
    folder/feed.json, an asset listed in SHA256SUMS."""
    import package_release as pr
    folder = Path(folder)
    names = [archive, pr.CATALOG_MANIFEST] + ([] if feed_path else [pr.FEED])
    feed_path = Path(feed_path or folder / pr.FEED)
    if not (folder / "SHA256SUMS").is_file():
        return [f"no SHA256SUMS in {folder}"]
    sums = read_sums(folder / "SHA256SUMS")
    bad = [f"{n}: missing" for n in names if not (folder / n).is_file()]
    if bad:
        return bad
    bad = [f"{n}: sha256 does not match SHA256SUMS" for n in names if sums.get(n) != pr.sha256(folder / n)]
    if set(sums) != set(names):
        bad.append(f"SHA256SUMS lists {sorted(sums)}, the release assets are {sorted(names)}")
    if not feed_path.is_file():
        return bad + [f"{feed_path}: missing"]
    man_bytes, feed_bytes = (folder / pr.CATALOG_MANIFEST).read_bytes(), feed_path.read_bytes()
    try:
        man, feed = json.loads(man_bytes), json.loads(feed_bytes)
    except ValueError as e:
        return bad + [f"not JSON: {e}"]
    bad += pr.catalog_problems(man, feed, man_bytes, folder / archive, feed_bytes, sevenzip)
    if not bad:
        bad += launcher_validation(folder / pr.CATALOG_MANIFEST, feed_path, folder / archive)
    return bad


def launcher_validation(manifest: Path, feed: Path, archive: Path = None) -> list:
    """The launcher's own validate-release on these files when VALIDATOR_ENV names it; [] = valid, or not set."""
    exe = os.environ.get(VALIDATOR_ENV)
    if not exe:
        return []
    try:
        r = subprocess.run([exe, str(manifest), str(feed), *([str(archive)] if archive else [])],
                           capture_output=True, text=True, errors="replace")
    except OSError as e:
        return [f"{VALIDATOR_ENV} ({exe}) does not run: {e}"]
    return [f"{VALIDATOR_ENV} ({exe}) refused it: {(r.stdout + r.stderr).strip()[-600:]}"] if r.returncode else []


def assets_body(cfg: dict, man: dict, archive: str) -> str:
    builds = ", ".join(g["build"] for g in man["compatibility"]["game_builds"])
    return (f"{man['release_notes'].strip()}\n\n**Install or update:** in the Resurrected launcher, or unpack `{archive}` into your "
            f"D2R `mods` folder.\n\nNeeds Diablo II: Resurrected {builds} and D2RLoader "
            f"{', '.join(man['compatibility']['loader_versions'])} (https://d2rloader.net/download.html).\n")


def gh_runner(args):
    try:
        return subprocess.run(["gh", *args], capture_output=True, text=True, errors="replace")
    except OSError as e:
        raise PublishFailed(f"cannot run gh (GitHub CLI, https://cli.github.com): {e}")


def latest_tag(gh, repo):
    """The tag of the repository's current Latest release, "" when it has none."""
    r = gh(["release", "view", "-R", repo, "--json", "tagName", "-q", ".tagName"])
    return r.stdout.strip() if r.returncode == 0 else ""


def publish_assets(cfg: dict, version: str, dist, commit=None, dry_run=False, gh=gh_runner, sevenzip=None, log=print,
                   skip_launcher_validation=False, allow_older=False) -> str:
    """Publish dist/ (package_release.py with [catalog]) as the GitHub release v<version>, draft first:
    create the draft, upload the 7z, release-manifest.json, feed.json and SHA256SUMS, download them back and check them
    (SHA256SUMS, every launcher rule, $RESURRECTED_VALIDATE_RELEASE), and only then make it public and Latest, which
    moves releases/latest/download/feed.json to it. Any failure leaves the draft and raises PublishFailed (exit 1).
    A release that is already public is never touched: a published release ID never changes. A real run needs the
    launcher's validator ($RESURRECTED_VALIDATE_RELEASE) unless skip_launcher_validation, and refuses a version older
    than the current Latest unless allow_older. The dry run makes the same read-only gh checks.
    With a shared catalog feed (catalog.feed_url) the release carries no feed.json: once it is public, publish_feed
    merges it into the shared feed."""
    import package_release as pr
    version, dist, repo = version.lstrip("v"), Path(dist), cfg["repos"]["github"]
    tag = pr.release_tag(version)
    shared = pr.shared_feed(cfg)
    names = [n for n in (pr.CATALOG_MANIFEST, pr.FEED, "SHA256SUMS") if not (shared and n == pr.FEED)]
    feed_path = dist / pr.FEED if shared else None  # the packager's merge: checked here, merged again by publish_feed
    if not (dist / pr.CATALOG_MANIFEST).is_file():
        raise PublishFailed(f"no {dist / pr.CATALOG_MANIFEST}: package with [catalog] set (an --incomplete build has none)")
    man = json.loads((dist / pr.CATALOG_MANIFEST).read_bytes())
    archive = str(man.get("archive", {}).get("url", "")).rsplit("/", 1)[-1]
    if man.get("archive", {}).get("url") != pr.asset_url(cfg, version, archive):
        raise PublishFailed(f"archive.url {man.get('archive', {}).get('url')!r} is not an asset of {repo} {tag}")
    if man.get("release_id") != f"{man.get('product_id')}-{version}":
        raise PublishFailed(f"{pr.CATALOG_MANIFEST} is {man.get('release_id')!r}, not version {version}")
    if not dry_run and not skip_launcher_validation and not os.environ.get(VALIDATOR_ENV):
        raise PublishFailed(f"set {VALIDATOR_ENV} to the launcher's validate-release executable (docs/release.md), or pass "
                            "--skip-launcher-validation")
    problems = check_assets(dist, archive, sevenzip, feed_path)
    if problems:
        raise PublishFailed("refusing to publish:\n  " + "\n  ".join(problems[:40]))
    if not os.environ.get(VALIDATOR_ENV):
        log(f"note: {VALIDATOR_ENV} is not set: the launcher's own validator did not run")
    seen = gh(["release", "view", tag, "-R", repo, "--json", "isDraft", "-q", ".isDraft"])
    if seen.returncode == 0 and seen.stdout.strip() != "true":
        raise PublishFailed(f"{repo} already has a public release {tag}: a published release never changes; "
                            "package a new version")
    latest = latest_tag(gh, repo)
    moved = "releases/latest" if shared else "the launcher's feed (releases/latest/download/feed.json)"
    if latest and older_than(version, latest.lstrip("v")) and not allow_older:
        raise PublishFailed(f"{tag} is older than the current Latest {latest}; making it Latest moves {moved} back to "
                            "it. Pass --allow-older if that is meant")
    assets = [str(dist / n) for n in (archive, *names)]
    with tempfile.TemporaryDirectory() as tmp:
        body = Path(tmp) / "body.md"
        body.write_text(assets_body(cfg, man, archive), encoding="utf-8")
        # no --prerelease: releases/latest skips pre-releases; without catalog.feed_url it carries the launcher's feed
        create = ["release", "create", tag, "-R", repo, "--draft", "--title", f"{cfg['mod']['name']} {version}",
                  "--notes-file", str(body)] + (["--target", commit] if commit else [])
        upload = ["release", "upload", tag, *assets, "-R", repo, "--clobber"]
        back = Path(tmp) / "back"
        download = ["release", "download", tag, "-R", repo, "-D", str(back),
                    *[x for n in (archive, *names) for x in ("-p", n)]]
        public = ["release", "edit", tag, "-R", repo, "--draft=false", "--latest"]
        steps = ([] if seen.returncode == 0 else [create]) + [upload, download, public]
        if dry_run:
            log(f"{tag}: " + ("an existing draft would be reused" if seen.returncode == 0 else "no release yet")
                + f"; current Latest: {latest or 'none'}")
            for c in steps:
                log("would run: gh " + subprocess.list2cmdline(c))
            log(f"dry run: {dist} passes every check; nothing was sent")
            if shared:
                publish_feed(cfg, version, dist, dry_run=True, gh=gh, log=log, allow_older=allow_older, release_public=False)
            return ""

        def run(args, what):
            r = gh(args)
            if r.returncode != 0:
                raise PublishFailed(f"gh {what} failed ({r.returncode}): {(r.stdout + r.stderr).strip()[-600:]}\n"
                                    f"{tag} stays a draft (if it was created): run again to reuse it, or delete it")
            return r

        if seen.returncode == 0:
            log(f"{tag}: reusing the existing draft")
        else:
            run(create, "release create")
            log(f"{tag}: draft created on {repo}")
        run(upload, "release upload")
        log(f"{tag}: uploaded {len(assets)} assets; downloading them back")
        run(download, "release download")
        problems = check_assets(back, archive, sevenzip, feed_path)
        if not problems and (back / "SHA256SUMS").read_bytes() != (dist / "SHA256SUMS").read_bytes():
            problems = ["the downloaded SHA256SUMS is not the one in dist/"]
        if problems:
            raise PublishFailed(f"the uploaded assets of {tag} are wrong; it stays a draft:\n  " + "\n  ".join(problems[:40]))
        run(public, "release edit --draft=false --latest")
    url = f"https://github.com/{repo}/releases/tag/{tag}"
    if shared:
        log(f"{url} is public and Latest; now the shared feed")
        publish_feed(cfg, version, dist, gh=gh, log=log, allow_older=allow_older)
    else:
        log(f"{url} is public and Latest; the feed is https://github.com/{repo}/releases/latest/download/{pr.FEED}")
    return url


FEED_LOCK = "feed.lock"  # on the feed release while one publish_feed runs; uploaded without --clobber, so only one wins


def older_than(version: str, other: str) -> bool:
    """True when `version` sorts before `other`, or `other` is not a version at all (so nothing silently goes back)."""
    from publish_release import version_key
    try:
        return version_key(version) < version_key(other)
    except AttributeError:
        return True


def publish_feed(cfg: dict, version: str, dist, dry_run=False, gh=gh_runner, log=print, allow_older=False,
                 release_public=True) -> bool:
    """Merge this product's public release (dist/release-manifest.json) into the shared catalog feed, which is the
    feed.json asset of the release catalog.feed_tag of catalog.feed_repo (created once, by hand, as a pre-release).

    1. The product release must be public and its release-manifest.json asset byte-equal to dist's: the feed never
       points at a manifest players cannot download (release_public=False skips this for the dry run of --assets,
       whose release is not public yet).
    2. Take the lock: upload feed.lock without --clobber; a second publish at the same time fails here and stops.
    3. Download feed.json, replace this product's entry (every other product is kept), check the result with every
       launcher rule and $RESURRECTED_VALIDATE_RELEASE.
    4. Download feed.json again: it must still be the one merged into, else another publish got in and this one stops.
    5. Upload it (--clobber), download it back and compare, drop the lock.

    Refuses also when the feed already has another manifest under this release ID (a published release never changes)
    and when it recommends a newer release of this product unless allow_older. True when the feed changed (or would,
    in a dry run, which takes no lock and sends nothing)."""
    import package_release as pr
    if not pr.shared_feed(cfg):
        raise PublishFailed("catalog.feed_url is not set: the feed is the release's own feed.json (--assets)")
    version, dist = version.lstrip("v"), Path(dist)
    repo, tag, product_repo = cfg["catalog"]["feed_repo"], cfg["catalog"]["feed_tag"], cfg["repos"]["github"]
    if not (dist / pr.CATALOG_MANIFEST).is_file():
        raise PublishFailed(f"no {dist / pr.CATALOG_MANIFEST}: package with [catalog] set")
    man_bytes = (dist / pr.CATALOG_MANIFEST).read_bytes()
    man = json.loads(man_bytes)
    rid = man.get("release_id")
    if rid != f"{man.get('product_id')}-{version}":
        raise PublishFailed(f"{pr.CATALOG_MANIFEST} is {rid!r}, not version {version}")
    again = f"run github_release.py {version} --feed {dist} again"

    def fetch(release, owner, name, dest):
        """Bytes of one asset, None when the release has no such asset; PublishFailed on any other gh error."""
        r = gh(["release", "download", release, "-R", owner, "-p", name, "-D", str(dest)])
        if r.returncode != 0:
            if "no assets match" in (r.stdout + r.stderr).lower():
                return None
            raise PublishFailed(f"gh release download {release} -R {owner} -p {name} failed ({r.returncode}): "
                                f"{(r.stdout + r.stderr).strip()[-600:]}")
        return (Path(dest) / name).read_bytes() if (Path(dest) / name).is_file() else None

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if release_public:
            product_tag = pr.release_tag(version)
            seen = gh(["release", "view", product_tag, "-R", product_repo, "--json", "isDraft", "-q", ".isDraft"])
            if seen.returncode != 0 or seen.stdout.strip() != "false":
                raise PublishFailed(f"{product_repo} {product_tag} is not public: publish it first (--assets)")
            public = fetch(product_tag, product_repo, pr.CATALOG_MANIFEST, tmp / "public")
            if public is None:
                raise PublishFailed(f"{product_repo} {product_tag} has no {pr.CATALOG_MANIFEST}: publish it first (--assets)")
            if public != man_bytes:
                raise PublishFailed(f"the public {pr.CATALOG_MANIFEST} of {product_repo} {product_tag} (sha256 "
                                    f"{hashlib.sha256(public).hexdigest()}, {len(public)} B) is not "
                                    f"{dist / pr.CATALOG_MANIFEST} (sha256 {hashlib.sha256(man_bytes).hexdigest()}, "
                                    f"{len(man_bytes)} B): the feed must point at the bytes players download; use the "
                                    "dist/ that was published")
        home = gh(["release", "view", tag, "-R", repo, "--json", "isDraft,isPrerelease", "-q",
                   '"\\(.isDraft) \\(.isPrerelease)"'])
        if home.returncode != 0:
            raise PublishFailed(f"{repo} has no release {tag} for the shared feed: create it once, as a pre-release that is "
                                f"never Latest: gh release create {tag} -R {repo} --prerelease --latest=false "
                                f"--title \"Catalog feed\" --notes \"The launcher's catalog feed.\"")
        if home.stdout.split() != ["false", "true"]:
            raise PublishFailed(f"{repo} {tag} must be a public pre-release, so it never becomes the repository's Latest "
                                f"release (isDraft isPrerelease: {home.stdout.strip()!r}): gh release edit {tag} -R {repo} "
                                "--draft=false --prerelease --latest=false")
        locked = False
        if not dry_run:
            lock = tmp / FEED_LOCK
            lock.write_text(f"{rid}\n", encoding="utf-8")
            r = gh(["release", "upload", tag, str(lock), "-R", repo])  # no --clobber: fails while another publish holds it
            if r.returncode != 0:
                raise PublishFailed(f"cannot take the feed lock ({FEED_LOCK} on {repo} {tag}): another publish is running, "
                                    f"or one stopped without dropping it: {(r.stdout + r.stderr).strip()[-300:]}\nWhen none "
                                    f"is running: gh release delete-asset {tag} {FEED_LOCK} -R {repo} -y, then {again}")
            locked = True
        try:
            return _merge_feed(cfg, man, man_bytes, version, dist, repo, tag, tmp, fetch, again, dry_run, gh, log,
                               allow_older)
        finally:
            if locked:
                r = gh(["release", "delete-asset", tag, FEED_LOCK, "-R", repo, "-y"])
                if r.returncode != 0:
                    log(f"warning: could not drop the feed lock: gh release delete-asset {tag} {FEED_LOCK} -R {repo} -y")


def _merge_feed(cfg, man, man_bytes, version, dist, repo, tag, tmp, fetch, again, dry_run, gh, log, allow_older):
    """publish_feed steps 3-5, with the lock held (or in a dry run)."""
    import package_release as pr
    pid, rid = man["product_id"], man["release_id"]
    current_bytes = fetch(tag, repo, pr.FEED, tmp / "now")
    try:
        current, _ = pr.read_feed(tmp / "now" / pr.FEED) if current_bytes is not None else (None, None)
    except ValueError as e:
        raise PublishFailed(f"the shared feed on {repo} {tag} is refused: {e}")
    old = next((p for p in (current or {}).get("products", []) if p.get("product_id") == pid), None)
    rec = (old or {}).get("recommended") or {}
    if rec.get("release_id") == rid and (rec.get("manifest_size"), rec.get("manifest_sha256")) != \
            (len(man_bytes), hashlib.sha256(man_bytes).hexdigest()):
        raise PublishFailed(f"the shared feed already recommends {rid} with another manifest: a published release never "
                            "changes; package a new version")
    if rec.get("release_id") and rec["release_id"] != rid:
        before = rec["release_id"].removeprefix(f"{pid}-") if rec["release_id"].startswith(f"{pid}-") else ""
        if older_than(version, before) and not allow_older:
            raise PublishFailed(f"the shared feed recommends {rec['release_id']}, newer than {version}; pass "
                                "--allow-older if that is meant")
    feed = pr.catalog_feed(cfg, man, man_bytes, pr.asset_url(cfg, version, pr.CATALOG_MANIFEST), current)
    feed_bytes = pr.json_bytes(feed)
    out = tmp / pr.FEED
    out.write_bytes(feed_bytes)
    problems = pr.catalog_problems(man, feed, man_bytes, None, feed_bytes)
    problems += [] if problems else launcher_validation(dist / pr.CATALOG_MANIFEST, out)
    if problems:
        raise PublishFailed("refusing to publish the shared feed:\n  " + "\n  ".join(problems[:40]))
    if feed_bytes == current_bytes:
        log(f"the shared feed on {repo} {tag} already recommends {rid}")
        return False
    upload = ["release", "upload", tag, str(out), "-R", repo, "--clobber"]
    if dry_run:
        kept = [p["product_id"] for p in feed["products"] if p["product_id"] != pid]
        log(f"shared feed {repo} {tag}: {len(current['products']) if current else 'no'} products now; "
            f"{rid} would be recommended; kept: {', '.join(kept) or 'none'}")
        log("would run: gh " + subprocess.list2cmdline(upload))
        return True
    if fetch(tag, repo, pr.FEED, tmp / "recheck") != current_bytes:
        raise PublishFailed(f"the shared feed on {repo} {tag} changed while this release was merged into it (another "
                            f"publish?); nothing was uploaded; {again}")
    r = gh(upload)
    if r.returncode != 0:
        raise PublishFailed(f"gh release upload of the shared feed failed ({r.returncode}): "
                            f"{(r.stdout + r.stderr).strip()[-600:]}\n{again}")
    if fetch(tag, repo, pr.FEED, tmp / "back") != feed_bytes:
        raise PublishFailed(f"the shared feed on {repo} {tag} is not the one just uploaded; {again}")
    log(f"the shared feed {cfg['catalog']['feed_url']} recommends {rid}")
    return True


def main(argv=None) -> int:
    cfg = release_config.early_config(argv)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    release_config.add_config_arg(ap)
    ap.add_argument("version")
    ap.add_argument("--service", choices=("github", "forgejo"), default="github", help="where the release goes (default github)")
    ap.add_argument("--commit", help="commit to tag (default: git rev-parse HEAD)")
    ap.add_argument("--downloader", type=Path, help=f"{cfg['downloader']['exe_name']} to attach")
    ap.add_argument("--downloader-version", default="", help="its version, for the link (default: read from the exe)")
    ap.add_argument("--latest", action="store_true", help="mark as the latest release (GitHub)")
    ap.add_argument("--dry-run", action="store_true", help="print the tag and the body; no token needed, nothing is sent")
    ap.add_argument("--assets", type=Path, metavar="DIST",
                    help="publish DIST's schema 3 release for the launcher with gh: draft, upload, verify, then public")
    ap.add_argument("--skip-launcher-validation", action="store_true",
                    help=f"--assets without the launcher's validate-release (${VALIDATOR_ENV})")
    ap.add_argument("--allow-older", action="store_true", help="--assets: allow a version older than the current Latest to become Latest")
    ap.add_argument("--feed", type=Path, metavar="DIST",
                    help="only merge DIST's public release into the shared catalog feed (catalog.feed_url), for example "
                         "after a failed feed step of --assets")
    a = ap.parse_args(argv)
    if a.feed:
        try:
            publish_feed(cfg, a.version, a.feed, a.dry_run, gh=gh_runner, allow_older=a.allow_older)
        except PublishFailed as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        return 0
    if a.assets:
        if a.service != "github":
            print("error: --assets publishes to GitHub only", file=sys.stderr)
            return 1
        try:
            publish_assets(cfg, a.version, a.assets, a.commit, a.dry_run,
                           skip_launcher_validation=a.skip_launcher_validation, allow_older=a.allow_older)
        except PublishFailed as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        return 0
    commit = a.commit
    if not commit and not a.dry_run:
        r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
        if r.returncode != 0:
            print("error: no --commit and not in a git checkout", file=sys.stderr)
            return 1
        commit = r.stdout.strip()
    try:
        run(cfg, a.version, a.service, commit, a.downloader, a.downloader_version, a.latest, a.dry_run)
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
