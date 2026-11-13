#!/usr/bin/env python3
"""Copies Mozilla's translation models into a release of this repository and writes the list PP Mail reads.

    python3 mirror.py --tag packs-1 --out build          # download, verify, write build/packs.json
    python3 mirror.py --tag packs-1 --list-only          # print the list without downloading

Each file is checked against the SHA-256 Mozilla publishes for it; a file that does not match stops the run.
"""
import argparse
import hashlib
import json
import pathlib
import re
import urllib.request

SERVER = "https://firefox.settings.services.mozilla.com/v1/"
RECORDS = SERVER + "buckets/main/collections/translations-models/records"
REPOSITORY = "prabhatsharma07/ppmail-language-packs"
RELEASE_VERSION = re.compile(r"^\d+(\.\d+)*$")
# Models Mozilla still limits to its nightly or beta browsers are not mirrored.
PRERELEASE_ONLY = re.compile(r"env\.channel == '(default|nightly|beta)'")


def version_key(version):
    return tuple(int(part) for part in version.split("."))


def released(records):
    return all(not PRERELEASE_ONLY.search(record.get("filter_expression") or "") for record in records)


def complete(files):
    has_vocabulary = "vocab" in files or {"srcvocab", "trgvocab"} <= files.keys()
    return "model" in files and "lex" in files and has_vocabulary


def select_packs(records):
    """One pack per direction: the newest released version that has every file the engine needs."""
    by_direction = {}
    for record in records:
        direction = (record["fromLang"], record["toLang"])
        by_direction.setdefault(direction, {}).setdefault(record["version"], []).append(record)
    packs = []
    for (source, target), versions in sorted(by_direction.items()):
        usable = [
            version
            for version, version_records in versions.items()
            if RELEASE_VERSION.match(version)
            and released(version_records)
            and complete({record["fileType"]: record for record in version_records})
        ]
        if not usable:
            continue
        version = max(usable, key=version_key)
        files = sorted(versions[version], key=lambda record: record["fileType"])
        packs.append({"from": source, "to": target, "version": version, "records": files})
    return packs


def asset_name(pack, record):
    """Simplified and traditional Chinese share Mozilla's file names, so each file carries its direction."""
    return f"{pack['from']}-{pack['to']}.{record['attachment']['filename']}"


def manifest(packs, tag):
    base_url = f"https://github.com/{REPOSITORY}/releases/download/{tag}/"
    return {
        "release": tag,
        "baseUrl": base_url,
        "packs": [
            {
                "from": pack["from"],
                "to": pack["to"],
                "version": pack["version"],
                "files": [
                    {
                        "type": record["fileType"],
                        "name": asset_name(pack, record),
                        "size": record["attachment"]["size"],
                        "sha256": record["attachment"]["hash"],
                    }
                    for record in pack["records"]
                ],
            }
            for pack in packs
        ],
    }


def read_json(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def download(url, destination, expected_sha256):
    digest = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=600) as response, open(destination, "wb") as out:
        while chunk := response.read(1 << 20):
            digest.update(chunk)
            out.write(chunk)
    if digest.hexdigest() != expected_sha256:
        destination.unlink()
        raise ValueError(f"{destination.name}: SHA-256 does not match the one Mozilla publishes")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", required=True, help="the release the files belong to, e.g. packs-1")
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("build"), help="directory for the files")
    parser.add_argument("--list-only", action="store_true", help="write packs.json without downloading")
    parser.add_argument("--skip", type=pathlib.Path, help="file with the names already in the release, one a line")
    args = parser.parse_args()

    packs = select_packs(read_json(RECORDS)["data"])
    names = [asset_name(pack, record) for pack in packs for record in pack["records"]]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "packs.json").write_text(json.dumps(manifest(packs, args.tag), indent=1) + "\n")
    total = sum(record["attachment"]["size"] for pack in packs for record in pack["records"])
    print(f"{len(packs)} packs, {len(names)} files, {total / 1e9:.2f} GB")
    if args.list_only:
        return

    already = set(args.skip.read_text().split()) if args.skip and args.skip.exists() else set()
    base_url = read_json(SERVER)["capabilities"]["attachments"]["base_url"]
    for pack in packs:
        for record in pack["records"]:
            attachment = record["attachment"]
            name = asset_name(pack, record)
            if name in already:
                continue
            download(base_url + attachment["location"], args.out / name, attachment["hash"])
            print(f"{name}  {attachment['size'] / 1e6:.1f} MB  SHA-256 ok", flush=True)


if __name__ == "__main__":
    main()
