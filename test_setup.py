import getpass
import io
import json
import ctypes
import wincred
import maccred
import i18n
import shutil
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
import uuid
from unittest import mock
import warnings

SCRIPT = Path(__file__).resolve().parent / "setup.py"
spec = importlib.util.spec_from_file_location("deepseek_setup", SCRIPT)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "isolated"

    def test_create_isolated_profile_and_never_overwrite(self):
        setup.init_home(self.home)
        profile = self.home / "deepseek.config.toml"
        contents = profile.read_text()
        self.assertIn('model = "deepseek-flash"', contents)
        self.assertIn('env_key = "DEEPSEEK_API_KEY"', contents)
        self.assertNotIn("sk-", contents)
        if os.name != "nt":
            self.assertEqual(self.home.stat().st_mode & 0o777, 0o700)
            self.assertEqual(profile.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(FileExistsError):
            setup.init_home(self.home)
        self.assertEqual(profile.read_text(), contents)

    def test_existing_directory_and_symlink_are_untouched(self):
        self.home.mkdir()
        marker = self.home / "keep"
        marker.write_text("untouched")
        with self.assertRaises(FileExistsError):
            setup.init_home(self.home)
        self.assertEqual(marker.read_text(), "untouched")
        symlink = self.root / "link"
        try:
            symlink.symlink_to(self.home, target_is_directory=True)
        except OSError:
            self.skipTest("symlink creation is unavailable")
        with self.assertRaises(FileExistsError):
            setup.init_home(symlink)

    def test_run_passes_key_only_in_child_environment(self):
        setup.init_home(self.home)
        original_key = os.environ.get("DEEPSEEK_API_KEY")
        with mock.patch.object(setup.getpass, "getpass", return_value="sk-test"), mock.patch.object(setup.subprocess, "call", return_value=0) as call:
            self.assertEqual(setup.run(self.home, "pro", ["exec", "hello"], "/fake/codex.exe"), 0)
        cmd = call.call_args.args[0]
        self.assertEqual(cmd[:6], ["/fake/codex.exe", "--profile", "deepseek", "--model", "deepseek-v4-pro", "exec"])
        self.assertEqual(cmd[6], "-c")
        self.assertTrue(cmd[7].startswith("model_catalog_json="))
        self.assertEqual(cmd[-1], "hello")
        self.assertNotIn("sk-test", cmd)
        # env is cleared of the key after the child exits.
        self.assertNotIn("DEEPSEEK_API_KEY", call.call_args.kwargs["env"])
        self.assertNotIn("sk-test", (self.home / "deepseek.config.toml").read_text())
        self.assertEqual(os.environ.get("DEEPSEEK_API_KEY"), original_key)

    def test_find_codex_prefers_path_over_app_bundle(self):
        with mock.patch.object(setup.shutil, "which", return_value="/usr/local/bin/codex"), mock.patch.object(setup.sys, "platform", "darwin"), mock.patch.object(setup.os.path, "isfile") as isfile:
            self.assertEqual(setup.find_codex(), "/usr/local/bin/codex")
            isfile.assert_not_called()

    def test_find_codex_app_fallback_requires_executable_on_macos(self):
        with mock.patch.object(setup.shutil, "which", return_value=None), mock.patch.object(setup.sys, "platform", "darwin"), mock.patch.object(setup.os.path, "isfile", return_value=True), mock.patch.object(setup.os, "access", return_value=True):
            self.assertEqual(setup.find_codex(), setup.CHATGPT_MAC_CODEX)
        with mock.patch.object(setup.shutil, "which", return_value=None), mock.patch.object(setup.sys, "platform", "darwin"), mock.patch.object(setup.os.path, "isfile", return_value=True), mock.patch.object(setup.os, "access", return_value=False):
            self.assertIsNone(setup.find_codex())
        with mock.patch.object(setup.shutil, "which", return_value=None), mock.patch.object(setup.sys, "platform", "linux"), mock.patch.object(setup.os.path, "isfile") as isfile:
            self.assertIsNone(setup.find_codex())
            isfile.assert_not_called()

    def test_windows_prefers_exe_and_never_launches_cmd(self):
        with mock.patch.object(setup.sys, "platform", "win32"), mock.patch.object(setup.shutil, "which", return_value="C:/cli/codex.exe") as which:
            self.assertEqual(setup.find_codex(), "C:/cli/codex.exe")
            which.assert_called_once_with("codex.exe")
        with mock.patch.object(setup.sys, "platform", "win32"), mock.patch.object(setup.shutil, "which", return_value="C:/cli/codex.cmd"), mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(setup.find_codex())

    def test_windows_cmd_only_reports_install_instructions(self):
        setup.init_home(self.home)
        def which(name):
            return "C:/cli/codex.cmd" if name == "codex.cmd" else None
        with mock.patch.object(setup.sys, "platform", "win32"), mock.patch.object(setup.shutil, "which", side_effect=which), mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(setup.subprocess, "call") as child:
            with self.assertRaisesRegex(ValueError, "codex.cmd.*codex.exe.*https://"):
                setup.run(self.home, "flash", [])
            child.assert_not_called()
        with mock.patch.object(setup.sys, "platform", "win32"), mock.patch.object(setup.subprocess, "call") as child:
            with self.assertRaisesRegex(ValueError, "codex.exe"):
                setup.run(self.home, "flash", [], "C:/cli/codex.cmd")
            child.assert_not_called()

    def test_windows_find_cli_from_local_appdata(self):
        with mock.patch.object(setup.sys, "platform", "win32"), mock.patch.object(setup.shutil, "which", return_value=None), mock.patch.dict(os.environ, {"LOCALAPPDATA": "X-local"}), mock.patch.object(setup.glob, "glob", return_value=[]), mock.patch.object(setup.os.path, "isfile", return_value=True), mock.patch.object(setup.os, "access", return_value=True):
            self.assertEqual(setup.find_codex(), os.path.join("X-local", "Programs", "OpenAI", "Codex", "bin", "codex.exe"))

    def test_windows_save_and_launch_with_mock_credential_store(self):
        setup.init_home(self.home)
        seen = {}
        def child(command, env):
            seen.update(command=command, key=env["DEEPSEEK_API_KEY"])
            return 19
        with mock.patch.object(setup.sys, "platform", "win32"), mock.patch.object(setup.getpass, "getpass", return_value="sk-fake"), mock.patch.object(wincred, "save_key") as save:
            self.assertEqual(setup.save_credential(), 0)
            save.assert_called_once_with("sk-fake")
        with mock.patch.object(setup.sys, "platform", "win32"), mock.patch.object(wincred, "read_key", return_value="sk-fake"), mock.patch.object(setup.subprocess, "call", side_effect=child):
            self.assertEqual(setup.run(self.home, "flash", ["exec", "-"], "codex.exe", use_keychain=True), 19)
        self.assertEqual(seen["key"], "sk-fake")
        self.assertNotIn("sk-fake", seen["command"])
        self.assertNotIn("sk-fake", (self.home / "deepseek.config.toml").read_text())

    def test_macos_save_uses_hidden_prompt_and_api(self):
        with mock.patch.object(setup.sys, "platform", "darwin"), mock.patch.object(setup.getpass, "getpass", return_value="fake-key"), mock.patch.object(maccred, "save_key") as save, mock.patch.object(setup.subprocess, "call") as child:
            self.assertEqual(setup.save_keychain(), 0)
            save.assert_called_once_with("fake-key")
            child.assert_not_called()

    def test_keychain_run_inherits_standard_streams(self):
        setup.init_home(self.home)
        def check_child(command, **kwargs):
            self.assertEqual(kwargs["env"]["DEEPSEEK_API_KEY"], "sk-fake")
            self.assertNotIn("stdin", kwargs)
            self.assertNotIn("stdout", kwargs)
            self.assertEqual(command[5], "exec")
            self.assertEqual(command[-1], "-")
            return 42
        with mock.patch.object(setup.sys, "platform", "darwin"), mock.patch.object(maccred, "read_key", return_value="sk-fake"), mock.patch.object(setup.subprocess, "call", side_effect=check_child):
            self.assertEqual(setup.run(self.home, "flash", ["exec", "-"], "/fake/codex.exe", use_keychain=True), 42)
        self.assertNotIn("sk-fake", (self.home / "deepseek.config.toml").read_text())

    def test_macos_keychain_error_does_not_leak_key(self):
        with mock.patch.object(setup.sys, "platform", "darwin"), mock.patch.object(maccred, "read_key", side_effect=ValueError("status 42")):
            with self.assertRaisesRegex(ValueError, "status 42"):
                setup.read_keychain()

    def test_keychain_unavailable_on_other_platforms(self):
        with mock.patch.object(setup.sys, "platform", "linux"):
            with self.assertRaises(ValueError):
                setup.save_keychain()

    def test_mac_fallback_to_codex_app_when_chatgpt_missing(self):
        def isfile(path):
            return path == setup.CODEX_MAC_CODEX
        with mock.patch.object(setup.shutil, "which", return_value=None), mock.patch.object(setup.sys, "platform", "darwin"), mock.patch.object(setup.os.path, "isfile", side_effect=isfile), mock.patch.object(setup.os, "access", return_value=True):
            self.assertEqual(setup.find_codex(), setup.CODEX_MAC_CODEX)

    def test_catalog_covers_models_and_subcommand_configuration(self):
        catalog = json.loads((SCRIPT.parent / "models.json").read_text(encoding="utf-8"))
        models = {entry["slug"]: entry for entry in catalog["models"]}
        self.assertEqual(set(models), set(setup.MODELS.values()))
        for model in models.values():
            self.assertTrue({"high", "max"}.issubset({x["effort"] for x in model["supported_reasoning_levels"]}))
        self.assertIn("image", models["deepseek-flash"]["input_modalities"])
        self.assertNotIn("image", models["deepseek-v4-pro"]["input_modalities"])
        cmd = setup.build_command("codex", "pro", ["exec", "-c", 'foo="bar"', "-"], "max")
        self.assertEqual(cmd[5], "exec")
        self.assertEqual(json.loads(cmd[7].split("=", 1)[1]), str(SCRIPT.parent / "models.json"))
        self.assertEqual(cmd[-5:], ["-c", 'model_reasoning_effort="max"', "-c", 'foo="bar"', "-"])

    def test_reasoning_uses_single_toml_argument_and_preserves_tail(self):
        for effort in ("high", "max"):
            cmd = setup.build_command("codex.exe", "pro", ["exec", "-"], effort)
            self.assertEqual(cmd[5], "exec")
            self.assertEqual(cmd[-3:], ["-c", f'model_reasoning_effort="{effort}"', "-"])
        cmd = setup.build_command("codex", "flash", ["exec", "-"])
        self.assertEqual(cmd[5], "exec")
        self.assertEqual(cmd[-1], "-")

    def test_main_passes_reasoning_and_codex_arguments(self):
        arguments = ["setup.py", "--lang", "en", "--home", str(self.home), "run", "--credential", "--model", "pro", "--reasoning", "max", "--", "exec", "-"]
        with mock.patch.object(setup.sys, "argv", arguments), mock.patch.object(setup, "run", return_value=0) as launch:
            self.assertEqual(setup.main(), 0)
        launch.assert_called_once_with(self.home, "pro", ["exec", "-"], use_keychain=True, reasoning="max")
        i18n.set_language("zh")

    def test_english_interface_and_language_file(self):
        for filename in ("setup.py", "i18n.py", "maccred.py", "wincred.py"):
            shutil.copyfile(SCRIPT.parent / filename, self.root / filename)
        (self.root / "LANGUAGE").write_text("en\n", encoding="utf-8")
        script = str(self.root / "setup.py")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8:strict"
        for args in (["--help"], ["run", "--help"], ["--home", str(self.home), "run", "--credential"], ["--home", str(self.root), "init"]):
            result = subprocess.run([sys.executable, "-B", script, *args], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
            output = (result.stdout + result.stderr).decode("utf-8")
            self.assertNotRegex(output, "[\u4e00-\u9fff]")
        zh = subprocess.run([sys.executable, "-B", script, "--lang", "zh", "--help"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        self.assertIn("独立".encode("utf-8"), zh.stdout)
        en = subprocess.run([sys.executable, "-B", script, "--lang", "en", "--help"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        self.assertIn(b"Separate", en.stdout)

    def test_english_keychain_error_and_key_prompt(self):
        i18n.set_language("en")
        self.addCleanup(i18n.set_language, "zh")
        with mock.patch.object(setup.getpass, "getpass", return_value="fake") as prompt:
            self.assertEqual(setup.prompt_key(), "fake")
            self.assertNotRegex(prompt.call_args.args[0], "[\u4e00-\u9fff]")
        with mock.patch.object(setup.sys, "platform", "darwin"), mock.patch.object(maccred, "read_key", side_effect=ValueError(i18n.tr("未找到钥匙串项目；请先执行 credential-save。"))):
            with self.assertRaises(ValueError) as error:
                setup.read_keychain()
        self.assertNotRegex(str(error.exception), "[\u4e00-\u9fff]")

    def test_argparse_handles_strict_legacy_encoding_in_subprocess(self):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "cp1252:strict"
        for args, expected in ((["--help"], 0), (["invalid-action"], 2)):
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--lang", "zh", *args],
                                        env=env, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, timeout=15)
                self.assertEqual(result.returncode, expected)
                self.assertNotIn(b"UnicodeEncodeError", result.stdout + result.stderr)
                self.assertIn(b"usage:", result.stdout if expected == 0 else result.stderr)
                if expected == 0:
                    self.assertIn(b"\\u", result.stdout)

    def test_legacy_output_encoding_and_password_prompt_do_not_fail(self):
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding="cp1252", errors="strict", write_through=True)
        setup.safe_print("完成: café", file=stream)
        self.assertEqual(buffer.getvalue().replace(b"\r\n", b"\n"), b"\\u5b8c\\u6210: caf\xe9\n")
        with mock.patch.object(setup.sys, "stderr", stream), mock.patch.object(setup.getpass, "getpass", return_value="sk-fake") as prompt:
            self.assertEqual(setup.prompt_key(), "sk-fake")
        self.assertTrue(prompt.call_args.args[0].isascii())
        self.assertNotIn(b"sk-fake", buffer.getvalue())

    def test_utf8_output_retains_chinese(self):
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding="utf-8", errors="strict", write_through=True)
        setup.safe_print("完成", file=stream)
        self.assertEqual(buffer.getvalue().decode("utf-8").replace("\r\n", "\n"), "完成\n")

    def test_non_hidden_input_is_rejected(self):
        setup.init_home(self.home)
        def cannot_hide(_):
            warnings.warn("input may be echoed", getpass.GetPassWarning)
            return "sk-test"
        with mock.patch.object(setup.getpass, "getpass", side_effect=cannot_hide), mock.patch.object(setup.subprocess, "call") as call:
            with self.assertRaises(ValueError):
                setup.run(self.home, "flash", [], "/fake/codex.exe")
            call.assert_not_called()

    def test_missing_install_or_key_and_child_status(self):
        with self.assertRaises(ValueError):
            setup.run(self.home, "flash", [], "/fake/codex.exe")
        setup.init_home(self.home)
        with mock.patch.object(setup.getpass, "getpass", return_value=""):
            with self.assertRaises(ValueError):
                setup.run(self.home, "flash", [], "/fake/codex.exe")
        with mock.patch.object(setup.getpass, "getpass", return_value="sk-test"), mock.patch.object(setup.subprocess, "call", return_value=23):
            self.assertEqual(setup.run(self.home, "flash", [], "/fake/codex.exe"), 23)

    def test_secret_and_home_reach_child_without_shell_interpolation(self):
        setup.init_home(self.home)
        seen = {}
        def child(command, env):
            seen.update(command=command, key=env["DEEPSEEK_API_KEY"], home=env["CODEX_HOME"])
            return 0
        with mock.patch.object(setup.getpass, "getpass", return_value="sk-test"), mock.patch.object(setup.subprocess, "call", side_effect=child):
            self.assertEqual(setup.run(self.home, "flash", ["exec", "$(echo no)"], "/fake/codex.exe"), 0)
        self.assertEqual(seen["key"], "sk-test")
        self.assertEqual(seen["home"], str(self.home.resolve()))
        self.assertEqual(seen["command"][-1], "$(echo no)")



class FakeMacAPI:
    def __init__(self, value="fake", add_status=0, read_status=0, default_status=0):
        self.value = value
        self.add_status = add_status
        self.read_status = read_status
        self.default_status = default_status
        self.freed = 0
        self.released = 0
        self.added = []
        self.buffer = None

    def SecKeychainCopyDefault(self, out):
        if self.default_status == 0:
            ctypes.cast(out, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.c_void_p(123)
        return self.default_status

    def SecKeychainAddGenericPassword(self, chain, slen, service, alen, account, size, secret, item):
        self.added.append((chain.value, service, account, ctypes.string_at(secret, size)))
        return self.add_status

    def SecKeychainFindGenericPassword(self, chain, slen, service, alen, account, size, data, item):
        if self.read_status:
            return self.read_status
        encoded = self.value.encode("utf-8")
        self.buffer = ctypes.create_string_buffer(encoded)
        ctypes.cast(size, ctypes.POINTER(ctypes.c_uint32))[0] = len(encoded)
        ctypes.cast(data, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.cast(self.buffer, ctypes.c_void_p)
        return 0

    def SecKeychainItemFreeContent(self, attributes, data):
        self.freed += 1
        return 0

    def CFRelease(self, reference):
        self.released += 1


class MacCredentialTests(unittest.TestCase):
    def test_save_and_read_fake_api_only(self):
        api = FakeMacAPI(value="fake-key")
        with mock.patch.object(maccred, "_load_api", return_value=(api, api)):
            maccred.save_key("fake-key")
            self.assertEqual(maccred.read_key(), "fake-key")
        self.assertEqual(api.added, [(123, maccred.SERVICE, maccred.ACCOUNT, b"fake-key")])
        self.assertEqual(api.freed, 1)
        self.assertEqual(api.released, 2)

    def test_duplicate_missing_and_auth_errors_fail_closed(self):
        api = FakeMacAPI(add_status=maccred.DUPLICATE_ITEM)
        with mock.patch.object(maccred, "_load_api", return_value=(api, api)), self.assertRaisesRegex(ValueError, "已存在"):
            maccred.save_key("fake-key")
        self.assertEqual(api.released, 1)
        api = FakeMacAPI(read_status=maccred.ITEM_NOT_FOUND)
        with mock.patch.object(maccred, "_load_api", return_value=(api, api)), self.assertRaisesRegex(ValueError, "未找到"):
            maccred.read_key()
        self.assertEqual(api.released, 1)
        api = FakeMacAPI(read_status=-25293)
        with mock.patch.object(maccred, "_load_api", return_value=(api, api)), self.assertRaisesRegex(ValueError, "-25293"):
            maccred.read_key()
        self.assertEqual(api.released, 1)


class FakeWinCredAPI:
    def __init__(self, value=None, read_error=1168, write_ok=True):
        self.value = value
        self.read_error = read_error
        self.write_ok = write_ok
        self.freed = 0
        self.writes = []
        self.keep = None

    def CredReadW(self, target, typ, flags, output):
        if self.value is None:
            return 0
        encoded = self.value.encode("utf-16-le")
        blob = (wincred.BYTE * len(encoded)).from_buffer_copy(encoded)
        credential = wincred.CREDENTIALW()
        credential.CredentialBlobSize = len(encoded)
        credential.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(wincred.BYTE))
        pointer = ctypes.pointer(credential)
        self.keep = (blob, credential, pointer)
        ctypes.cast(output, ctypes.POINTER(wincred.PCREDENTIALW))[0] = pointer
        return 1

    def CredWriteW(self, pointer, flags):
        item = ctypes.cast(pointer, wincred.PCREDENTIALW).contents
        self.writes.append((item.TargetName, item.Type, item.Persist,
                            ctypes.string_at(item.CredentialBlob, item.CredentialBlobSize)))
        return int(self.write_ok)

    def CredFree(self, pointer):
        self.freed += 1


class WindowsCredentialTests(unittest.TestCase):
    def patch_api(self, api):
        return mock.patch.object(wincred, "_load_api", return_value=(api, lambda: api.read_error))

    def test_write_new_credential_with_no_key_in_name(self):
        api = FakeWinCredAPI()
        with self.patch_api(api):
            wincred.save_key("sk-fake")
        self.assertEqual(api.writes, [(wincred.TARGET, 1, 2, "sk-fake".encode("utf-16-le"))])
        self.assertNotIn("sk-fake", api.writes[0][0])

    def test_existing_key_never_overwritten(self):
        api = FakeWinCredAPI(value="sk-existing")
        with self.patch_api(api), self.assertRaisesRegex(ValueError, "已存在"):
            wincred.save_key("sk-new")
        self.assertEqual(api.writes, [])
        self.assertEqual(api.freed, 1)

    def test_read_and_free(self):
        api = FakeWinCredAPI(value="sk-fake")
        with self.patch_api(api):
            self.assertEqual(wincred.read_key(), "sk-fake")
        self.assertEqual(api.freed, 1)

    def test_missing_and_unexpected_error_fail_closed(self):
        missing = FakeWinCredAPI()
        with self.patch_api(missing), self.assertRaisesRegex(ValueError, "未找到"):
            wincred.read_key()
        bad = FakeWinCredAPI(read_error=5)
        with self.patch_api(bad), self.assertRaisesRegex(ValueError, "错误码 5"):
            wincred.save_key("sk-fake")
        self.assertEqual(bad.writes, [])

    def test_write_error_does_not_show_secret(self):
        api = FakeWinCredAPI(write_ok=False, read_error=1168)
        with self.patch_api(api), self.assertRaises(ValueError) as error:
            wincred.save_key("sk-fake")
        self.assertNotIn("sk-fake", str(error.exception))


@unittest.skipUnless(sys.platform == "win32", "Windows Credential Manager integration requires Windows")
class WindowsCredentialIntegrationTests(unittest.TestCase):
    def test_isolated_write_read_and_delete(self):
        # A fresh, unguessable target ensures we never read or modify a user's
        # existing entry. The value is deliberately fake, not an API key.
        target = "codex-deepseek-connect/test/" + uuid.uuid4().hex
        fake_value = "integration-test-only-fake-value"
        api = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        api.CredDeleteW.argtypes = [ctypes.c_wchar_p, wincred.DWORD, wincred.DWORD]
        api.CredDeleteW.restype = ctypes.c_int
        with mock.patch.object(wincred, "TARGET", target):
            created = False
            try:
                wincred.save_key(fake_value)
                created = True
                self.assertEqual(wincred.read_key(), fake_value)
            finally:
                if created and not api.CredDeleteW(target, wincred.CRED_TYPE_GENERIC, 0):
                    error = ctypes.get_last_error()
                    if error != wincred.ERROR_NOT_FOUND:
                        self.fail(f"删除临时测试凭据失败（错误码 {error}）")
            with self.assertRaisesRegex(ValueError, "未找到"):
                wincred.read_key()


if __name__ == "__main__":
    unittest.main()
