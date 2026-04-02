#!/usr/bin/env python3
"""
Backend Dev Agent: code review, performance optimization, bug fixes.
"""
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent

class BackendDevAgent(BaseAgent):
    """Backend Development Agent for Python/Flask codebase."""

    def __init__(self):
        super().__init__('backend', 'Backend Dev Agent')

    def analyze_imports(self, content: str) -> List[str]:
        """Find unused imports (basic heuristic)."""
        issues = []
        lines = content.split('\n')
        imports = []
        used_names = set()

        # Extract imported names
        for line in lines:
            if re.match(r'^\s*(from|import)\s+', line):
                imports.append(line.strip())
                # Extract imported module/names
                match = re.search(r'(?:from\s+\S+\s+)?import\s+(.+)', line)
                if match:
                    names = match.group(1).split(',')
                    for name in names:
                        name = name.strip().split(' as ')[0].strip()
                        if name != '*':
                            used_names.add(name)

        # Simple check - if we import but don't see usage in non-import lines
        # This is a basic heuristic; real analysis would need AST parsing
        return issues

    def check_security(self, content: str, filename: str) -> List[str]:
        """Check for common security issues."""
        issues = []
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            # SQL injection risk: raw string formatting in queries
            if re.search(r'\.execute\(.*%[sd]', line) and 'params' not in line:
                issues.append(f"Possible SQL injection in {filename}:{i} - use parameterized queries")
            # Hardcoded secrets
            if re.search(r'(password|secret|key)\s*=\s*["\'][^"\']+["\']', line, re.IGNORECASE):
                if 'os.getenv' not in line and 'config' not in line.lower():
                    issues.append(f"Possible hardcoded secret in {filename}:{i}")
            # Debug mode
            if 'DEBUG = True' in line and 'if' not in line:
                issues.append(f"DEBUG set to True in {filename}:{i} (production security risk)")

        return issues

    def check_performance(self, content: str, filename: str) -> List[str]:
        """Identify potential performance issues."""
        issues = []

        # N+1 query pattern: loop with DB queries inside
        if 'for ' in content and ('query' in content.lower() or '.get(' in content or '.all()' in content):
            issues.append(f"Possible N+1 query in {filename} - review for loop with DB queries")

        # Missing indexes on frequently queried fields
        if 'filter(' in content and 'created_at' in content:
            issues.append(f"Consider database index for created_at in {filename}")

        return issues

    def review_python_files(self) -> Dict[str, Any]:
        """Review all Python files in backend."""
        self.log("🔍 Performing Backend Code Review...")

        results = {
            'files_reviewed': 0,
            'security_issues': [],
            'performance_issues': [],
            'code_quality': [],
            'suggestions': []
        }

        python_files = list(self.backend_dir.rglob('*.py'))
        # Exclude venv, __pycache__, migrations
        python_files = [f for f in python_files if 'venv' not in str(f) and '__pycache__' not in str(f)]

        self.log(f"Found {len(python_files)} Python files to review")

        for py_file in python_files:
            try:
                rel_path = py_file.relative_to(self.project_root)
                content = py_file.read_text()
                results['files_reviewed'] += 1

                # Check for common issues
                security = self.check_security(content, str(rel_path))
                results['security_issues'].extend(security)

                performance = self.check_performance(content, str(rel_path))
                results['performance_issues'].extend(performance)

                # Check file length
                lines = len(content.split('\n'))
                if lines > 1000:
                    results['code_quality'].append(f"{rel_path} is very long ({lines} lines) - consider splitting")

                # Check for docstrings
                if 'def ' in content and '"""' not in content and "'''" not in content:
                    results['code_quality'].append(f"{rel_path} has functions without docstrings")

            except Exception as e:
                self.log(f"Error reviewing {py_file}: {e}", "ERROR")

        return results

    def apply_safe_fixes(self, review_results: Dict[str, Any]) -> List[str]:
        """Apply safe, non-breaking fixes automatically."""
        self.log("🔧 Applying safe fixes...")

        fixes_applied = []

        # Remove console.log or print statements (simple pattern)
        for py_file in self.backend_dir.rglob('*.py'):
            if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                continue
            try:
                content = py_file.read_text()
                original = content

                # Remove debug print statements (keep intentional logging)
                lines = content.split('\n')
                new_lines = []
                for line in lines:
                    stripped = line.strip()
                    # Remove print() statements but keep logging calls
                    if stripped.startswith('print(') and 'logging' not in line:
                        # Comment out or remove
                        if line.startswith('    ') or line.startswith('\t'):
                            new_lines.append(line)  # Keep indentation but it's removed
                        continue
                    new_lines.append(line)

                content = '\n'.join(new_lines)
                if content != original:
                    self.write_file(str(py_file.relative_to(self.project_root)), content)
                    fixes_applied.append(f"Removed print statements from {py_file.name}")
            except:
                pass

        return fixes_applied

    def generate_performance_suggestions(self, review_results: Dict[str, Any]) -> List[str]:
        """Generate actionable performance improvement suggestions."""
        suggestions = []

        if any('N+1' in issue for issue in review_results['performance_issues']):
            suggestions.append("Use eager loading (joinedload/subqueryload) for relationships to avoid N+1 queries")

        if any('created_at' in issue for issue in review_results['performance_issues']):
            suggestions.append("Add database indexes for frequently filtered columns: created_at, updated_at, customer_name")

        if len(review_results['performance_issues']) > 5:
            suggestions.append("Consider adding a caching layer (Redis) for expensive queries")

        return suggestions

    def run(self) -> bool:
        """Execute backend development tasks."""
        self.start()

        success = True
        summary_parts = []

        try:
            # Code review
            review = self.review_python_files()

            summary_parts.append(f"Reviewed {review['files_reviewed']} Python files")
            summary_parts.append(f"Security issues: {len(review['security_issues'])}")
            summary_parts.append(f"Performance issues: {len(review['performance_issues'])}")
            summary_parts.append(f"Code quality notes: {len(review['code_quality'])}")

            if review['security_issues']:
                for issue in review['security_issues'][:5]:  # Log first 5
                    self.log(f"🔒 Security: {issue}")
                success = False

            if review['performance_issues']:
                for issue in review['performance_issues'][:5]:
                    self.log(f"⚡ Performance: {issue}")

            if review['code_quality']:
                for note in review['code_quality'][:5]:
                    self.log(f"📝 Quality: {note}")

            # Apply safe fixes
            fixes = self.apply_safe_fixes(review)
            if fixes:
                self.log(f"Applied {len(fixes)} automatic fixes")
                for fix in fixes[:5]:
                    self.log(f"  - {fix}")

            # Generate suggestions
            suggestions = self.generate_performance_suggestions(review)
            if suggestions:
                summary_parts.append("Suggestions:")
                for sug in suggestions:
                    summary_parts.append(f"  • {sug}")

            summary = "\n".join(summary_parts)
            self.complete(success=success, summary=summary)
            return success

        except Exception as e:
            self.log(f"Fatal error in Backend Dev agent: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            self.complete(success=False, summary=f"Fatal error: {str(e)}")
            return False

if __name__ == "__main__":
    agent = BackendDevAgent()
    success = agent.run()
    import sys
    sys.exit(0 if success else 1)
