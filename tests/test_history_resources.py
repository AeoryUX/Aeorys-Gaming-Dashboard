from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backend.history import cached_history
from backend.resources import parse_gpu_csv, parse_pmon, cpu_temperatures, classify_window_activity, number
from backend.resources import resource_context


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.games = [{"id": f"steam:{i}", "appid": str(i), "kind": "steam", "name": f"Game {i}"} for i in range(1, 8)]

    def cache(self, user="123", flatpak=False, content=None):
        base = ".var/app/com.valvesoftware.Steam/.local/share/Steam" if flatpak else ".local/share/Steam"
        path = self.home / base / "userdata" / user / "config/localconfig.vdf"
        path.parent.mkdir(parents=True, exist_ok=True)
        if content is None:
            apps = " ".join(f'"{i}" {{ "Playtime" "{i * 60}" "LastPlayed" "{1000 + i}" }}' for i in range(1, 8))
            content = '"UserLocalConfigStore" { "Software" { "Valve" { "Steam" { "apps" { ' + apps + ' } } } } }'
        path.write_text(content)
        return path

    def test_missing_data_is_empty_not_zero_hours(self):
        result = cached_history(self.games, self.home)
        self.assertEqual(result["most_played"], [])
        self.assertEqual(result["continue_playing"], [])

    def test_sorting_and_limits(self):
        self.cache()
        result = cached_history(self.games, self.home)
        self.assertEqual([g["appid"] for g in result["continue_playing"]], ["7", "6", "5"])
        self.assertEqual([g["appid"] for g in result["most_played"]], ["7", "6", "5", "4", "3"])
        self.assertEqual(result["most_played"][0]["playtime_minutes"], 420)
        self.assertIn("Steam-reported", result["source"])

    def test_accounts_never_silently_merged(self):
        self.cache("123")
        self.cache("456")
        result = cached_history(self.games, self.home)
        self.assertEqual(result["most_played"], [])
        self.assertIn("Multiple Steam accounts", result["status"])
        self.assertEqual(len(cached_history(self.games, self.home, "456")["continue_playing"]), 3)

    def test_flatpak_cache(self):
        self.cache(flatpak=True)
        self.assertEqual(len(cached_history(self.games, self.home)["most_played"]), 5)

    def test_corrupt_cache_returns_warning(self):
        self.cache(content='"broken" {')
        result = cached_history(self.games, self.home)
        self.assertEqual(result["most_played"], [])
        self.assertTrue(result["warnings"])

    def test_absent_and_invalid_values_not_fabricated(self):
        self.cache(content='"UserLocalConfigStore" { "software" { "valve" { "steam" { "Apps" { "1" { "Playtime" "N/A" "LastPlayed" "-1" } "2" { "Playtime" "60" } } } } } }')
        result = cached_history(self.games, self.home)
        self.assertEqual(result["continue_playing"], [])
        self.assertEqual([g["appid"] for g in result["most_played"]], ["2"])

    def test_not_installed_entries_omitted(self):
        self.cache()
        self.assertEqual(cached_history([], self.home)["most_played"], [])

    def test_invalid_account_rejected(self):
        with self.assertRaises(ValueError):
            cached_history(self.games, self.home, "../other")

    def test_same_account_cache_not_summed_across_clients(self):
        self.cache()
        self.cache(flatpak=True)
        self.assertEqual(cached_history(self.games, self.home)["most_played"][0]["playtime_minutes"], 420)


class ResourceTests(unittest.TestCase):
    def test_gpu_scope_and_unsupported_values(self):
        result = parse_gpu_csv("0, NVIDIA GTX 1660 SUPER, 40, 1000, 6144, 65\n1, Other, [N/A], [N/A], 1000, [N/A]\n")
        self.assertEqual(result[0]["utilization_percent"], 40)
        self.assertIn("GPU-wide", result[0]["scope"])
        self.assertIsNone(result[1]["temperature_c"])

    def test_pmon_fields_and_nulls(self):
        result = parse_pmon("# gpu pid type sm mem enc dec fb bar1 command\n# Idx # C/G % % % % MB MB name\n0 123 G 30 - - - 512 - game\n0 456 G - - - - - - game2\n")
        self.assertEqual(result[0]["gpu_percent"], 30)
        self.assertEqual(result[0]["vram_mib"], 512)
        self.assertIsNone(result[1]["gpu_percent"])
        self.assertEqual(parse_pmon("Not supported"), [])
        self.assertEqual(parse_pmon("# gpu pid type sm mem command\n0 - - - - -"), [])

    def test_temperature_context(self):
        with tempfile.TemporaryDirectory() as directory:
            device = Path(directory) / "hwmon0"
            device.mkdir()
            (device / "name").write_text("coretemp")
            (device / "temp1_label").write_text("Package id 0")
            (device / "temp1_input").write_text("65000")
            values = cpu_temperatures(Path(directory))
            self.assertEqual(values[0]["celsius"], 65)
            self.assertEqual(values[0]["scope"], "system context")

    def test_foreground_background_only_exact_pid_matches(self):
        clients = [{"pid": 42}, {"pid": 43}]
        self.assertEqual(classify_window_activity(42, {"pid": 42}, clients), "foreground")
        self.assertEqual(classify_window_activity(43, {"pid": 42}, clients), "background")
        self.assertEqual(classify_window_activity(44, {"pid": 42}, clients), "unknown")
        self.assertEqual(classify_window_activity(43, {}, clients), "unknown")

    def test_invalid_metrics_stay_unavailable(self):
        for text in ("N/A", "-", "nan", "inf", "-1", "invalid"):
            self.assertIsNone(number(text))

    @patch("backend.resources.shutil.which", return_value=None)
    @patch("backend.resources.cpu_temperatures", return_value=[])
    def test_missing_hardware_tools_are_explicit(self, temperatures, which):
        result = resource_context([])
        self.assertEqual(result["gpus"], [])
        self.assertIn("unavailable", result["per_process_status"])


if __name__ == "__main__":
    unittest.main()
