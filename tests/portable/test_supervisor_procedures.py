"""Reviewed procedure registry: fixed names, typed arguments, no arbitrary execution."""

from pathlib import Path
import sys
import unittest

from deskmate_formats.supervisor import procedures

RESOURCE_NAMES = {"source-read", "portable-tests", "synthetic-fixtures"}
EXECUTION_CLASSES = {"fixed-script", "reviewed-repository-code",
                     "third-party-tool-over-repository-data"}
NETWORK_CLASSES = {"none", "no-isolation"}


class ProcedureTests(unittest.TestCase):
    def test_catalog_is_sorted_and_documents_reviewed_requirements(self):
        names = procedures.names()
        self.assertEqual(names, tuple(sorted(names)))
        self.assertIn("hash-files", names)
        for entry in procedures.catalog():
            with self.subTest(procedure=entry["name"]):
                # The descriptor is the reviewer's interface: every key that
                # describes what will run, and no key that does not.
                self.assertEqual(set(entry), {"name", "summary", "resources",
                                              "timeout_seconds", "arguments",
                                              "executes", "inputs", "modules",
                                              "network", "limits"})
                self.assertTrue(set(entry["resources"]) <= RESOURCE_NAMES)
                self.assertTrue(entry["resources"])
                self.assertGreater(entry["timeout_seconds"], 0)
                self.assertIn(entry["executes"], EXECUTION_CLASSES)
                self.assertIn(entry["network"], NETWORK_CLASSES)
                for key in ("inputs", "modules"):
                    self.assertIsInstance(entry[key], list)
                    self.assertTrue(all(type(item) is str and item for item in entry[key]))
                self.assertEqual(set(entry["limits"]),
                                 {"file_bytes", "total_bytes", "paths"})
                self.assertEqual(entry["limits"]["file_bytes"], procedures.MAX_FILE_BYTES)
                self.assertEqual(entry["limits"]["total_bytes"], procedures.MAX_TOTAL_BYTES)

    def test_unknown_names_and_unexpected_arguments_are_refused(self):
        for name in ("shell", "../x", "Hash-Files", "portable-test", "", None, 1):
            with self.subTest(name=name), self.assertRaises(procedures.ProcedureError):
                procedures.get(name)
        with self.assertRaises(procedures.ProcedureError):
            procedures.validate("repository-audit", {"command": "echo pwned"})
        with self.assertRaises(procedures.ProcedureError):
            procedures.validate("hash-files", {})
        with self.assertRaises(procedures.ProcedureError):
            procedures.validate("portable-tests", {"scope": "all", "pattern": "x"})

    def test_arguments_reject_traversal_absolute_devices_and_duplicates(self):
        for path in ("../x", "/etc/passwd", "C:/x", "a/../../b", "con", "a.",
                     "dir//x", "a\\b", "", "a" * 241):
            with self.subTest(path=path), self.assertRaises(procedures.ProcedureError):
                procedures.validate("hash-files", {"paths": [path]})
        for value in ({"scope": "everything"}, {"scope": 1}, {}, {"paths": []}):
            with self.subTest(value=value), self.assertRaises(procedures.ProcedureError):
                procedures.validate("portable-tests", value)
        with self.assertRaises(procedures.ProcedureError):
            procedures.validate("hash-files", {"paths": ["a", "a"]})
        with self.assertRaises(procedures.ProcedureError):
            procedures.validate("fixture-compare", {"expected": "a"})

    def test_argument_vectors_are_assembled_from_reviewed_constants(self):
        argv = procedures.build("hash-files", {"paths": ["README.md", "AGENTS.md"]},
                                artifacts=Path("artifacts"), working_directory=Path("."))
        self.assertEqual(argv[0], str(Path(sys.executable).resolve()))
        self.assertEqual(argv[1:4], ["-I", "-c", procedures.HASH_SCRIPT])
        # The reviewed caps travel in the argument vector, so the limits that
        # appear in the plan are the limits the script actually applies.
        self.assertEqual(argv[4:6], [str(procedures.MAX_FILE_BYTES),
                                     str(procedures.MAX_TOTAL_BYTES)])
        self.assertEqual(argv[6:], ["README.md", "AGENTS.md"])

        audit = procedures.build("repository-audit", {}, artifacts=Path("a"),
                                 working_directory=Path("."))
        self.assertEqual(audit[1:], ["-I", "-c", procedures.AUDIT_SCRIPT])

        tests = procedures.build("portable-tests", {"scope": "supervisor"},
                                 artifacts=Path("a"), working_directory=Path("."))
        self.assertEqual(tests[1:], ["-m", "unittest", "discover", "-s", "tests/portable",
                                     "-v", "-p", "test_supervisor*.py"])

        compare = procedures.build("fixture-compare", {"expected": "a", "actual": "b"},
                                   artifacts=Path("a"), working_directory=Path("."))
        self.assertEqual(compare[1:4], ["-I", "-c", procedures.COMPARE_SCRIPT])
        self.assertEqual(compare[4:6], [str(procedures.MAX_FILE_BYTES),
                                        str(procedures.MAX_TOTAL_BYTES)])
        self.assertEqual(compare[6:], ["a", "b"])

        package = procedures.build("package-build", {}, artifacts=Path("out/artifacts"),
                                   working_directory=Path("."))
        self.assertEqual(package[1:4], ["-m", "build", "--wheel"])
        # Isolation builds a fresh environment from an index; the reviewed
        # build must use the installed toolchain instead.
        self.assertEqual(package[4], "--no-isolation")
        self.assertEqual(package[5], "--outdir")
        self.assertEqual(package[6].replace("\\", "/"), "out/artifacts")

    def test_procedure_resources_match_their_task_declarations(self):
        self.assertEqual(procedures.resources("portable-tests"), ("portable-tests",))
        self.assertEqual(procedures.resources("hash-files"), ("source-read",))
        self.assertEqual(procedures.resources("package-build"), ("portable-tests",))
