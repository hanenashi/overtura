from pathlib import Path
import tempfile
import unittest
from phone_lab_config import configure, ALIAS, BEGIN


class LabConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        (self.home / '.ssh').mkdir()
        self.config = self.home / '.ssh/config'
        self.payload = {'action': 'up', 'key': 'test-only-key', 'known_hosts': 'test-only-host'}

    def test_repeat_setup_and_remove_preserve_unrelated_config_and_symlink(self):
        original = b'Host example\r\n    HostName example.invalid\r\n'
        target = self.home / 'actual-config'
        target.write_bytes(original)
        self.config.symlink_to(target)
        configure(self.home, self.payload)
        configure(self.home, self.payload)
        self.assertEqual(1, target.read_text().count(BEGIN))
        self.assertTrue(target.read_bytes().endswith(original))
        configure(self.home, {'action': 'remove'})
        self.assertTrue(self.config.is_symlink())
        self.assertEqual(original, target.read_bytes())
        self.assertFalse((self.home / '.ssh' / ALIAS).exists())

    def test_refuses_existing_unowned_alias_or_directory(self):
        self.config.write_text('Host ' + ALIAS + '\n')
        with self.assertRaises(ValueError):
            configure(self.home, self.payload)
        self.config.unlink()
        (self.home / '.ssh' / ALIAS).mkdir()
        with self.assertRaises(ValueError):
            configure(self.home, self.payload)

    def test_tampered_markers_or_key_symlink_are_refused(self):
        configure(self.home, self.payload)
        self.config.write_text('Host example\n' + self.config.read_text())
        with self.assertRaises(ValueError):
            configure(self.home, {'action': 'remove'})
        self.config.write_text(self.config.read_text().removeprefix('Host example\n'))
        key = self.home / '.ssh' / ALIAS / 'key'
        key.unlink()
        key.symlink_to(self.config)
        with self.assertRaises(ValueError):
            configure(self.home, self.payload)


if __name__ == '__main__':
    unittest.main()
