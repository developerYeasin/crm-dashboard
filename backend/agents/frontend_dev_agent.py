#!/usr/bin/env python3
"""
Frontend Dev Agent: code review, UI/UX improvements, performance optimization.
"""
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent

class FrontendDevAgent(BaseAgent):
    """Frontend Development Agent for React codebase."""

    def __init__(self):
        super().__init__('frontend', 'Frontend Dev Agent')

    def review_jsx_files(self) -> Dict[str, Any]:
        """Review React JSX/JS files for common issues."""
        self.log("🔍 Performing Frontend Code Review...")

        results = {
            'files_reviewed': 0,
            'accessibility_issues': [],
            'performance_issues': [],
            'code_quality': [],
            'potential_bugs': []
        }

        js_files = list(self.frontend_dir.rglob('*.js')) + list(self.frontend_dir.rglob('*.jsx'))
        # Exclude node_modules
        js_files = [f for f in js_files if 'node_modules' not in str(f)]

        self.log(f"Found {len(js_files)} JavaScript files to review")

        for js_file in js_files:
            try:
                rel_path = js_file.relative_to(self.project_root)
                content = js_file.read_text()
                results['files_reviewed'] += 1

                lines = content.split('\n')

                # Check for accessibility
                for i, line in enumerate(lines, 1):
                    # Missing alt on img tags
                    if '<img' in line and 'alt=' not in line:
                        results['accessibility_issues'].append(f"{rel_path}:{i} - <img> missing alt attribute")

                    # Missing aria labels
                    if ('<button' in line or '<a' in line) and 'aria-label=' not in line:
                        if 'type=' in line or 'href=' in line:
                            pass  # Acceptable
                        else:
                            results['accessibility_issues'].append(f"{rel_path}:{i} - interactive element missing aria-label")

                    # onClick on div/span - should use button
                    if re.search(r'<div[^>]*onClick=', line):
                        results['accessibility_issues'].append(f"{rel_path}:{i} - <div> with onClick (use <button>)")

                    # Missing key in list items
                    if re.search(r'map\(.*key=', line):
                        pass  # Has key
                    elif 'map(' in line and '{' in line:
                        # Heuristic check - if map but no explicit key
                        if 'key=' not in content[content.find(line):content.find(line)+200]:
                            results['accessibility_issues'].append(f"{rel_path}:{i} - List rendering may be missing key prop")

                # Check for React performance anti-patterns
                if 'useEffect(' in content:
                    # check for missing dependencies
                    effect_count = content.count('useEffect(')
                    for match in re.finditer(r'useEffect\(\(\).*?\[(.*?)\]', content, re.DOTALL):
                        deps = match.group(1).strip()
                        if deps == '':
                            results['performance_issues'].append(f"{rel_path} - useEffect with empty dependency array may be intended")

                # Check for console statements
                console_count = sum(1 for line in lines if re.match(r'\s*console\.(log|warn|error)\(', line))
                if console_count > 0:
                    results['code_quality'].append(f"{rel_path} - {console_count} console.* statements found")

                # Check for large components (lines > 200)
                if len(lines) > 200:
                    results['code_quality'].append(f"{rel_path} - Component is large ({len(lines)} lines) - consider splitting")

                # Check for inline functions in render
                if re.search(r'<[A-Z][^>]*on\w+\s*=\s*{\(.*?\)\s*=>\s*{', content):
                    results['performance_issues'].append(f"{rel_path} - Inline arrow function in JSX (may cause unnecessary re-renders)")

                # Check for proper error boundaries (is there an ErrorBoundary component?)
                if 'ErrorBoundary' not in content and 'componentDidCatch' not in content:
                    # Only flag if component has complex logic
                    if 'useState' in content or 'useEffect' in content:
                        results['potential_bugs'].append(f"{rel_path} - Consider adding Error Boundary for error handling")

            except Exception as e:
                self.log(f"Error reviewing {js_file}: {e}", "ERROR")

        return results

    def check_build_and_lint(self) -> Dict[str, Any]:
        """Run frontend build and linting."""
        results = {
            'lint_passed': False,
            'build_passed': False,
            'lint_issues': [],
            'build_errors': []
        }

        if not self.frontend_dir.exists():
            results['lint_issues'].append("Frontend directory not found")
            return results

        package_json = self.frontend_dir / 'package.json'
        if not package_json.exists():
            results['lint_issues'].append("package.json not found")
            return results

        try:
            import json
            with open(package_json) as f:
                pkg = json.load(f)
            scripts = pkg.get('scripts', {})

            # Run lint
            if 'lint' in scripts:
                self.log("Running: npm run lint")
                result = self.run_command(['npm', 'run', 'lint'], cwd=self.frontend_dir)
                if result.returncode == 0:
                    results['lint_passed'] = True
                    self.log("✅ Linting passed")
                else:
                    results['lint_issues'].append(result.stderr[:1000])
                    self.log("❌ Linting failed")
            else:
                results['lint_issues'].append("No lint script defined")

            # Run build
            if 'build' in scripts:
                self.log("Running: npm run build")
                result = self.run_command(['npm', 'run', 'build'], cwd=self.frontend_dir)
                if result.returncode == 0:
                    results['build_passed'] = True
                    self.log("✅ Build succeeded")
                else:
                    results['build_errors'].append(result.stderr[:1000])
                    self.log("❌ Build failed")
            else:
                results['build_errors'].append("No build script defined")

        except Exception as e:
            self.log(f"Build/lint error: {e}", "ERROR")
            results['build_errors'].append(str(e))

        return results

    def check_responsive_design(self) -> Dict[str, Any]:
        """Check for responsive design patterns."""
        self.log("📱 Checking responsive design...")

        results = {
            'responsive_components': 0,
            'mobile_first': False,
            'breakpoints_used': set(),
            'issues': []
        }

        tailwind_config = self.frontend_dir / 'tailwind.config.js'
        if tailwind_config.exists():
            config_content = tailwind_config.read_text()
            if 'mobile-first' in config_content.lower():
                results['mobile_first'] = True
                self.log("✅ Tailwind configured for mobile-first")

        JSX_files = list(self.frontend_dir.rglob('*.jsx')) + list(self.frontend_dir.rglob('*.js'))
        JSX_files = [f for f in JSX_files if 'node_modules' not in str(f)]

        responsive_classes = {
            'sm:': 'small',
            'md:': 'medium',
            'lg:': 'large',
            'xl:': 'extra-large',
            '2xl:': '2x'
        }

        for js_file in JSX_files[:20]:  # Sample first 20
            try:
                content = js_file.read_text()
                file_responsive = [rc for rc in responsive_classes if rc in content]
                if file_responsive:
                    results['responsive_components'] += 1
                    for rc in file_responsive:
                        results['breakpoints_used'].add(responsive_classes[rc])
            except:
                pass

        self.log(f"Found {results['responsive_components']} files using responsive classes")
        self.log(f"Breakpoints: {', '.join(results['breakpoints_used'])}")

        if results['responsive_components'] == 0:
            results['issues'].append("No responsive design patterns detected")

        results['breakpoints_used'] = list(results['breakpoints_used'])
        return results

    def generate_suggestions(self, review: Dict[str, Any], build_results: Dict[str, Any]) -> List[str]:
        """Generate actionable suggestions."""
        suggestions = []

        if not build_results['lint_passed']:
            suggestions.append("Fix linting errors to maintain code quality")

        if not build_results['build_passed']:
            suggestions.append("Resolve build errors before deploying")

        if len(review['accessibility_issues']) > 0:
            suggestions.append(f"Address {len(review['accessibility_issues'])} accessibility issues (alt attributes, aria-labels)")

        if review['performance_issues']:
            suggestions.append("Optimize performance: remove inline functions, use useMemo/useCallback for expensive computations")

        if len(review['code_quality']) > 5:
            suggestions.append("Consider code splitting and component refactoring to improve maintainability")

        return suggestions

    def run(self) -> bool:
        """Execute frontend development tasks."""
        self.start()

        success = True
        summary_parts = []

        try:
            # Code review
            review = self.review_jsx_files()
            self.log(f"Reviewed {review['files_reviewed']} JavaScript files")

            summary_parts.append(f"Files reviewed: {review['files_reviewed']}")
            summary_parts.append(f"Accessibility issues: {len(review['accessibility_issues'])}")
            summary_parts.append(f"Performance issues: {len(review['performance_issues'])}")
            summary_parts.append(f"Quality notes: {len(review['code_quality'])}")

            for issue in review['accessibility_issues'][:5]:
                self.log(f"♿ A11y: {issue}")

            for issue in review['performance_issues'][:5]:
                self.log(f"⚡ Perf: {issue}")

            # Build & lint
            build_results = self.check_build_and_lint()
            if not build_results['lint_passed']:
                success = False
            if not build_results['build_passed']:
                success = False

            # Responsive design
            responsive = self.check_responsive_design()
            if responsive['issues']:
                summary_parts.append(f"Responsive: {len(responsive['issues'])} issues")

            # Generate suggestions
            suggestions = self.generate_suggestions(review, build_results)
            if suggestions:
                summary_parts.append("Suggestions:")
                for sug in suggestions:
                    summary_parts.append(f"  • {sug}")

            summary = "\n".join(summary_parts)
            self.complete(success=success, summary=summary)
            return success

        except Exception as e:
            self.log(f"Fatal error in Frontend Dev agent: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            self.complete(success=False, summary=f"Fatal error: {str(e)}")
            return False

if __name__ == "__main__":
    agent = FrontendDevAgent()
    success = agent.run()
    import sys
    sys.exit(0 if success else 1)
