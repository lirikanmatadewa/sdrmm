import runpy
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

MEDIA = runpy.run_path(str(Path(__file__).with_name("build-media.py")))


class FdkToolchainTests(unittest.TestCase):
    def setUp(self):
        tool_patch = patch.dict(
            MEDIA["fdk_toolchain"].__globals__,
            tool=lambda name, env: f"C:/tools/{name}.exe",
        )
        tool_patch.start()
        self.addCleanup(tool_patch.stop)

    def test_windows_uses_msvc_linker(self):
        for arch in ("x86_64", "aarch64"):
            with self.subTest(arch=arch):
                args = MEDIA["fdk_toolchain"](f"{arch}-pc-windows-msvc", {})
                self.assertIn("-DCMAKE_LINKER=C:/tools/lld-link.exe", args)
                self.assertIn("-DCMAKE_AR=C:/tools/lib.exe", args)

    def test_non_windows_does_not_force_msvc_linker(self):
        for target in ("aarch64-apple-darwin", "x86_64-unknown-linux-gnu"):
            with self.subTest(target=target):
                args = MEDIA["fdk_toolchain"](target, {})
                self.assertFalse(any(arg.startswith("-DCMAKE_LINKER=") for arg in args))
                self.assertFalse(any(arg.startswith("-DCMAKE_AR=") for arg in args))

    def test_windows_configure_overrides_cached_linker(self):
        build_fdk = MEDIA["build_fdk"]
        with patch.dict(build_fdk.__globals__, run=Mock()):
            build_fdk(
                Path("work/source"),
                Path("work/prefix"),
                "x86_64-pc-windows-msvc",
                {},
            )
            configure_args = build_fdk.__globals__["run"].call_args_list[0].args[0]
        self.assertIn("-DCMAKE_LINKER=C:/tools/lld-link.exe", configure_args)
        self.assertIn("-DCMAKE_AR=C:/tools/lib.exe", configure_args)
        self.assertIn("--fresh", configure_args)


class MediaShellTests(unittest.TestCase):
    def test_make_uses_relative_source_paths(self):
        make_command = MEDIA["make_command"]
        with (
            patch.dict(make_command.__globals__, tool=lambda name, env: name),
            patch("platform.system", return_value="Linux"),
        ):
            args = make_command(Path("work/ffmpeg-9.0.2"), {})
        self.assertEqual(
            args,
            [
                "make",
                "SHELL=sh",
                "-f",
                "work/ffmpeg-9.0.2/Makefile",
                "SRC_PATH=ffmpeg-9.0.2",
                "SRC_LINK=ffmpeg-9.0.2",
            ],
        )

    def test_windows_uses_msys_make(self):
        make_command = MEDIA["make_command"]
        with (
            patch("platform.system", return_value="Windows"),
            patch.dict(
                make_command.__globals__,
                tool=lambda name, env: name,
                prepare_msys_make=Mock(return_value="msys/make.exe"),
            ),
        ):
            args = make_command(Path("work/source"), {})
        self.assertEqual(args[0], "msys/make.exe")

    def test_windows_uses_native_shell_directory(self):
        shell_env = MEDIA["shell_env"]
        with (
            patch.dict("os.environ", {"PATH": "tools"}, clear=True),
            patch("platform.system", return_value="Windows"),
            patch("shutil.which", return_value="C:/Git/usr/bin/sh.exe"),
        ):
            env = shell_env()
        self.assertEqual(
            Path(env["PATH"].split(MEDIA["os"].pathsep)[0]), Path("C:/Git/usr/bin")
        )

    def test_explicit_shell_directory_is_preserved(self):
        with patch.dict("os.environ", {"MEDIA_SHELL_BIN": "custom", "PATH": "tools"}):
            env = MEDIA["shell_env"]()
        self.assertEqual(env["PATH"].split(MEDIA["os"].pathsep)[0], "custom")

    def test_only_msys_shells_are_accepted(self):
        require_shell = MEDIA["require_msys_shell"]
        for kernel in ("MINGW64_NT-10.0", "MSYS_NT-10.0", "Linux", "CYGWIN_NT-10.0"):
            with (
                self.subTest(kernel=kernel),
                patch.dict(require_shell.__globals__, tool=lambda *args: "bash"),
                patch("subprocess.run", return_value=Mock(stdout=kernel)),
            ):
                if kernel.startswith(("MINGW", "MSYS")):
                    require_shell({})
                else:
                    with self.assertRaisesRegex(RuntimeError, "MSYS2 or Git Bash"):
                        require_shell({})


if __name__ == "__main__":
    unittest.main()
