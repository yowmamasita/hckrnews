#!/usr/bin/env python3
"""
Version bumping script for hckrnews.

This script updates version numbers across the codebase:
- pyproject.toml (version field)
- User-Agent in scraper.py
- User-Agent in api.py
- Creates a git commit (optional)
- Creates a git tag for the new version (optional)

Usage:
    python bump_version.py [major|minor|patch]
    python bump_version.py --set X.Y.Z
    python bump_version.py [major|minor|patch] --commit  # Create git commit
    python bump_version.py [major|minor|patch] --tag     # Create git tag (with commit)
    python bump_version.py --set X.Y.Z --commit         # Create git commit
    python bump_version.py --set X.Y.Z --tag            # Create git tag (with commit)

Examples:
    python bump_version.py patch  # Increments the patch version (0.1.0 -> 0.1.1)
    python bump_version.py minor  # Increments the minor version (0.1.0 -> 0.2.0)
    python bump_version.py major  # Increments the major version (0.1.0 -> 1.0.0)
    python bump_version.py --set 0.2.0  # Sets version to 0.2.0
    python bump_version.py patch --commit  # Increments patch and creates commit
    python bump_version.py patch --tag  # Increments patch, commits and tags git repo
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def parse_version(version_str):
    """Parse version string into major, minor, patch components."""
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version_str)
    if not match:
        print(f"Error: Invalid version format: {version_str}")
        sys.exit(1)
    
    major, minor, patch = map(int, match.groups())
    return major, minor, patch


def increment_version(current_version, increment_type):
    """Increment version based on the specified type."""
    major, minor, patch = parse_version(current_version)
    
    if increment_type == "major":
        return f"{major + 1}.0.0"
    elif increment_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif increment_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        print(f"Error: Invalid increment type: {increment_type}")
        sys.exit(1)


def update_pyproject_toml(file_path, new_version):
    """Update version in pyproject.toml."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    updated_content = re.sub(
        r'version = "(\d+\.\d+\.\d+)"',
        f'version = "{new_version}"',
        content
    )
    
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    return updated_content != content


def update_user_agent(file_path, new_version):
    """Update User-Agent version in Python files."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Get major.minor part of the version (0.1.2 -> 0.1)
    version_prefix = ".".join(new_version.split(".")[:2])
    
    # Replace User-Agent version using string operations to avoid regex issues
    search_str = '"User-Agent": "HckrnewsClient/'
    if search_str in content:
        start_idx = content.find(search_str) + len(search_str)
        end_idx = content.find('"', start_idx)
        if start_idx > 0 and end_idx > start_idx:
            old_version = content[start_idx:end_idx]
            updated_content = content.replace(
                f'{search_str}{old_version}"', 
                f'{search_str}{version_prefix}"'
            )
            
            with open(file_path, 'w') as f:
                f.write(updated_content)
            
            return old_version != version_prefix
    
    return False


def get_current_version():
    """Extract current version from pyproject.toml."""
    pyproject_path = Path(__file__).parent / "pyproject.toml"
    
    if not pyproject_path.exists():
        print("Error: pyproject.toml not found")
        sys.exit(1)
        
    with open(pyproject_path, 'r') as f:
        content = f.read()
    
    match = re.search(r'version = "(\d+\.\d+\.\d+)"', content)
    if not match:
        print("Error: Could not find version in pyproject.toml")
        sys.exit(1)
        
    return match.group(1)


def create_git_commit(version, files_changed):
    """Create a git commit with the version bump changes."""
    if not files_changed:
        print("No files changed, skipping commit")
        return False
        
    try:
        # Add files to staging
        for file_path in files_changed:
            subprocess.run(
                ["git", "add", str(file_path)],
                check=True
            )
        
        # Create commit
        subprocess.run(
            ["git", "commit", "-m", f"chore: version bump to {version}"],
            check=True
        )
        print(f"Created git commit for version {version}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating git commit: {e}")
        return False


def create_git_tag(version):
    """Create a git tag for the given version."""
    tag_name = f"v{version}"
    try:
        # Check if tag already exists
        result = subprocess.run(
            ["git", "tag", "-l", tag_name],
            capture_output=True,
            text=True,
            check=True
        )
        
        if tag_name in result.stdout:
            print(f"Warning: Tag {tag_name} already exists")
            return False
            
        # Create tag
        subprocess.run(
            ["git", "tag", "-a", tag_name, "-m", f"Version {version}"],
            check=True
        )
        print(f"Created git tag: {tag_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating git tag: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Bump version numbers across the codebase")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("increment_type", nargs="?", choices=["major", "minor", "patch"],
                       help="Type of version increment")
    group.add_argument("--set", dest="set_version", 
                       help="Set specific version (format: X.Y.Z)")
    parser.add_argument("--commit", action="store_true",
                        help="Create a git commit for the version bump")
    parser.add_argument("--tag", action="store_true",
                        help="Create a git tag for the new version (implies --commit)")
    
    args = parser.parse_args()
    
    # --tag implies --commit
    if args.tag:
        args.commit = True
    
    # Get current version
    current_version = get_current_version()
    print(f"Current version: {current_version}")
    
    # Determine new version
    if args.set_version:
        try:
            parse_version(args.set_version)  # Validate format
            new_version = args.set_version
        except:
            print(f"Error: Invalid version format: {args.set_version}")
            sys.exit(1)
    else:
        new_version = increment_version(current_version, args.increment_type)
    
    print(f"New version: {new_version}")
    
    # Update files
    project_root = Path(__file__).parent
    files_updated = 0
    files_changed = []
    
    # Update pyproject.toml
    pyproject_path = project_root / "pyproject.toml"
    if update_pyproject_toml(pyproject_path, new_version):
        print(f"Updated version in {pyproject_path}")
        files_updated += 1
        files_changed.append(pyproject_path)
    else:
        print(f"No changes needed in {pyproject_path}")
    
    # Update scraper.py
    scraper_path = project_root / "hckrnews" / "scraper.py"
    if update_user_agent(scraper_path, new_version):
        print(f"Updated User-Agent in {scraper_path}")
        files_updated += 1
        files_changed.append(scraper_path)
    else:
        print(f"No changes needed in {scraper_path}")
    
    # Update api.py
    api_path = project_root / "hckrnews" / "api.py"
    if update_user_agent(api_path, new_version):
        print(f"Updated User-Agent in {api_path}")
        files_updated += 1
        files_changed.append(api_path)
    else:
        print(f"No changes needed in {api_path}")
    
    print(f"\nSummary: Updated {files_updated} file(s) to version {new_version}")
    
    # Create git commit if requested
    if args.commit:
        if create_git_commit(new_version, files_changed):
            # Create git tag if requested
            if args.tag:
                create_git_tag(new_version)
        elif args.tag:
            print("Skipping tag creation as commit failed")
    elif args.tag:
        print("Warning: --tag requires files to be committed first. Use --commit or run git commit manually.")
        print("Skipping tag creation.")


if __name__ == "__main__":
    main()