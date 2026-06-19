#!/usr/bin/env python3
"""
Script to automatically fetch the latest payload links from GitHub releases
and update payloads.json with the latest versions.
"""

import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class PayloadUpdater:
    def __init__(self, payloads_file: str = "payloads.json"):
        self.payloads_file = Path(payloads_file)
        self.payloads_data = self.load_payloads()
        
    def load_payloads(self) -> Dict:
        """Load existing payloads.json file"""
        if self.payloads_file.exists():
            with open(self.payloads_file, 'r') as f:
                return json.load(f)
        return {"name": "Custom Payloads", "payloads": []}
    
    def save_payloads(self) -> None:
        """Save updated payloads to file"""
        with open(self.payloads_file, 'w') as f:
            json.dump(self.payloads_data, f, indent=2)
    
    @staticmethod
    def get_latest_release(owner: str, repo: str, allow_prerelease: bool = True) -> Optional[Dict]:
        """
        Fetch the latest release from a GitHub repository
        
        Args:
            owner: Repository owner
            repo: Repository name
            allow_prerelease: Whether to include pre-releases
            
        Returns:
            Dictionary with release info or None if not found
        """
        try:
            if allow_prerelease:
                url = f"https://api.github.com/repos/{owner}/{repo}/releases"
            else:
                url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
            
            headers = {"Accept": "application/vnd.github.v3+json"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            releases = response.json() if isinstance(response.json(), list) else [response.json()]
            
            # Filter out draft releases
            releases = [r for r in releases if not r.get('draft', False)]
            
            if not releases:
                return None
            
            release = releases[0]  # Latest release
            
            # Find the .elf file
            elf_asset = None
            for asset in release.get('assets', []):
                if asset['name'].endswith('.elf'):
                    elf_asset = asset
                    break
            
            if not elf_asset:
                print(f"⚠️  No .elf file found in {owner}/{repo} release {release['tag_name']}")
                return None
            
            return {
                'tag': release['tag_name'],
                'filename': elf_asset['name'],
                'url': elf_asset['browser_download_url'],
                'published_at': release['published_at'],
            }
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching {owner}/{repo}: {e}")
            return None
    
    def update_payload(self, payload: Dict) -> bool:
        """
        Update a single payload with the latest release info
        
        Returns:
            True if updated, False otherwise
        """
        source = payload.get('source', '')
        
        # Parse owner/repo from source URL
        # Expected format: https://github.com/owner/repo/releases
        if 'github.com' not in source:
            print(f"⚠️  Skipping {payload['name']}: unsupported source")
            return False
        
        try:
            parts = source.replace('https://github.com/', '').split('/releases')[0].split('/')
            if len(parts) != 2:
                print(f"⚠️  Skipping {payload['name']}: invalid source format")
                return False
            
            owner, repo = parts
            allow_prerelease = payload.get('allow_prerelease', False)
            
            print(f"🔍 Checking {owner}/{repo}...")
            
            latest = self.get_latest_release(owner, repo, allow_prerelease)
            if not latest:
                print(f"⚠️  No release found for {owner}/{repo}")
                return False
            
            old_version = payload.get('version', 'unknown')
            old_url = payload.get('url', '')
            
            # Check if update is needed
            if old_version == latest['tag'] and old_url == latest['url']:
                print(f"✓ {payload['name']}: already up-to-date ({old_version})")
                return False
            
            # Update the payload
            payload['url'] = latest['url']
            payload['source_direct'] = latest['url']
            payload['filename'] = latest['filename']
            payload['version'] = latest['tag']
            payload['last_update'] = latest['published_at'][:10]  # YYYY-MM-DD format
            
            print(f"✅ {payload['name']}: updated from {old_version} to {latest['tag']}")
            return True
        
        except Exception as e:
            print(f"❌ Error updating {payload['name']}: {e}")
            return False
    
    def update_all(self) -> None:
        """Update all payloads"""
        print("=" * 60)
        print("🚀 Starting payload update process")
        print("=" * 60)
        
        payloads = self.payloads_data.get('payloads', [])
        updated_count = 0
        
        for payload in payloads:
            if self.update_payload(payload):
                updated_count += 1
        
        print("=" * 60)
        print(f"📊 Summary: {updated_count}/{len(payloads)} payloads updated")
        print("=" * 60)
        
        self.save_payloads()
        print("💾 Changes saved to payloads.json")


def main():
    """Main entry point"""
    updater = PayloadUpdater()
    updater.update_all()


if __name__ == "__main__":
    main()
