#!/usr/bin/env python3
"""Exercise the installed app on an explicitly selected Android test device."""

import argparse
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

PACKAGE = "io.github.hanenashi.overtura"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True, help="ADB device; never select a device implicitly")
    parser.add_argument("--lab", action="store_true", help="Target the separate Overtura Lab app")
    args = parser.parse_args()
    package = PACKAGE + (".lab" if args.lab else "")
    adb = ["adb", "-s", args.serial]
    evidence = Path(tempfile.mkdtemp(prefix="overtura-app-"))

    def shell(*command):
        return subprocess.run(adb + ["shell", shlex.join(command)], text=True,
                              capture_output=True, check=True, timeout=20).stdout

    def screen():
        shell("uiautomator", "dump", "/data/local/tmp/overtura-ui.xml")
        xml = shell("cat", "/data/local/tmp/overtura-ui.xml")
        return ET.fromstring(xml)

    def find(value, attribute="text"):
        for _ in range(3):
            for node in screen().iter("node"):
                if node.get(attribute, "").casefold() == value.casefold():
                    return node
            time.sleep(0.3)
        raise AssertionError("App control not found: " + value)

    def tap(value, attribute="text"):
        node = find(value, attribute)
        bounds = [int(number) for number in re.findall(r"\d+", node.get("bounds"))]
        shell("input", "tap", str((bounds[0] + bounds[2]) // 2), str((bounds[1] + bounds[3]) // 2))
        time.sleep(0.2)

    def edit(label, value):
        tap(label, "content-desc")
        # Fields select all on focus; a delete also handles restoring an empty alias.
        shell("input", "keyevent", "KEYCODE_MOVE_END")
        shell("input", "keyevent", "--longpress", "KEYCODE_DEL")
        # Select the entire value explicitly, independent of keyboard behavior.
        shell("input", "keycombination", "113", "29")
        shell("input", "keyevent", "KEYCODE_DEL")
        if value:
            shell("input", "text", value)
        shell("input", "keyevent", "KEYCODE_BACK")

    def launch():
        shell("am", "start", "-W", "-n", package + "/io.github.hanenashi.overtura.MainActivity")

    def screenshot(name):
        with (evidence / name).open("wb") as stream:
            subprocess.run(adb + ["exec-out", "screencap", "-p"], stdout=stream, check=True, timeout=15)

    shell("am", "force-stop", package)
    launch()
    find("Your work,\nwithin reach.")
    screenshot("start.png")
    print("PASS: app launch", flush=True)
    tap("Sessions")
    old_host = find("SSH alias in Termux", "content-desc").get("text", "")
    old_session = find("Session name", "content-desc").get("text", "")
    # Android exposes the hint as text for an empty field.
    if old_host == "my-node":
        old_host = ""
    try:
        edit("SSH alias in Termux", "bad;host")
        tap("Reattach  →")
        find("Check your details")
        tap("OK")
        edit("SSH alias in Termux", "my-node")
        edit("Session name", "demo")
        tap("Reattach  →")
        find("Return to your session")
        commands = [n.get("text", "") for n in screen().iter("node")]
        assert any("session attach" in value and "demo" in value for value in commands)
        tap("CANCEL")
        screenshot("sessions.png")
        print("PASS: validation and session command preview", flush=True)
        tap("List sessions")
        find("List host sessions")
        tap("COPY + TERMUX")
        time.sleep(0.5)
        # Inspect only a package name, never dump Termux's terminal contents.
        activities = shell("dumpsys", "activity", "activities")
        resumed = "\n".join(line for line in activities.splitlines() if "ResumedActivity" in line)
        if "com.termux/" in resumed:
            print("PASS: Termux opened; no command was executed")
            launch()
        else:
            find("Termux is needed")
            tap("OK")
            print("PASS: missing-Termux fallback")
        shell("am", "force-stop", package)
        launch()
        tap("Sessions")
        assert find("SSH alias in Termux", "content-desc").get("text") == "my-node"
        assert find("Session name", "content-desc").get("text") == "demo"
        tap("Install")
        find("1 · Download Termux")
        screenshot("install.png")
        tap("FAQ")
        find("Where does my work run?")
        screenshot("faq.png")
        print("PASS: navigation, validation, command preview and saved settings")
    finally:
        shell("am", "force-stop", package)
        launch()
        tap("Sessions")
        edit("SSH alias in Termux", old_host)
        edit("Session name", old_session)
        tap("Start")
        shell("rm", "-f", "/data/local/tmp/overtura-ui.xml")
    print("Screenshots:", evidence)


if __name__ == "__main__":
    main()
