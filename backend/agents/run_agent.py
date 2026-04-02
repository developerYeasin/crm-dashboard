#!/usr/bin/env python3
"""
CLI entry point for running individual agents.
Usage: python run_agent.py --type qa|backend|frontend
"""
import argparse
import sys
from pathlib import Path

# Add project root
ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from agents.qa_agent import QAAgent
from agents.backend_dev_agent import BackendDevAgent
from agents.frontend_dev_agent import FrontendDevAgent

def main():
    parser = argparse.ArgumentParser(description="Run an AI agent for order-tracker")
    parser.add_argument('--type', choices=['qa', 'backend', 'frontend'], required=True,
                        help='Type of agent to run')
    args = parser.parse_args()

    agent_map = {
        'qa': QAAgent,
        'backend': BackendDevAgent,
        'frontend': FrontendDevAgent
    }

    agent_class = agent_map.get(args.type)
    if not agent_class:
        print(f"Unknown agent type: {args.type}")
        sys.exit(1)

    agent = agent_class()
    success = agent.run()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
