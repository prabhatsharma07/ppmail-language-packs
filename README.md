# PP Mail language packs

The translation models [PP Mail](https://github.com/prabhatsharma07/ppmail) downloads when a user adds a language
under Settings › Translation. PP Mail translates on the phone; these files are all it fetches, and fetching one sends
no email content anywhere.

## What is here

- **Releases** hold the packs. Each release (`packs-1`, `packs-2`, …) is a fixed set: one pack per translation
  direction, with `packs.json` listing every file, its size and its SHA-256. PP Mail ships that list and checks each
  downloaded file against it.
- `mirror.py` builds a release: it reads Mozilla's published list, takes the newest released model of each direction,
  downloads its files, checks each against the SHA-256 Mozilla publishes and writes `packs.json`.
- `.github/workflows/mirror.yml` runs it and uploads the files. It runs when `RELEASE` changes.

## A new set of packs

Change the name in `RELEASE` (for example to `packs-2`) and push. The workflow creates the release and fills it. Then
copy that release's `packs.json` into PP Mail, which is what makes the app offer the new set. An existing release is
never changed, so an installed app always finds the files its list names.

## Where the models come from

They are the models Mozilla trains for Firefox Translations (<https://github.com/mozilla/translations>), copied
unchanged. Every pack translates into or out of English; PP Mail reaches other pairs in two passes.

## Licence

The models are Mozilla's and are under the Mozilla Public License 2.0 (`LICENSE`), as is this repository.
