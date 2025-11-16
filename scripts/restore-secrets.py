#!/usr/bin/env python3
"""
Secret Restore Script

Restore secrets from a timestamped backup.
Use this if secret rotation causes issues.

Usage:
    ./scripts/restore-secrets.py [options]

Options:
    --list                List all available backups
    --backup TIMESTAMP    Restore from specific backup (YYYYMMDD-HHMMSS)
    --latest              Restore from most recent backup
    --dry-run             Preview restore without applying changes
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


class Colors:
    """ANSI color codes for terminal output"""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


class SecretRestorer:
    """Restore secrets from backup"""

    def __init__(self, project_root: Path, backup_dir: str = "backups/secrets"):
        self.project_root = project_root
        self.backup_root = project_root / backup_dir

    def list_backups(self) -> List[Tuple[str, Path, dict]]:
        """List all available backups with metadata"""
        if not self.backup_root.exists():
            return []

        backups = []

        for backup_path in sorted(self.backup_root.iterdir(), reverse=True):
            if not backup_path.is_dir():
                continue

            # Parse timestamp
            try:
                timestamp_str = backup_path.name.replace("secrets-backup-", "")
                datetime.strptime(timestamp_str, "%Y%m%d-%H%M%S")
            except ValueError:
                continue

            # Load metadata
            metadata_path = backup_path / "metadata.json"
            metadata = {}
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)

            backups.append((timestamp_str, backup_path, metadata))

        return backups

    def print_backups(self):
        """Print list of available backups"""
        backups = self.list_backups()

        if not backups:
            print(
                f"{Colors.WARNING}No backups found in {self.backup_root}{Colors.ENDC}"
            )
            return

        print(f"{Colors.HEADER}Available Backups:{Colors.ENDC}\n")

        for i, (timestamp, path, metadata) in enumerate(backups):
            # Format timestamp for display
            try:
                dt = datetime.strptime(timestamp, "%Y%m%d-%H%M%S")
                display_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                display_time = timestamp

            # Calculate age
            age = datetime.now() - dt
            if age.days > 0:
                age_str = f"{age.days} day(s) ago"
            elif age.seconds > 3600:
                age_str = f"{age.seconds // 3600} hour(s) ago"
            else:
                age_str = f"{age.seconds // 60} minute(s) ago"

            # Print backup info
            print(f"{Colors.OKBLUE}{i + 1}. {display_time}{Colors.ENDC} ({age_str})")
            print(f"   Timestamp: {Colors.OKCYAN}{timestamp}{Colors.ENDC}")

            if "rotated_secrets" in metadata:
                secret_count = len(metadata["rotated_secrets"])
                print(f"   Secrets rotated: {secret_count}")

            if "affected_services" in metadata:
                service_count = len(metadata["affected_services"])
                print(f"   Services affected: {service_count}")

            print()

    def find_backup(self, timestamp: str) -> Optional[Path]:
        """Find backup by timestamp"""
        backup_path = self.backup_root / f"secrets-backup-{timestamp}"

        if backup_path.exists() and backup_path.is_dir():
            return backup_path

        return None

    def get_latest_backup(self) -> Optional[Path]:
        """Get the most recent backup"""
        backups = self.list_backups()

        if not backups:
            return None

        return backups[0][1]  # Return path of first (most recent) backup

    def restore_from_backup(self, backup_path: Path, dry_run: bool = False):
        """Restore .env files from backup"""
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        # Load metadata
        metadata_path = backup_path / "metadata.json"
        metadata = {}
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

        print(
            f"{Colors.HEADER}Restoring from backup: {backup_path.name}{Colors.ENDC}\n"
        )

        if metadata:
            print(f"{Colors.OKBLUE}Backup Info:{Colors.ENDC}")
            print(f"  Timestamp: {metadata.get('timestamp', 'unknown')}")

            if "rotated_secrets" in metadata:
                print(f"  Secrets: {', '.join(metadata['rotated_secrets'][:5])}")
                if len(metadata["rotated_secrets"]) > 5:
                    print(
                        f"          ... and {len(metadata['rotated_secrets']) - 5} more"
                    )

            print()

        # Find all .env files in backup
        env_files = []
        for item in backup_path.rglob(".env*"):
            if item.is_file() and item.name != "metadata.json":
                # Get relative path
                rel_path = item.relative_to(backup_path)
                env_files.append(rel_path)

        if not env_files:
            print(f"{Colors.WARNING}No .env files found in backup{Colors.ENDC}")
            return

        print(f"{Colors.OKBLUE}Restoring {len(env_files)} file(s):{Colors.ENDC}\n")

        # Restore each file
        for rel_path in env_files:
            src = backup_path / rel_path
            dst = self.project_root / rel_path

            if dry_run:
                print(
                    f"  {Colors.OKCYAN}[DRY RUN] Would restore: {rel_path}{Colors.ENDC}"
                )
            else:
                # Ensure destination directory exists
                dst.parent.mkdir(parents=True, exist_ok=True)

                # Copy file
                shutil.copy2(src, dst)

                # Set restrictive permissions
                import os

                os.chmod(dst, 0o600)

                print(f"  {Colors.OKGREEN}✓ Restored: {rel_path}{Colors.ENDC}")

        print(f"\n{Colors.OKGREEN}✓ Restore complete!{Colors.ENDC}\n")

        # Print next steps
        print(f"{Colors.BOLD}Next Steps:{Colors.ENDC}")
        print(
            f"  1. Restart services: {Colors.OKCYAN}./scripts/restart-after-rotation.sh{Colors.ENDC}"
        )
        print(
            f"  2. Verify services are healthy: {Colors.OKCYAN}./scripts/check-services.py{Colors.ENDC}"
        )
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Restore secrets from backup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--list", action="store_true", help="List all available backups"
    )
    parser.add_argument(
        "--backup",
        type=str,
        metavar="TIMESTAMP",
        help="Restore from specific backup (YYYYMMDD-HHMMSS)",
    )
    parser.add_argument(
        "--latest", action="store_true", help="Restore from most recent backup"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview restore without applying changes",
    )

    args = parser.parse_args()

    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    try:
        restorer = SecretRestorer(project_root)

        # List backups if requested
        if args.list:
            restorer.print_backups()
            sys.exit(0)

        # Determine which backup to restore
        backup_path = None

        if args.backup:
            backup_path = restorer.find_backup(args.backup)
            if not backup_path:
                print(f"{Colors.FAIL}Backup not found: {args.backup}{Colors.ENDC}")
                print("\nRun with --list to see available backups")
                sys.exit(1)

        elif args.latest:
            backup_path = restorer.get_latest_backup()
            if not backup_path:
                print(f"{Colors.FAIL}No backups found{Colors.ENDC}")
                sys.exit(1)

        else:
            # No restore action specified
            parser.print_help()
            print(
                f"\n{Colors.WARNING}Please specify --list, --backup, or --latest{Colors.ENDC}"
            )
            sys.exit(1)

        # Confirm restore
        if not args.dry_run:
            print(
                f"{Colors.WARNING}This will OVERWRITE current .env files!{Colors.ENDC}"
            )
            response = input(
                f"Are you sure you want to restore from {backup_path.name}? [y/N]: "
            )

            if response.lower() not in ["y", "yes"]:
                print(f"{Colors.WARNING}Restore cancelled{Colors.ENDC}")
                sys.exit(0)

        # Perform restore
        restorer.restore_from_backup(backup_path, dry_run=args.dry_run)

        if args.dry_run:
            print(
                f"{Colors.OKCYAN}This was a DRY RUN. No changes were made.{Colors.ENDC}"
            )
            print(f"Remove --dry-run to apply changes.{Colors.ENDC}\n")

        sys.exit(0)

    except Exception as e:
        print(f"\n{Colors.FAIL}ERROR: {e}{Colors.ENDC}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
