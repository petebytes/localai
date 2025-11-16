#!/usr/bin/env python3
"""
Service Health Check Script

Checks the health status of all Docker services before secret rotation.
Saves state for comparison after rotation.

Usage:
    ./scripts/check-services.py [options]

Options:
    --save STATE_FILE    Save health status to JSON file
    --compare STATE_FILE Compare current health with saved state
    --verbose            Show detailed service information
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List


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


class ServiceHealthChecker:
    """Check health status of Docker Compose services"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.services = {}

    def get_compose_services(self) -> List[str]:
        """Get list of all services from docker-compose.yml"""
        try:
            result = subprocess.run(
                ["docker", "compose", "config", "--services"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip().split("\n")
        except subprocess.CalledProcessError as e:
            print(f"{Colors.FAIL}Error getting service list: {e.stderr}{Colors.ENDC}")
            return []

    def check_container_status(self, service_name: str) -> Dict:
        """Check detailed status of a single service"""
        try:
            # Get container info using docker compose ps
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json", service_name],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0 or not result.stdout.strip():
                return {
                    "status": "not_running",
                    "health": "unknown",
                    "state": "not found",
                }

            # Parse JSON output
            container_info = json.loads(result.stdout)

            status = container_info.get("State", "unknown")
            health = container_info.get("Health", "none")

            return {
                "status": status,
                "health": health,
                "service": service_name,
                "name": container_info.get("Name", ""),
                "state": status,
            }

        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            return {"status": "error", "health": "unknown", "error": str(e)}

    def check_all_services(self, verbose: bool = False) -> Dict[str, Dict]:
        """Check health of all services"""
        print(f"{Colors.HEADER}Checking service health...{Colors.ENDC}\n")

        services = self.get_compose_services()

        if not services:
            print(f"{Colors.WARNING}No services found{Colors.ENDC}")
            return {}

        results = {}

        for service in services:
            status = self.check_container_status(service)
            results[service] = status

            # Print status
            state = status.get("state", "unknown")
            health = status.get("health", "none")

            # Determine color based on status
            if state == "running":
                if health == "healthy" or health == "none":
                    color = Colors.OKGREEN
                    symbol = "✓"
                elif health == "starting":
                    color = Colors.WARNING
                    symbol = "⟳"
                else:
                    color = Colors.FAIL
                    symbol = "✗"
            else:
                color = Colors.FAIL
                symbol = "✗"

            # Print service status
            health_str = f"({health})" if health != "none" else ""
            print(
                f"  {color}{symbol} {service:30} {state:15} {health_str}{Colors.ENDC}"
            )

            if verbose and "error" in status:
                print(f"    {Colors.FAIL}Error: {status['error']}{Colors.ENDC}")

        return results

    def save_state(self, state_file: Path, results: Dict[str, Dict]):
        """Save current health state to JSON file"""
        state = {"timestamp": datetime.now().isoformat(), "services": results}

        state_file.parent.mkdir(parents=True, exist_ok=True)

        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

        print(f"\n{Colors.OKGREEN}✓ State saved to: {state_file}{Colors.ENDC}")

    def compare_state(self, state_file: Path, current_results: Dict[str, Dict]) -> bool:
        """Compare current state with saved state"""
        if not state_file.exists():
            print(f"{Colors.FAIL}State file not found: {state_file}{Colors.ENDC}")
            return False

        with open(state_file, "r") as f:
            saved_state = json.load(f)

        saved_timestamp = saved_state.get("timestamp", "unknown")
        saved_services = saved_state.get("services", {})

        print(
            f"\n{Colors.HEADER}Comparing with state from: {saved_timestamp}{Colors.ENDC}\n"
        )

        all_services = set(saved_services.keys()) | set(current_results.keys())
        all_healthy = True

        for service in sorted(all_services):
            saved = saved_services.get(service, {})
            current = current_results.get(service, {})

            saved_state_val = saved.get("state", "unknown")
            current_state_val = current.get("state", "unknown")

            saved_health = saved.get("health", "none")
            current_health = current.get("health", "none")

            # Determine if state changed
            if saved_state_val != current_state_val or saved_health != current_health:
                # State changed
                if current_state_val == "running" and (
                    current_health == "healthy" or current_health == "none"
                ):
                    color = Colors.OKGREEN
                    symbol = "↑"
                elif current_state_val != "running" or current_health == "unhealthy":
                    color = Colors.FAIL
                    symbol = "↓"
                    all_healthy = False
                else:
                    color = Colors.WARNING
                    symbol = "~"

                print(
                    f"  {color}{symbol} {service:30} {saved_state_val:15} → {current_state_val:15}{Colors.ENDC}"
                )
                if saved_health != current_health:
                    print(f"    Health: {saved_health} → {current_health}")
            else:
                # No change
                if current_state_val == "running":
                    color = Colors.OKGREEN
                    symbol = "="
                else:
                    color = Colors.WARNING
                    symbol = "="

                print(
                    f"  {color}{symbol} {service:30} {current_state_val:15} (unchanged){Colors.ENDC}"
                )

        return all_healthy

    def print_summary(self, results: Dict[str, Dict]):
        """Print summary statistics"""
        total = len(results)
        running = sum(1 for r in results.values() if r.get("state") == "running")
        healthy = sum(
            1
            for r in results.values()
            if r.get("state") == "running"
            and (r.get("health") == "healthy" or r.get("health") == "none")
        )

        print(f"\n{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
        print(f"{Colors.BOLD}Summary{Colors.ENDC}")
        print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
        print(f"  Total services:   {total}")
        print(f"  Running:          {Colors.OKGREEN}{running}{Colors.ENDC}")
        print(f"  Healthy:          {Colors.OKGREEN}{healthy}{Colors.ENDC}")

        not_healthy = total - healthy
        if not_healthy > 0:
            print(f"  Issues:           {Colors.FAIL}{not_healthy}{Colors.ENDC}")

        print()


def main():
    parser = argparse.ArgumentParser(
        description="Check health status of Docker Compose services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--save", type=str, metavar="STATE_FILE", help="Save health status to JSON file"
    )
    parser.add_argument(
        "--compare",
        type=str,
        metavar="STATE_FILE",
        help="Compare current health with saved state",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Show detailed service information"
    )

    args = parser.parse_args()

    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    try:
        checker = ServiceHealthChecker(project_root)

        # Check all services
        results = checker.check_all_services(verbose=args.verbose)

        # Save state if requested
        if args.save:
            state_file = Path(args.save)
            checker.save_state(state_file, results)

        # Compare state if requested
        if args.compare:
            state_file = Path(args.compare)
            all_healthy = checker.compare_state(state_file, results)
            if not all_healthy:
                print(
                    f"\n{Colors.WARNING}Warning: Some services degraded compared to saved state{Colors.ENDC}"
                )
                sys.exit(1)

        # Print summary
        checker.print_summary(results)

        # Exit with error if any services are not healthy
        unhealthy = [
            name
            for name, info in results.items()
            if info.get("state") != "running"
            or (
                info.get("health") not in ["healthy", "none"]
                and info.get("health") != ""
            )
        ]

        if unhealthy:
            print(
                f"{Colors.WARNING}Warning: {len(unhealthy)} service(s) are not healthy:{Colors.ENDC}"
            )
            for service in unhealthy:
                print(f"  • {service}")
            print()
            sys.exit(1)

        sys.exit(0)

    except Exception as e:
        print(f"\n{Colors.FAIL}ERROR: {e}{Colors.ENDC}\n", file=sys.stderr)
        import traceback

        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
