#!/usr/bin/env python3
"""
Unit and integration tests for migration utility (Story 1.7).

Tests AC#1-5:
- AC#1: --migrate flag converts single-file → split format
- AC#2: Migration preserves all existing index data
- AC#3: Migration creates backup of original index
- AC#4: Migration validates split index after creation
- AC#5: Clear success/failure messages with rollback on failure
"""

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

# Import functions under test
from project_index import (
    create_backup,
    extract_legacy_data,
    validate_migration_integrity,
    rollback_migration,
    migrate_to_split_format,
    generate_split_index,
    build_index
)


class TestCreateBackup(unittest.TestCase):
    """Test backup creation mechanism (AC#3)."""

    def setUp(self):
        """Create temporary directory for test files."""
        self.test_dir = tempfile.mkdtemp()
        self.index_path = Path(self.test_dir) / 'PROJECT_INDEX.json'
        self.index_path.write_text('{"version": "1.0", "test": "data"}')

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_backup_creation_with_timestamp(self):
        """Test AC#3: Backup created with timestamp."""
        backup_path = create_backup(self.index_path)

        # Verify backup exists
        self.assertTrue(backup_path.exists())

        # Verify backup filename has timestamp
        self.assertTrue(backup_path.name.startswith('PROJECT_INDEX.json.backup-'))

        # Verify backup content matches original
        self.assertEqual(
            backup_path.read_text(),
            self.index_path.read_text()
        )

    def test_backup_preserves_permissions(self):
        """Test AC#3: Backup preserves file permissions."""
        # Set specific permissions on original
        os.chmod(self.index_path, 0o644)

        backup_path = create_backup(self.index_path)

        # Verify permissions preserved
        original_stat = os.stat(self.index_path)
        backup_stat = os.stat(backup_path)
        self.assertEqual(original_stat.st_mode, backup_stat.st_mode)

    def test_backup_failure_on_nonexistent_file(self):
        """Test backup fails gracefully if source doesn't exist."""
        nonexistent = Path(self.test_dir) / 'nonexistent.json'

        with self.assertRaises(IOError):
            create_backup(nonexistent)


class TestExtractLegacyData(unittest.TestCase):
    """Test legacy data extraction (AC#2)."""

    def setUp(self):
        """Create temporary directory and test index."""
        self.test_dir = tempfile.mkdtemp()
        self.index_path = Path(self.test_dir) / 'PROJECT_INDEX.json'

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_extract_valid_legacy_index(self):
        """Test extracting valid legacy index data."""
        legacy_data = {
            "version": "1.0",
            "at": "2025-11-01",
            "f": {"test.py": ["p", ["test_func:():"]]},
            "g": [],
            "d": {}
        }
        self.index_path.write_text(json.dumps(legacy_data))

        result = extract_legacy_data(self.index_path)

        self.assertEqual(result, legacy_data)
        self.assertEqual(result['version'], '1.0')

    def test_extract_nonexistent_index(self):
        """Test extraction fails if index doesn't exist."""
        nonexistent = Path(self.test_dir) / 'nonexistent.json'

        with self.assertRaises(FileNotFoundError):
            extract_legacy_data(nonexistent)

    def test_extract_corrupted_json(self):
        """Test extraction fails on corrupted JSON."""
        self.index_path.write_text('{"invalid": json}')

        with self.assertRaises(json.JSONDecodeError):
            extract_legacy_data(self.index_path)


class TestValidateMigrationIntegrity(unittest.TestCase):
    """Test migration integrity validation (AC#4)."""

    def test_validation_passes_with_matching_data(self):
        """Test AC#4: Validation passes when all data preserved."""
        legacy_index = {
            "f": {
                "scripts/test.py": ["p", ["test_func:(x:int)->bool:test_func:"]],
                "scripts/utils.py": ["p", ["helper:()::"]]
            },
            "g": [["test_func", "helper"]],
            "d": {"README.md": ["Overview"]}
        }

        core_index = {
            "version": "2.0-split",
            "modules": {
                "scripts": {"file_count": 2, "function_count": 2}
            },
            "g": [["test_func", "helper"]]
        }

        detail_modules = {
            "scripts": {
                "files": {
                    "scripts/test.py": {
                        "functions": {
                            "test_func": {
                                "signature": "test_func:(x:int)->bool:test_func:",
                                "calls": ["helper"]
                            }
                        }
                    },
                    "scripts/utils.py": {
                        "functions": {
                            "helper": {
                                "signature": "helper:::",
                                "calls": []
                            }
                        }
                    }
                },
                "documentation": {"README.md": ["Overview"]},
                "call_graph_local": []
            }
        }

        result = validate_migration_integrity(legacy_index, core_index, detail_modules)
        self.assertTrue(result)

    def test_validation_fails_on_missing_files(self):
        """Test AC#4: Validation fails if files are missing."""
        legacy_index = {
            "f": {
                "scripts/test.py": ["p", []],
                "scripts/utils.py": ["p", []]
            },
            "g": [],
            "d": {}
        }

        core_index = {"version": "2.0-split"}

        detail_modules = {
            "scripts": {
                "files": {
                    "scripts/test.py": {}
                    # Missing utils.py
                }
            }
        }

        result = validate_migration_integrity(legacy_index, core_index, detail_modules)
        self.assertFalse(result)

    def test_validation_fails_on_function_count_mismatch(self):
        """Test AC#4: Validation fails if function count doesn't match."""
        legacy_index = {
            "f": {
                "test.py": ["p", ["func1:():", "func2:(x):"]]
            },
            "g": [],
            "d": {}
        }

        core_index = {"version": "2.0-split"}

        detail_modules = {
            "root": {
                "files": {
                    "test.py": {
                        "functions": {
                            "func1": {"signature": "func1:():"}
                            # Missing func2
                        }
                    }
                }
            }
        }

        result = validate_migration_integrity(legacy_index, core_index, detail_modules)
        self.assertFalse(result)


class TestRollbackMigration(unittest.TestCase):
    """Test rollback mechanism (AC#5)."""

    def setUp(self):
        """Create temporary directory and test files."""
        self.test_dir = tempfile.mkdtemp()
        self.index_path = Path(self.test_dir) / 'PROJECT_INDEX.json'
        self.backup_path = Path(self.test_dir) / 'PROJECT_INDEX.json.backup-test'
        self.detail_dir = Path(self.test_dir) / 'PROJECT_INDEX.d'

        # Create original and backup
        self.index_path.write_text('{"version": "2.0-split"}')
        self.backup_path.write_text('{"version": "1.0"}')

        # Create detail directory
        self.detail_dir.mkdir()
        (self.detail_dir / 'module.json').write_text('{}')

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_rollback_restores_backup(self):
        """Test AC#5: Rollback restores original from backup."""
        rollback_migration(self.backup_path, self.index_path, self.detail_dir)

        # Verify original restored
        restored_content = self.index_path.read_text()
        self.assertEqual(restored_content, '{"version": "1.0"}')

    def test_rollback_cleans_up_detail_directory(self):
        """Test AC#5: Rollback removes partial split artifacts."""
        rollback_migration(self.backup_path, self.index_path, self.detail_dir)

        # Verify detail directory removed
        self.assertFalse(self.detail_dir.exists())

    def test_rollback_handles_missing_backup_gracefully(self):
        """Test rollback doesn't fail if backup missing."""
        nonexistent_backup = Path(self.test_dir) / 'nonexistent.backup'

        # Should not raise exception
        rollback_migration(nonexistent_backup, self.index_path, self.detail_dir)


class TestMigrateToSplitFormat(unittest.TestCase):
    """Integration tests for full migration workflow (AC#1-5)."""

    def setUp(self):
        """Create temporary directory with legacy index."""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Create minimal project structure
        Path('scripts').mkdir()
        Path('scripts/test.py').write_text('def test_func():\n    pass\n')

        # Create legacy index
        self.legacy_index = {
            "version": "1.0",
            "at": "2025-11-01",
            "root": ".",
            "tree": [".", "├── scripts/"],
            "stats": {
                "total_files": 1,
                "total_directories": 1,
                "fully_parsed": {"python": 1},
                "markdown_files": 0
            },
            "f": {
                "scripts/test.py": ["p", ["test_func:()::test_func:"]]
            },
            "g": [],
            "d": {}
        }

        Path('PROJECT_INDEX.json').write_text(json.dumps(self.legacy_index))

    def tearDown(self):
        """Clean up temporary directory."""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)

    def test_migrate_creates_split_format(self):
        """Test AC#1: Migration converts legacy → split format."""
        success = migrate_to_split_format('.')

        self.assertTrue(success)

        # Verify split format created
        core_index_path = Path('PROJECT_INDEX.json')
        detail_dir = Path('PROJECT_INDEX.d')

        self.assertTrue(core_index_path.exists())
        self.assertTrue(detail_dir.exists())

        # Verify core index has split version (updated to 2.1-enhanced in Story 2.3)
        core_index = json.loads(core_index_path.read_text())
        self.assertEqual(core_index['version'], '2.1-enhanced')

    def test_migrate_creates_backup(self):
        """Test AC#3: Migration creates backup before converting."""
        success = migrate_to_split_format('.')

        self.assertTrue(success)

        # Verify backup exists
        backups = list(Path('.').glob('PROJECT_INDEX.json.backup-*'))
        self.assertEqual(len(backups), 1)

        # Verify backup contains original data
        backup_data = json.loads(backups[0].read_text())
        self.assertEqual(backup_data['version'], '1.0')

    def test_migrate_preserves_data(self):
        """Test AC#2: Migration preserves all data."""
        success = migrate_to_split_format('.')

        self.assertTrue(success)

        # Load split format
        core_index = json.loads(Path('PROJECT_INDEX.json').read_text())
        detail_dir = Path('PROJECT_INDEX.d')

        # Verify file preserved
        detail_modules = {}
        for module_file in detail_dir.glob('*.json'):
            module_data = json.loads(module_file.read_text())
            detail_modules[module_file.stem] = module_data

        # Check file count
        all_files = set()
        for module_data in detail_modules.values():
            all_files.update(module_data.get('files', {}).keys())

        self.assertIn('scripts/test.py', all_files)

    def test_migrate_validates_integrity(self):
        """Test AC#4: Migration validates data integrity."""
        # This is tested implicitly by the validation function tests above
        success = migrate_to_split_format('.')

        # Migration should succeed (validation passes)
        self.assertTrue(success)

    def test_migrate_already_split_format(self):
        """Test migration detects already-split format and exits gracefully."""
        # First migration
        migrate_to_split_format('.')

        # Second migration attempt
        success = migrate_to_split_format('.')

        # Should succeed with no-op
        self.assertTrue(success)

    def test_migrate_nonexistent_index(self):
        """Test AC#5: Clear failure message when no index exists."""
        Path('PROJECT_INDEX.json').unlink()

        success = migrate_to_split_format('.')

        # Should fail gracefully
        self.assertFalse(success)

    def test_migrate_performance_under_10_seconds(self):
        """Test NFR: Migration completes in <10 seconds."""
        start_time = time.time()
        migrate_to_split_format('.')
        elapsed = time.time() - start_time

        self.assertLess(elapsed, 10.0, f"Migration took {elapsed:.2f}s (should be <10s)")


class TestMigrationCommandLineInterface(unittest.TestCase):
    """Test --migrate flag integration (AC#1)."""

    def setUp(self):
        """Create temporary directory with legacy index."""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Create minimal legacy index
        legacy_index = {
            "version": "1.0",
            "at": "2025-11-01",
            "root": ".",
            "f": {},
            "g": [],
            "d": {}
        }
        Path('PROJECT_INDEX.json').write_text(json.dumps(legacy_index))

    def tearDown(self):
        """Clean up temporary directory."""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)

    @patch('sys.argv', ['project_index.py', '--migrate'])
    def test_migrate_flag_triggers_migration(self):
        """Test AC#1: --migrate flag triggers migration workflow."""
        # Import main to test CLI
        from project_index import main

        # Mock sys.exit to catch exit code
        with self.assertRaises(SystemExit) as cm:
            main()

        # Should exit with code 0 (success)
        self.assertEqual(cm.exception.code, 0)

        # Verify migration happened
        self.assertTrue(Path('PROJECT_INDEX.d').exists())


def run_all_tests():
    """Run all migration tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCreateBackup))
    suite.addTests(loader.loadTestsFromTestCase(TestExtractLegacyData))
    suite.addTests(loader.loadTestsFromTestCase(TestValidateMigrationIntegrity))
    suite.addTests(loader.loadTestsFromTestCase(TestRollbackMigration))
    suite.addTests(loader.loadTestsFromTestCase(TestMigrateToSplitFormat))
    suite.addTests(loader.loadTestsFromTestCase(TestMigrationCommandLineInterface))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
