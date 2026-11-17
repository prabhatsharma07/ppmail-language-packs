import unittest

import mirror


def record(source, target, version, file_type, sha256, name=None, expression=None):
    return {
        "fromLang": source,
        "toLang": target,
        "version": version,
        "fileType": file_type,
        "filter_expression": expression,
        "attachment": {
            "filename": name or f"{file_type}.{source}{target}.bin",
            "location": f"main/{sha256}.bin",
            "size": 10,
            "hash": sha256,
        },
    }


def pack(source, target, version, prefix, expression=None, types=("lex", "model", "vocab")):
    return [record(source, target, version, kind, f"{prefix}-{kind}", expression=expression) for kind in types]


class SelectPacksTest(unittest.TestCase):
    def test_the_newest_released_complete_version_of_each_direction(self):
        records = (
            pack("de", "en", "1.0", "old")
            + pack("de", "en", "1.10", "new")
            + pack("de", "en", "2.0", "nightly", expression="env.channel == 'nightly'")
            + pack("de", "en", "3.0", "partial", types=("lex", "model"))
            + pack("de", "en", "2.0a1", "alpha")
        )

        (chosen,) = mirror.select_packs(records)

        self.assertEqual(("de", "en", "1.10"), (chosen["from"], chosen["to"], chosen["version"]))
        self.assertEqual(["new-lex", "new-model", "new-vocab"], [r["attachment"]["hash"] for r in chosen["records"]])

    def test_two_vocabularies_make_a_pack_complete_and_a_direction_without_one_is_left_out(self):
        records = pack("en", "ja", "1.0", "split", types=("lex", "model", "srcvocab", "trgvocab")) + pack(
            "en", "ko", "1.0", "bare", types=("lex", "model")
        )

        self.assertEqual([("en", "ja")], [(p["from"], p["to"]) for p in mirror.select_packs(records)])

    def test_a_file_carries_its_direction_in_its_name(self):
        records = pack("zh", "en", "1.0", "s") + pack("zh-Hant", "en", "1.0", "t")
        names = [name for name, _, _ in mirror.downloads(mirror.select_packs(records))]

        self.assertEqual(len(names), len(set(names)))
        self.assertIn("zh-en.model.zhen.bin", names)


class PublishedReleaseTest(unittest.TestCase):
    def published(self, records):
        return mirror.manifest(mirror.select_packs(records), "packs-1")

    def test_the_list_names_each_file_with_the_hash_mozilla_publishes(self):
        listed = self.published(pack("de", "en", "1.0", "a"))

        self.assertEqual("https://github.com/prabhatsharma07/ppmail-language-packs/releases/download/packs-1/", listed["baseUrl"])
        self.assertEqual(
            {"type": "model", "name": "de-en.model.deen.bin", "size": 10, "sha256": "a-model"},
            listed["packs"][0]["files"][1],
        )

    def test_a_newer_model_at_mozilla_does_not_change_what_a_published_release_gets(self):
        first = pack("de", "en", "1.0", "a")
        listed = self.published(first)
        newer = pack("de", "en", "2.0", "b")

        wanted = mirror.published_downloads(listed, first + newer)

        self.assertEqual({"a-lex", "a-model", "a-vocab"}, {sha256 for _, _, sha256 in wanted})
        self.assertEqual({"main/a-lex.bin", "main/a-model.bin", "main/a-vocab.bin"}, {where for _, where, _ in wanted})

    def test_a_listed_file_mozilla_dropped_stops_the_run(self):
        listed = self.published(pack("de", "en", "1.0", "a"))

        with self.assertRaisesRegex(ValueError, "de-en.model.deen.bin"):
            mirror.published_downloads(listed, pack("de", "en", "2.0", "b"))


if __name__ == "__main__":
    unittest.main()
