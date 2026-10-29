import getpass
import ctypes
import wincred
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
            self.assertEqual(setup.run(self.home, "pro", ["exec", "hello"], "/fake/codex"), 0)
        cmd = call.call_args.args[0]
        self.assertEqual(cmd, ["/fake/codex", "--profile", "deepseek", "--model", "deepseek-v4-pro", "exec", "hello"])
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

    def test_macos_security_uses_only_fixed_system_path(self):
        with mock.patch.object(setup.sys, "platform", "darwin"), mock.patch.object(setup.shutil, "which") as which, mock.patch.object(setup.os.path, "isfile", return_value=True) as isfile, mock.patch.object(setup.os, "access", return_value=True) as access:
            self.assertEqual(setup.macos_security(), "/usr/bin/security")
            which.assert_not_called()
            isfile.assert_called_once_with("/usr/bin/security")
            access.assert_called_once_with("/usr/bin/security", os.X_OK)

    def test_macos_security_reports_missing_or_unexecutable_command(self):
        with mock.patch.object(setup.sys, "platform", "darwin"), mock.patch.object(setup.os.path, "isfile", return_value=False):
            with self.assertRaisesRegex(ValueError, "/usr/bin/security"):
                setup.macos_security()
        with mock.patch.object(setup.sys, "platform", "darwin"), mock.patch.object(setup.os.path, "isfile", return_value=True), mock.patch.object(setup.os, "access", return_value=False):
            with self.assertRaisesRegex(ValueError, "/usr/bin/security"):
                setup.macos_security()

    def test_macos_keychain_save_has_no_password_in_arguments_or_update_flag(self):
        with mock.patch.object(setup.sys, "platform", "darwin"), mock.patch.object(setup.os.path, "isfile", return_value=True), mock.patch.object(setup.os, "access", return_value=True), mock.patch.object(setup.subprocess, "call", return_value=0) as call:
            self.assertEqual(setup.save_keychain(), 0)
        command = call.call_args.args[0]
        self.assertEqual(command[-1], "-w")
        self.assertNotIn("-U", command)
        self.assertEqual(command[1], "add-generic-password")

    def test_keychain_run_inherits_standard_streams(self):
        setup.init_home(self.home)
        result = subprocess.CompletedProcess([], 0, stdout="sk-fake\n")
        def check_child(command, **kwargs):
            self.assertEqual(kwargs["env"]["DEEPSEEK_API_KEY"], "sk-fake")
            self.assertNotIn("stdin", kwargs)
            self.assertNotIn("stdout", kwargs)
            self.assertEqual(command[-2:], ["exec", "-"])
            return 42
        with mock.patch.object(setup.sys, "platform", "darwin"), mock.patch.object(setup.os.path, "isfile", return_value=True), mock.patch.object(setup.os, "access", return_value=True), mock.patch.object(setup.subprocess, "run", return_value=result) as read, mock.patch.object(setup.subprocess, "call", side_effect=check_child):
            self.assertEqual(setup.run(self.home, "flash", ["exec", "-"], "/fake/codex", use_keychain=True), 42)
        self.assertNotIn("sk-fake", read.call_args.args[0])
        self.assertNotIn("sk-fake", (self.home / "deepseek.config.toml").read_text())

    def test_keychain_failure_fails_closed_without_revealing_stderr(self):
        result = subprocess.CompletedProcess([], 1, stdout="", stderr="sensitive sentinel")
        with mock.patch.object(setup.sys, "platform", "darwin"), mock.patch.object(setup.os.path, "isfile", return_value=True), mock.patch.object(setup.os, "access", return_value=True), mock.patch.object(setup.subprocess, "run", return_value=result):
            with self.assertRaises(ValueError) as error:
                setup.read_keychain()
        self.assertNotIn("sensitive sentinel", str(error.exception))

    def test_keychain_unavailable_on_other_platforms(self):
        with mock.patch.object(setup.sys, "platform", "linux"):
            with self.assertRaises(ValueError):
                setup.save_keychain()

    def test_non_hidden_input_is_rejected(self):
        setup.init_home(self.home)
        def cannot_hide(_):
            warnings.warn("input may be echoed", getpass.GetPassWarning)
            return "sk-test"
        with mock.patch.object(setup.getpass, "getpass", side_effect=cannot_hide), mock.patch.object(setup.subprocess, "call") as call:
            with self.assertRaises(ValueError):
                setup.run(self.home, "flash", [], "/fake/codex")
            call.assert_not_called()

    def test_missing_install_or_key_and_child_status(self):
        with self.assertRaises(ValueError):
            setup.run(self.home, "flash", [], "/fake/codex")
        setup.init_home(self.home)
        with mock.patch.object(setup.getpass, "getpass", return_value=""):
            with self.assertRaises(ValueError):
                setup.run(self.home, "flash", [], "/fake/codex")
        with mock.patch.object(setup.getpass, "getpass", return_value="sk-test"), mock.patch.object(setup.subprocess, "call", return_value=23):
            self.assertEqual(setup.run(self.home, "flash", [], "/fake/codex"), 23)

    def test_secret_and_home_reach_child_without_shell_interpolation(self):
        setup.init_home(self.home)
        seen = {}
        def child(command, env):
            seen.update(command=command, key=env["DEEPSEEK_API_KEY"], home=env["CODEX_HOME"])
            return 0
        with mock.patch.object(setup.getpass, "getpass", return_value="sk-test"), mock.patch.object(setup.subprocess, "call", side_effect=child):
            self.assertEqual(setup.run(self.home, "flash", ["exec", "$(echo no)"], "/fake/codex"), 0)
        self.assertEqual(seen["key"], "sk-test")
        self.assertEqual(seen["home"], str(self.home.resolve()))
        self.assertEqual(seen["command"][-1], "$(echo no)")


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
