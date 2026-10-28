import json
import os
from pathlib import Path
import tempfile
import unittest
import importlib
from unittest.mock import patch

from backend.library import ManifestError, discover, launch, parse_vdf
from backend.processes import identify, snapshot, terminate
from backend.__main__ import atomic_write, note_path


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.root = self.home / ".local/share/Steam"
        self.apps = self.root / "steamapps"
        self.apps.mkdir(parents=True)

    def manifest(self, apps=None, appid="42", directory="A Game", flags="4", name="A Game"):
        apps = apps or self.apps
        apps.mkdir(parents=True, exist_ok=True)
        (apps / f"appmanifest_{appid}.acf").write_text(
            '"AppState" ' + json.dumps({"appid": appid, "name": name,
                "installdir": directory, "StateFlags": flags}).replace(":", " ").replace(",", "\n"))
        (apps / "common" / directory).mkdir(parents=True, exist_ok=True)

    def scan(self, **kwargs):
        return discover(self.home, check_sober=False, **kwargs)

    def test_nested_comments_escapes_and_quoted_braces(self):
        self.assertEqual(parse_vdf('// comment\n"a" { "name" "}" "quote" "a\\\"b" }'),
                         {"a": {"name": "}", "quote": 'a"b'}})

    def test_malformed_vdf(self):
        for content in ('"a" {', '}', '"a"', '"a" }', '"unterminated'):
            with self.subTest(content=content), self.assertRaises(ManifestError):
                parse_vdf(content)

    def test_empty_home(self):
        self.assertEqual(self.scan()["games"], [])

    def test_native_manifest(self):
        self.manifest()
        game = self.scan()["games"][0]
        self.assertEqual(game["id"], "steam:42")
        self.assertTrue(game["install_path"].endswith("common/A Game"))

    def test_multiple_libraries_modern_and_legacy(self):
        other, legacy = self.home / "disk two", self.home / "old disk"
        self.manifest(other / "steamapps", "43")
        self.manifest(legacy / "steamapps", "44")
        (self.apps / "libraryfolders.vdf").write_text(
            f'"libraryfolders" {{ "0" {{ "path" "{self.root}" }} "1" {{ "path" "{other}" }} "2" "{legacy}" }}')
        self.assertEqual(len(self.scan()["games"]), 2)

    def test_flatpak(self):
        apps = self.home / ".var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps"
        self.manifest(apps)
        self.assertEqual(len(self.scan()["games"]), 1)

    def test_symlink_deduplication(self):
        (self.home / ".steam").mkdir()
        (self.home / ".steam/steam").symlink_to(self.root)
        self.manifest()
        self.assertEqual(len(self.scan()["games"]), 1)

    def test_corrupt_manifest_does_not_hide_good_game(self):
        self.manifest()
        (self.apps / "appmanifest_99.acf").write_text('"AppState" {')
        result = self.scan()
        self.assertEqual(len(result["games"]), 1)
        self.assertEqual(len(result["warnings"]), 1)

    def test_incomplete_or_missing_installation(self):
        self.manifest(flags="2")
        self.assertEqual(self.scan()["games"], [])
        self.assertTrue(self.scan()["warnings"])

    def test_path_traversal_rejected(self):
        self.manifest(directory="../../outside")
        self.assertEqual(self.scan()["games"], [])
        self.assertIn("escapes", self.scan()["warnings"][0])

    def test_manifest_id_mismatch(self):
        self.manifest()
        (self.apps / "appmanifest_42.acf").rename(self.apps / "appmanifest_43.acf")
        self.assertEqual(self.scan()["games"], [])

    def test_unavailable_extra_library_is_reported(self):
        self.assertIn("unavailable", self.scan(extra_libraries=[self.home / "gone"])["warnings"][0])

    @patch("backend.library.subprocess.Popen")
    @patch("backend.library.shutil.which", return_value="/usr/bin/steam")
    def test_launch_uses_validated_argv_not_metadata(self, which, popen):
        popen.return_value.pid = 123
        launch({"kind": "steam", "appid": "42", "name": '$(touch /tmp/unsafe)'})
        self.assertEqual(popen.call_args.args[0], ["steam", "steam://rungameid/42"])
        self.assertNotIn("shell", popen.call_args.kwargs)

    def test_invalid_launch_id(self):
        with self.assertRaises(ValueError):
            launch({"kind": "steam", "appid": "42;kill"})

    @patch("backend.library.shutil.which", return_value="flatpak")
    @patch("backend.library.subprocess.run")
    def test_sober_only_when_installed(self, run, which):
        run.return_value.returncode = 0
        self.assertEqual(discover(self.home)["games"][0]["id"], "sober")
        run.return_value.returncode = 1
        self.assertEqual(discover(self.home)["games"], [])


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.games = [{"id": "steam:42", "kind": "steam", "appid": "42", "install_path": "/games/Example"},
                      {"id": "sober", "kind": "sober"}]
        self.process = {"pid": 12345, "uid": os.getuid(), "exe": "/games/Example/game",
                        "argv": ["/games/Example/game"], "environment": {"SteamAppId": "42"}, "token": "identity"}

    def test_native_game(self):
        self.assertEqual(identify(self.process, self.games)["game_id"], "steam:42")

    def test_unknown_id_or_other_user(self):
        self.process["environment"] = {"SteamAppId": "99"}
        self.assertIsNone(identify(self.process, self.games))
        self.process["environment"] = {"SteamAppId": "42"}
        self.process["uid"] += 1
        self.assertIsNone(identify(self.process, self.games))

    def test_protected_processes_and_unrelated_app(self):
        for executable in ("Hyprland", "qs", "caelestia", "steam", "steamwebhelper", "wineserver", "services.exe"):
            self.process.update(exe=f"/games/Example/{executable}", argv=[executable])
            self.assertIsNone(identify(self.process, self.games), executable)
        self.process.update(exe="/usr/bin/vesktop", argv=["vesktop"])
        self.assertIsNone(identify(self.process, self.games))

    def test_proton_requires_game_path(self):
        self.process.update(exe="/steam/proton/bin/wine64-preloader", argv=["wine64-preloader", "/games/Example/game.exe"])
        self.assertIsNotNone(identify(self.process, self.games))
        self.process["argv"] = ["wine64-preloader", "/other/game.exe"]
        self.assertIsNone(identify(self.process, self.games))

    def test_sober_requires_matching_flatpak_and_executable(self):
        self.process.update(exe="/app/bin/sober", argv=["sober"], environment={"FLATPAK_ID": "org.vinegarhq.Sober"})
        self.assertEqual(identify(self.process, self.games)["game_id"], "sober")
        self.process["exe"] = "/usr/bin/something-else"
        self.assertIsNone(identify(self.process, self.games))

    def test_proc_stat_with_parentheses_and_identity_change(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            base = proc / "12345"
            base.mkdir()
            fields = ["S"] + ["0"] * 23
            fields[19] = "100"
            (base / "stat").write_text("12345 (game ) name) " + " ".join(fields))
            (base / "exe").symlink_to("/games/Example/game")
            (base / "cmdline").write_bytes(b"game\0")
            (base / "environ").write_bytes(b"SteamAppId=42\0PRIVATE_SECRET=never-return-this\0")
            before = snapshot(12345, proc)
            fields[19] = "101"
            (base / "stat").write_text("12345 (game ) name) " + " ".join(fields))
            after = snapshot(12345, proc)
            self.assertNotEqual(before["token"], after["token"])
            self.assertNotIn("PRIVATE_SECRET", before["environment"])

    @patch("backend.processes.os.close")
    @patch("backend.processes.signal.pidfd_send_signal", create=True)
    @patch("backend.processes.os.pidfd_open", return_value=88, create=True)
    @patch("backend.processes.snapshot")
    def test_changed_identity_never_signalled(self, read, open_fd, send, close):
        read.return_value = self.process
        with self.assertRaises(ValueError):
            terminate(12345, "old-identity", self.games)
        send.assert_not_called()
        close.assert_called_once_with(88)

    @patch("backend.processes.os.close")
    @patch("backend.processes.signal.pidfd_send_signal", create=True)
    @patch("backend.processes.os.pidfd_open", return_value=88, create=True)
    @patch("backend.processes.snapshot")
    def test_exact_pidfd_only(self, read, open_fd, send, close):
        import signal
        read.return_value = self.process
        terminate(12345, "identity", self.games)
        open_fd.assert_called_once_with(12345)
        send.assert_called_once_with(88, signal.SIGTERM)


class NotesTests(unittest.TestCase):
    def test_note_ids_and_atomic_write(self):
        with self.assertRaises(ValueError):
            note_path("../../escape")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "note.txt"
            atomic_write(path, "my notes")
            atomic_write(path, "updated notes")
            self.assertEqual(path.read_text(), "updated notes")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)


class TerminationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module("backend.__main__")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.token = "a" * 64

    def invoke(self, force=False):
        argv = ["backend", "terminate", "12345", "--confirm", self.token]
        if force:
            argv.append("--force")
        from contextlib import redirect_stdout
        from io import StringIO
        with patch("sys.argv", argv), patch.object(self.module, "data_directory", return_value=Path(self.temp.name)), \
             patch.object(self.module, "discover", return_value={"games": []}), \
             patch.dict(os.environ, {"XDG_CONFIG_HOME": self.temp.name}), redirect_stdout(StringIO()) as output:
            code = self.module.main()
        return code, json.loads(output.getvalue())

    @patch("backend.__main__.terminate")
    def test_force_requires_prior_graceful_request(self, send):
        code, result = self.invoke(force=True)
        self.assertEqual(code, 1)
        self.assertIn("graceful", result["error"])
        send.assert_not_called()

    @patch("backend.__main__.time.monotonic")
    @patch("backend.__main__.terminate")
    def test_force_requires_wait_and_separate_request(self, send, clock):
        clock.return_value = 100
        self.assertEqual(self.invoke()[0], 0)
        send.reset_mock()
        clock.return_value = 102
        self.assertEqual(self.invoke(force=True)[0], 1)
        send.assert_not_called()
        clock.return_value = 106
        self.assertEqual(self.invoke(force=True)[0], 0)
        self.assertTrue(send.call_args.args[3])

    @patch("backend.__main__.terminate", side_effect=ValueError("identity changed"))
    def test_failed_graceful_request_leaves_no_force_receipt(self, send):
        self.assertEqual(self.invoke()[0], 1)
        self.assertFalse(list(Path(self.temp.name).glob("termination-*")))


if __name__ == "__main__":
    unittest.main()
