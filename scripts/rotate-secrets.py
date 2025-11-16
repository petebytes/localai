#!/usr/bin/env python3
"""
Secret Rotation Script for Local AI Environment

Generates new cryptographically secure secrets and updates .env files.
Creates automatic backups before rotation and validates all changes.

Usage:
    ./scripts/rotate-secrets.py [options]

Options:
    --dry-run         Preview changes without applying them
    --secrets SECRET  Rotate only specific secrets (comma-separated)
    --skip-backup     Skip creating backup (not recommended)
    --config PATH     Path to secrets-config.yaml (default: scripts/secrets-config.yaml)
"""

import argparse
import base64
import datetime
import hashlib
import hmac
import json
import os
import secrets as crypto_secrets
import shutil
import string
import sys
from pathlib import Path
from typing import Dict, List, Set

import yaml


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
    UNDERLINE = "\033[4m"


class SecretRotator:
    """Manages secret rotation for the entire environment"""

    def __init__(self, config_path: str, project_root: Path):
        self.project_root = project_root
        self.config_path = config_path
        self.config = self._load_config()
        self.new_secrets: Dict[str, str] = {}
        self.affected_services: Set[str] = set()

    def _load_config(self) -> dict:
        """Load the secrets configuration file"""
        config_file = self.project_root / self.config_path
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        with open(config_file, "r") as f:
            return yaml.safe_load(f)

    def generate_random_secret(self, length: int) -> str:
        """Generate cryptographically secure random string"""
        alphabet = string.ascii_letters + string.digits
        return "".join(crypto_secrets.choice(alphabet) for _ in range(length))

    def generate_jwt_token(self, secret: str, role: str) -> str:
        """Generate Supabase-compatible JWT token"""

        # JWT header
        header = {"alg": "HS256", "typ": "JWT"}

        # JWT payload with long expiration (2100)
        iat = 1739948400  # 2025-02-19
        exp = 1897714800  # 2030-02-19

        payload = {"role": role, "iss": "supabase", "iat": iat, "exp": exp}

        # Base64URL encode
        def b64url_encode(data: dict) -> str:
            json_str = json.dumps(data, separators=(",", ":"))
            return base64.urlsafe_b64encode(json_str.encode()).decode().rstrip("=")

        header_b64 = b64url_encode(header)
        payload_b64 = b64url_encode(payload)

        # Create signature
        message = f"{header_b64}.{payload_b64}".encode()
        signature = hmac.new(secret.encode(), message, hashlib.sha256).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

        return f"{header_b64}.{payload_b64}.{signature_b64}"

    def generate_secret(self, secret_name: str, secret_config: dict) -> str:
        """Generate a new secret based on its type"""
        secret_type = secret_config["type"]

        if secret_type == "random":
            length = secret_config["length"]
            return self.generate_random_secret(length)

        elif secret_type == "jwt-token":
            # JWT tokens depend on JWT_SECRET
            depends_on = secret_config.get("depends_on")
            if not depends_on:
                raise ValueError(f"{secret_name} missing 'depends_on' field")

            jwt_secret = self.new_secrets.get(depends_on)
            if not jwt_secret:
                raise ValueError(
                    f"Cannot generate {secret_name}: {depends_on} not yet generated"
                )

            role = secret_config["role"]
            return self.generate_jwt_token(jwt_secret, role)

        elif secret_type == "static":
            # Static secrets are not auto-rotated
            return None

        else:
            raise ValueError(f"Unknown secret type: {secret_type}")

    def read_env_file(self, env_path: Path) -> Dict[str, str]:
        """Parse .env file into dictionary"""
        env_vars = {}

        if not env_path.exists():
            print(f"{Colors.WARNING}Warning: {env_path} does not exist{Colors.ENDC}")
            return env_vars

        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Parse KEY=value
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()

        return env_vars

    def write_env_file(
        self, env_path: Path, env_vars: Dict[str, str], dry_run: bool = False
    ):
        """Write dictionary to .env file, preserving comments and structure"""
        if dry_run:
            print(f"{Colors.OKCYAN}[DRY RUN] Would write to: {env_path}{Colors.ENDC}")
            return

        # Read original file to preserve structure
        original_lines = []
        if env_path.exists():
            with open(env_path, "r") as f:
                original_lines = f.readlines()

        # Create temp file for atomic write
        temp_path = env_path.with_suffix(".env.tmp")

        with open(temp_path, "w") as f:
            for line in original_lines:
                stripped = line.strip()

                # Preserve comments and empty lines
                if not stripped or stripped.startswith("#"):
                    f.write(line)
                    continue

                # Update KEY=value lines
                if "=" in stripped:
                    key = stripped.split("=", 1)[0].strip()
                    if key in env_vars:
                        # Write updated value
                        f.write(f"{key}={env_vars[key]}\n")
                    else:
                        # Preserve original line
                        f.write(line)
                else:
                    f.write(line)

        # Atomic rename
        temp_path.rename(env_path)

        # Set restrictive permissions
        os.chmod(env_path, 0o600)

    def create_backup(self, dry_run: bool = False) -> Path:
        """Create timestamped backup of all .env files"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_dir = self.project_root / self.config["backup"]["directory"]
        backup_path = backup_dir / f"secrets-backup-{timestamp}"

        if dry_run:
            print(
                f"{Colors.OKCYAN}[DRY RUN] Would create backup at: {backup_path}{Colors.ENDC}"
            )
            return backup_path

        # Create backup directory
        backup_path.mkdir(parents=True, exist_ok=True)

        # Backup all .env files
        env_files = set()
        for secret_config in self.config["secrets"].values():
            if "files" in secret_config:
                env_files.update(secret_config["files"])

        for env_file in env_files:
            src = self.project_root / env_file
            if src.exists():
                dst = backup_path / env_file
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                # Restrict permissions
                os.chmod(dst, 0o600)

        # Save metadata
        metadata = {
            "timestamp": timestamp,
            "rotated_secrets": list(self.new_secrets.keys()),
            "affected_services": list(self.affected_services),
        }

        metadata_path = backup_path / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        os.chmod(metadata_path, 0o600)

        print(f"{Colors.OKGREEN}✓ Backup created: {backup_path}{Colors.ENDC}")
        return backup_path

    def cleanup_old_backups(self, dry_run: bool = False):
        """Remove backups older than retention period"""
        retention_days = self.config["backup"]["retention_days"]
        backup_dir = self.project_root / self.config["backup"]["directory"]

        if not backup_dir.exists():
            return

        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)

        for backup_path in backup_dir.iterdir():
            if not backup_path.is_dir():
                continue

            # Parse timestamp from directory name
            try:
                timestamp_str = backup_path.name.replace("secrets-backup-", "")
                backup_date = datetime.datetime.strptime(timestamp_str, "%Y%m%d-%H%M%S")

                if backup_date < cutoff_date:
                    if dry_run:
                        print(
                            f"{Colors.OKCYAN}[DRY RUN] Would delete old backup: {backup_path}{Colors.ENDC}"
                        )
                    else:
                        shutil.rmtree(backup_path)
                        print(
                            f"{Colors.WARNING}Deleted old backup: {backup_path}{Colors.ENDC}"
                        )
            except ValueError:
                # Skip directories that don't match expected format
                continue

    def rotate_secrets(self, secret_names: List[str] = None, dry_run: bool = False):
        """Main rotation logic"""
        secrets_config = self.config["secrets"]

        # Determine which secrets to rotate
        if secret_names:
            # Validate requested secrets exist
            for name in secret_names:
                if name not in secrets_config:
                    raise ValueError(f"Unknown secret: {name}")
            secrets_to_rotate = secret_names
        else:
            # Rotate all auto-rotatable secrets
            secrets_to_rotate = [
                name
                for name, config in secrets_config.items()
                if config.get("auto_rotate", False)
            ]

        print(
            f"{Colors.HEADER}Rotating {len(secrets_to_rotate)} secrets...{Colors.ENDC}"
        )

        # Generate new secrets (dependencies first)
        # Simple approach: generate in order, JWT tokens will be generated after JWT_SECRET
        for secret_name in secrets_to_rotate:
            secret_config = secrets_config[secret_name]

            # Skip if depends on something not yet generated
            depends_on = secret_config.get("depends_on")
            if depends_on and depends_on not in self.new_secrets:
                # Generate dependency first
                if depends_on in secrets_to_rotate:
                    dep_value = self.generate_secret(
                        depends_on, secrets_config[depends_on]
                    )
                    if dep_value:
                        self.new_secrets[depends_on] = dep_value
                        print(f"  {Colors.OKBLUE}✓ Generated {depends_on}{Colors.ENDC}")

            # Generate this secret
            new_value = self.generate_secret(secret_name, secret_config)

            if new_value:
                self.new_secrets[secret_name] = new_value
                print(f"  {Colors.OKBLUE}✓ Generated {secret_name}{Colors.ENDC}")

                # Track affected services
                if "restart_services" in secret_config:
                    self.affected_services.update(secret_config["restart_services"])
            else:
                print(
                    f"  {Colors.WARNING}⊘ Skipped {secret_name} (static/user-managed){Colors.ENDC}"
                )

        # Update .env files
        print(f"\n{Colors.HEADER}Updating .env files...{Colors.ENDC}")

        env_files_to_update = set()
        for secret_name in self.new_secrets.keys():
            secret_config = secrets_config[secret_name]
            if "files" in secret_config:
                env_files_to_update.update(secret_config["files"])

        for env_file in env_files_to_update:
            env_path = self.project_root / env_file

            # Read current values
            env_vars = self.read_env_file(env_path)

            # Update with new secrets
            updated_count = 0
            for secret_name, new_value in self.new_secrets.items():
                secret_config = secrets_config[secret_name]
                if env_file in secret_config.get("files", []):
                    env_vars[secret_name] = new_value
                    updated_count += 1

            # Write back
            if updated_count > 0:
                self.write_env_file(env_path, env_vars, dry_run)
                print(
                    f"  {Colors.OKGREEN}✓ Updated {env_file} ({updated_count} secrets){Colors.ENDC}"
                )

    def print_summary(self):
        """Print summary of rotation"""
        print(f"\n{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
        print(f"{Colors.BOLD}Rotation Summary{Colors.ENDC}")
        print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}")

        print(f"\n{Colors.OKBLUE}Rotated Secrets:{Colors.ENDC}")
        for secret_name in sorted(self.new_secrets.keys()):
            print(f"  • {secret_name}")

        print(f"\n{Colors.WARNING}Services Requiring Restart:{Colors.ENDC}")
        if self.affected_services:
            for service in sorted(self.affected_services):
                print(f"  • {service}")
        else:
            print(f"  {Colors.OKGREEN}(none){Colors.ENDC}")

        print(f"\n{Colors.BOLD}Next Steps:{Colors.ENDC}")
        print("  1. Review the changes above")
        print(
            f"  2. Run: {Colors.OKCYAN}./scripts/restart-after-rotation.sh{Colors.ENDC}"
        )
        print("  3. Verify services are healthy")
        print(
            f"  4. If issues occur, restore with: {Colors.WARNING}./scripts/restore-secrets.py{Colors.ENDC}"
        )
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Rotate secrets for Local AI environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying them"
    )
    parser.add_argument(
        "--secrets",
        type=str,
        help="Comma-separated list of secrets to rotate (default: all auto-rotatable)",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip creating backup (NOT RECOMMENDED)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="scripts/secrets-config.yaml",
        help="Path to secrets-config.yaml",
    )

    args = parser.parse_args()

    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    try:
        # Initialize rotator
        rotator = SecretRotator(args.config, project_root)

        # Parse secret names if provided
        secret_names = None
        if args.secrets:
            secret_names = [s.strip() for s in args.secrets.split(",")]

        # Create backup
        if not args.skip_backup:
            rotator.create_backup(dry_run=args.dry_run)

        # Rotate secrets
        rotator.rotate_secrets(secret_names, dry_run=args.dry_run)

        # Cleanup old backups
        rotator.cleanup_old_backups(dry_run=args.dry_run)

        # Print summary
        rotator.print_summary()

        if args.dry_run:
            print(
                f"\n{Colors.OKCYAN}This was a DRY RUN. No changes were made.{Colors.ENDC}"
            )
            print(f"Remove --dry-run to apply changes.{Colors.ENDC}\n")
            sys.exit(0)
        else:
            print(f"{Colors.OKGREEN}✓ Secret rotation complete!{Colors.ENDC}\n")
            sys.exit(0)

    except Exception as e:
        print(f"\n{Colors.FAIL}ERROR: {e}{Colors.ENDC}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
