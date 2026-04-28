#!/bin/bash
# AWS Guardian - Gemini CLI Integration Script
# This script allows Claude Code to ask Gemini CLI questions from within the project

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
WRAPPER_SCRIPT="$HOME/.gemini/claude_wrapper.sh"

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Check if wrapper exists
if [ ! -f "$WRAPPER_SCRIPT" ]; then
    echo -e "${RED}❌ Error: Claude-Gemini wrapper not found at $WRAPPER_SCRIPT${NC}"
    echo "Please run: $PROJECT_ROOT/scripts/setup-gemini.sh"
    exit 1
fi

# Show help
show_help() {
    cat << EOF
${BLUE}AWS Guardian - Gemini CLI Integration${NC}

Usage:
    ./scripts/gemini-ask.sh "<prompt>" [task_name]
    ./scripts/gemini-ask.sh --file <file> [task_name]
    ./scripts/gemini-ask.sh --help

Examples:
    # Ask Gemini to generate code
    ./scripts/gemini-ask.sh "Generate a Python function to check AWS EC2 status" "ec2_checker"

    # Ask from a file
    ./scripts/gemini-ask.sh --file prompts/code_review.txt "review_my_code"

    # Ask about the project
    ./scripts/gemini-ask.sh "Review the CLAUDE.md file and suggest improvements"

Available Tasks:
    - code_generation: Generate code snippets
    - code_review: Review and improve code
    - documentation: Generate documentation
    - troubleshooting: Help with debugging
    - architecture: Design system architecture
    - testing: Generate test cases

EOF
}

# Main execution
main() {
    if [ $# -eq 0 ] || [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
        show_help
        exit 0
    fi

    echo -e "${BLUE}🔗 Connecting to Gemini CLI...${NC}"
    echo ""

    # Pass all arguments to wrapper
    "$WRAPPER_SCRIPT" "$@"

    echo ""
    echo -e "${GREEN}✅ Gemini request completed${NC}"
}

# Run main function
main "$@"
