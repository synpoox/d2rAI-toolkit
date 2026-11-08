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


def check_assets(folder: Path, archive: str, sevenzip=None) -> list:
    """Problems of the release assets in `folder`: each must match SHA256SUMS, the manifest and feed must pass every
    launcher rule (the 7z's listing included), and the launcher's own validator when VALIDATOR_ENV names one."""
    import package_release as pr
    folder = Path(folder)
    names = [archive, pr.CATALOG_MANIFEST, pr.FEED]
    if not (folder / "SHA256SUMS").is_file():
        return [f"no SHA256SUMS in {folder}"]
    sums = read_sums(folder / "SHA256SUMS")
    bad = [f"{n}: missing" for n in names if not (folder / n).is_file()]
    if bad:
        return bad
    bad = [f"{n}: sha256 does not match SHA256SUMS" for n in names if sums.get(n) != pr.sha256(folder / n)]
    man_bytes = (folder / pr.CATALOG_MANIFEST).read_bytes()
    try:
        man, feed = json.loads(man_bytes), json.loads((folder / pr.FEED).read_bytes())
        bad += pr.catalog_problems(man, feed, man_bytes, pr.archive_entries(folder / archive, sevenzip))
    except (ValueError, RuntimeError) as e:
        bad.append(str(e))
    exe = os.environ.get(VALIDATOR_ENV)
    if exe and not bad:
        try:
            r = subprocess.run([exe, str(folder / pr.CATALOG_MANIFEST), str(folder / pr.FEED), str(folder / archive)],
                               capture_output=True, text=True, errors="replace")
        except OSError as e:
            return bad + [f"{VALIDATOR_ENV} ({exe}) does not run: {e}"]
        if r.returncode != 0:
            bad.append(f"{VALIDATOR_ENV} ({exe}) refused it: {(r.stdout + r.stderr).strip()[-600:]}")
    return bad


def assets_body(cfg: dict, man: dict, archive: str) -> str:
    builds = ", ".join(g["build"] for g in man["compatibility"]["game_builds"])
    return (f"{man['release_notes'].strip()}\n\n**Install or update:** in the Resurrected launcher, or unpack `{archive}` into your "
            f"D2R `mods` folder.\n\nNeeds Diablo II: Resurrected {builds} and D2RLoader "
            f"{', '.join(man['compatibility']['loader_versions'])} (https://d2rloader.net/download.html).\n")


def gh_runner(args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, errors="replace")


def publish_assets(cfg: dict, version: str, dist, commit=None, dry_run=False, gh=gh_runner, sevenzip=None, log=print) -> str:
    """Publish dist/ (package_release.py with [catalog]) as the GitHub release v<version>, draft first:
    create the draft, upload the 7z, release-manifest.json, feed.json and SHA256SUMS, download them back and check them
    (SHA256SUMS, every launcher rule, $RESURRECTED_VALIDATE_RELEASE), and only then make it public and Latest, which
    moves releases/latest/download/feed.json to it. Any failure leaves the draft and raises PublishFailed (exit 1).
    A release that is already public is never touched: a published release ID never changes."""
    import package_release as pr
    version, dist, repo = version.lstrip("v"), Path(dist), cfg["repos"]["github"]
    tag = pr.release_tag(version)
    if not (dist / pr.CATALOG_MANIFEST).is_file():
        raise PublishFailed(f"no {dist / pr.CATALOG_MANIFEST}: package with [catalog] set (an --incomplete build has none)")
    man = json.loads((dist / pr.CATALOG_MANIFEST).read_bytes())
    archive = str(man.get("archive", {}).get("url", "")).rsplit("/", 1)[-1]
    if man.get("archive", {}).get("url") != pr.asset_url(cfg, version, archive):
        raise PublishFailed(f"archive.url {man.get('archive', {}).get('url')!r} is not an asset of {repo} {tag}")
    if man.get("release_id") != f"{man.get('product_id')}-{version}":
        raise PublishFailed(f"{pr.CATALOG_MANIFEST} is {man.get('release_id')!r}, not version {version}")
    problems = check_assets(dist, archive, sevenzip)
    if problems:
        raise PublishFailed("refusing to publish:\n  " + "\n  ".join(problems[:40]))
    assets = [str(dist / n) for n in (archive, pr.CATALOG_MANIFEST, pr.FEED, "SHA256SUMS")]
    with tempfile.TemporaryDirectory() as tmp:
        body = Path(tmp) / "body.md"
        body.write_text(assets_body(cfg, man, archive), encoding="utf-8")
        # no --prerelease: releases/latest (the launcher's feed URL) skips pre-releases
        create = ["release", "create", tag, "-R", repo, "--draft", "--title", f"{cfg['mod']['name']} {version}",
                  "--notes-file", str(body)] + (["--target", commit] if commit else [])
        upload = ["release", "upload", tag, *assets, "-R", repo, "--clobber"]
        back = Path(tmp) / "back"
        download = ["release", "download", tag, "-R", repo, "-D", str(back),
                    *[x for n in (archive, pr.CATALOG_MANIFEST, pr.FEED, "SHA256SUMS") for x in ("-p", n)]]
        public = ["release", "edit", tag, "-R", repo, "--draft=false", "--latest"]
        if dry_run:
            for c in (create, upload, download, public):
                log("would run: gh " + subprocess.list2cmdline(c))
            log(f"dry run: {dist} passes every check; nothing was sent")
            return ""

        def run(args, what):
            r = gh(args)
            if r.returncode != 0:
                raise PublishFailed(f"gh {what} failed ({r.returncode}): {(r.stdout + r.stderr).strip()[-600:]}\n"
                                    f"{tag} stays a draft (if it was created): run again to reuse it, or delete it")
            return r

        seen = gh(["release", "view", tag, "-R", repo, "--json", "isDraft", "-q", ".isDraft"])
        if seen.returncode == 0 and seen.stdout.strip() != "true":
            raise PublishFailed(f"{repo} already has a public release {tag}: a published release never changes; "
                                "package a new version")
        if seen.returncode == 0:
            log(f"{tag}: reusing the existing draft")
        else:
            run(create, "release create")
            log(f"{tag}: draft created on {repo}")
        run(upload, "release upload")
        log(f"{tag}: uploaded {len(assets)} assets; downloading them back")
        run(download, "release download")
        problems = check_assets(back, archive, sevenzip)
        if not problems and (back / "SHA256SUMS").read_bytes() != (dist / "SHA256SUMS").read_bytes():
            problems = ["the downloaded SHA256SUMS is not the one in dist/"]
        if problems:
            raise PublishFailed(f"the uploaded assets of {tag} are wrong; it stays a draft:\n  " + "\n  ".join(problems[:40]))
        run(public, "release edit --draft=false --latest")
    url = f"https://github.com/{repo}/releases/tag/{tag}"
    log(f"{url} is public and Latest; the feed is https://github.com/{repo}/releases/latest/download/{pr.FEED}")
    return url


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
    a = ap.parse_args(argv)
    if a.assets:
        if a.service != "github":
            print("error: --assets publishes to GitHub only", file=sys.stderr)
            return 1
        try:
            publish_assets(cfg, a.version, a.assets, a.commit, a.dry_run)
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
