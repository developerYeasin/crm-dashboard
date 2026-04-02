#!/usr/bin/env python3
"""
QA Agent: performs quality assurance on frontend and backend.
Focus: Frontend first, then APIs.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent

class QAAgent(BaseAgent):
    """QA Agent for comprehensive frontend and API testing."""

    def __init__(self):
        super().__init__('qa', 'QA Agent')

    def check_frontend_linting(self) -> Dict[str, Any]:
        """Run frontend linting checks."""
        self.log("🔍 Starting Frontend QA...")

        results = {
            'linting': {'passed': False, 'issues': []},
            'build': {'passed': False, 'errors': []},
            'console_checks': {'passed': False, 'issues': []},
            'responsive_checks': {'passed': False, 'issues': []}
        }

        # Check if frontend directory exists
        if not self.frontend_dir.exists():
            results['linting']['issues'].append("Frontend directory not found")
            return results

        # Check for package.json and lint script
        package_json = self.frontend_dir / 'package.json'
        if not package_json.exists():
            results['linting']['issues'].append("package.json not found")
            return results

        try:
            import json
            with open(package_json) as f:
                pkg = json.load(f)

            scripts = pkg.get('scripts', {})

            # Run ESLint if available
            if 'lint' in scripts:
                self.log("Running: npm run lint")
                result = self.run_command(['npm', 'run', 'lint'], cwd=self.frontend_dir)
                if result.returncode == 0:
                    results['linting']['passed'] = True
                    self.log("✅ Linting passed")
                else:
                    results['linting']['passed'] = False
                    results['linting']['issues'].append(result.stderr[:500])
                    self.log("❌ Linting failed")
            else:
                results['linting']['issues'].append("No lint script in package.json")

            # Check build
            if 'build' in scripts:
                self.log("Running: npm run build")
                result = self.run_command(['npm', 'run', 'build'], cwd=self.frontend_dir)
                if result.returncode == 0:
                    results['build']['passed'] = True
                    self.log("✅ Build succeeded")
                else:
                    results['build']['passed'] = False
                    results['build']['errors'].append(result.stderr[:500])
                    self.log("❌ Build failed")
            else:
                results['build']['issues'].append("No build script in package.json")

            # Check for console.log statements
            self.log("Checking for console.log statements...")
            console_count = 0
            js_files = list(self.frontend_dir.rglob('*.js')) + list(self.frontend_dir.rglob('*.jsx'))
            for js_file in js_files:
                try:
                    content = js_file.read_text()
                    console_lines = [i+1 for i, line in enumerate(content.split('\n')) if 'console.' in line and not line.strip().startswith('//')]
                    if console_lines:
                        console_count += len(console_lines)
                        if console_count <= 10:  # Only log first few
                            self.log(f"Found console.* in {js_file.name}: lines {console_lines}")
                except:
                    pass

            if console_count > 0:
                results['console_checks']['passed'] = False
                results['console_checks']['issues'].append(f"Found {console_count} console.* statements")
                self.log(f"⚠️ Found {console_count} console.* statements")
            else:
                results['console_checks']['passed'] = True
                self.log("✅ No console.* statements found")

            # Check responsive design (presence of Tailwind responsive classes)
            self.log("Checking responsive design patterns...")
            responsive_classes = ['sm:', 'md:', 'lg:', 'xl:', '2xl:']
            responsive_found = False
            for js_file in js_files:
                try:
                    content = js_file.read_text()
                    if any(rc in content for rc in responsive_classes):
                        responsive_found = True
                        break
                except:
                    pass

            if responsive_found:
                results['responsive_checks']['passed'] = True
                self.log("✅ Responsive classes found")
            else:
                results['responsive_checks']['passed'] = False
                results['responsive_checks']['issues'].append("No responsive Tailwind classes found")
                self.log("⚠️ No responsive classes detected")

        except Exception as e:
            self.log(f"Frontend QA error: {e}", "ERROR")
            results['linting']['issues'].append(str(e))

        return results

    def check_backend_apis(self) -> Dict[str, Any]:
        """Test backend API endpoints."""
        self.log("🔍 Starting Backend API QA...")

        results = {
            'health': {'passed': False},
            'auth': {'passed': False},
            'endpoints_tested': 0,
            'endpoints_passed': 0,
            'slow_endpoints': [],
            'errors': []
        }

        # Get base URL from environment or default to current backend port
        base_url = os.getenv('CRM_BASE_URL', 'http://localhost:8091')
        auth_token = None

        # First, try to authenticate
        try:
            import requests
            self.log("Authenticating with backend...")
            login_data = {
                "email": "admin@example.com",
                "password": "admin123"
            }
            resp = requests.post(f"{base_url}/login", json=login_data, timeout=5)
            if resp.status_code == 200:
                auth_token = resp.json().get('token')
                results['auth']['passed'] = True
                self.log("✅ Authentication successful")
            else:
                results['errors'].append(f"Auth failed: {resp.status_code}")
                self.log(f"❌ Authentication failed: {resp.status_code}")
        except Exception as e:
            results['errors'].append(f"Auth error: {str(e)}")
            self.log(f"❌ Authentication error: {e}")

        # Test health endpoint (public)
        try:
            import requests
            self.log(f"Testing: GET {base_url}/health")
            resp = requests.get(f"{base_url}/health", timeout=5)
            if resp.status_code == 200:
                results['health']['passed'] = True
                self.log("✅ Health check passed")
            else:
                results['errors'].append(f"Health check returned {resp.status_code}")
                self.log(f"❌ Health check failed: {resp.status_code}")
        except requests.exceptions.ConnectionError:
            results['errors'].append("Cannot connect to backend API - is it running?")
            self.log("❌ Backend not responding (connection refused)")
        except Exception as e:
            results['errors'].append(f"Health check error: {str(e)}")
            self.log(f"❌ Health check error: {e}")

        # List of critical endpoints to test (CRM Dashboard specific)
        if results['health']['passed']:
            endpoints = [
                ('GET', '/tasks'),  # Task management
                ('GET', '/team'),  # Team members
                ('GET', '/notes'),  # Notes
                ('GET', '/kb'),  # Knowledge base
                ('GET', '/calendar'),  # Calendar
                ('GET', '/activity'),  # Activity log
                ('GET', '/scheduled'),  # Scheduled reminders
                ('GET', '/agents/status'),  # Agent status
                ('GET', '/api/ai/conversations'),  # AI conversations (requires auth)
            ]

            headers = {}
            if auth_token:
                headers['Authorization'] = f'Bearer {auth_token}'

            for method, path in endpoints:
                results['endpoints_tested'] += 1
                url = f"{base_url}{path}"
                try:
                    self.log(f"Testing: {method} {path}")
                    if method == 'GET':
                        resp = requests.get(url, headers=headers, timeout=10)
                    else:
                        continue

                    if resp.status_code < 400:
                        results['endpoints_passed'] += 1
                        self.log(f"✅ {method} {path} - {resp.status_code}")
                    else:
                        results['errors'].append(f"{method} {path} returned {resp.status_code}")
                        self.log(f"❌ {method} {path} - {resp.status_code}")

                    # Check response time
                    elapsed = resp.elapsed.total_seconds()
                    if elapsed > 2.0:
                        results['slow_endpoints'].append({'endpoint': path, 'time': elapsed})
                        self.log(f"⚠️ Slow endpoint: {path} took {elapsed:.2f}s")

                except requests.exceptions.RequestException as e:
                    results['errors'].append(f"{method} {path} request failed: {str(e)}")
                    self.log(f"❌ {method} {path} failed: {e}")

        return results

    def run(self) -> bool:
        """Execute all QA checks."""
        self.start()

        all_passed = True
        summary_parts = []

        try:
            # Frontend QA
            frontend_results = self.check_frontend_linting()
            frontend_issues = (
                len(frontend_results['linting']['issues']) +
                len(frontend_results['build']['errors']) +
                len(frontend_results['console_checks']['issues']) +
                len(frontend_results['responsive_checks']['issues'])
            )
            if frontend_issues == 0:
                summary_parts.append("Frontend: ✅ All checks passed")
            else:
                summary_parts.append(f"Frontend: ⚠️ {frontend_issues} issues found")
                all_passed = False

            # Backend API QA
            backend_results = self.check_backend_apis()
            backend_issues = len(backend_results['errors']) + len(backend_results['slow_endpoints'])
            if backend_issues == 0 and backend_results['health']['passed']:
                summary_parts.append("Backend: ✅ All checks passed")
            else:
                summary_parts.append(f"Backend: ⚠️ {backend_issues} issues found")
                all_passed = False

            summary = "\n".join(summary_parts)
            self.log(f"📊 QA Summary:\n{summary}")
            self.complete(success=all_passed, summary=summary)
            return all_passed

        except Exception as e:
            self.log(f"Fatal error in QA agent: {e}", "ERROR")
            self.complete(success=False, summary=f"Fatal error: {str(e)}")
            return False

if __name__ == "__main__":
    agent = QAAgent()
    success = agent.run()
    sys.exit(0 if success else 1)
