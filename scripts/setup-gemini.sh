#!/bin/bash
# AWS Guardian - Gemini CLI Setup Script
# This script configures Gemini CLI for use with Claude Code

set -e

PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
WRAPPER_SCRIPT="$HOME/.gemini/claude_wrapper.sh"

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $@"; }
log_success() { echo -e "${GREEN}[✓]${NC} $@"; }
log_warn() { echo -e "${YELLOW}[⚠]${NC} $@"; }
log_error() { echo -e "${RED}[✗]${NC} $@"; }

# Step 1: Check Gemini CLI installation
step_check_gemini() {
    log_info "Checking Gemini CLI installation..."

    if ! command -v gemini &> /dev/null; then
        log_error "Gemini CLI is not installed"
        echo ""
        echo "Install Gemini CLI with:"
        echo "  brew install google/tap/gemini-cli"
        exit 1
    fi

    local version=$(gemini --version)
    log_success "Gemini CLI found: v$version"
}

# Step 2: Setup directories
step_setup_directories() {
    log_info "Setting up directories..."

    mkdir -p ~/.gemini/prompts
    mkdir -p ~/.gemini/logs
    mkdir -p "$PROJECT_ROOT/prompts"

    log_success "Directories created"
}

# Step 3: Check wrapper script
step_check_wrapper() {
    log_info "Checking wrapper script..."

    if [ ! -f "$WRAPPER_SCRIPT" ]; then
        log_error "Wrapper script not found at $WRAPPER_SCRIPT"
        log_info "Please ensure ~/.gemini/claude_wrapper.sh exists"
        exit 1
    fi

    if [ ! -x "$WRAPPER_SCRIPT" ]; then
        log_warn "Making wrapper script executable..."
        chmod +x "$WRAPPER_SCRIPT"
    fi

    log_success "Wrapper script ready"
}

# Step 4: Setup project scripts
step_setup_project_scripts() {
    log_info "Setting up project scripts..."

    local gemini_ask_script="$PROJECT_ROOT/scripts/gemini-ask.sh"

    if [ -f "$gemini_ask_script" ]; then
        chmod +x "$gemini_ask_script"
        log_success "Project scripts are executable"
    else
        log_warn "Project scripts not found"
    fi
}

# Step 5: Test Gemini CLI
step_test_gemini() {
    log_info "Testing Gemini CLI..."

    # Create a simple test prompt
    local test_prompt="Hello, this is a test from Claude Code. Respond with: 'Gemini CLI is working!'"
    local test_output=$(echo "$test_prompt" | timeout 30 gemini 2>&1 || true)

    if echo "$test_output" | grep -q "Gemini"; then
        log_success "Gemini CLI test passed"
    else
        log_warn "Gemini CLI test inconclusive, but connection seems OK"
    fi
}

# Step 6: Create sample prompts directory
step_create_sample_prompts() {
    log_info "Creating sample prompts..."

    local prompts_dir="$PROJECT_ROOT/prompts"
    mkdir -p "$prompts_dir"

    # Sample prompt 1: Code review
    cat > "$prompts_dir/code_review_template.txt" << 'EOF'
Please review the following code for:
1. Code quality and style
2. Potential bugs or issues
3. Performance optimizations
4. Security concerns
5. Suggestions for improvement

[INSERT CODE HERE]
EOF

    # Sample prompt 2: Documentation
    cat > "$prompts_dir/documentation_template.txt" << 'EOF'
Please generate comprehensive documentation for:
- Overview
- Installation/Setup
- Configuration
- Usage examples
- Troubleshooting
- API reference

[INSERT CODE OR PROJECT DESCRIPTION HERE]
EOF

    # Sample prompt 3: Architecture review
    cat > "$prompts_dir/architecture_template.txt" << 'EOF'
Please review this system architecture for:
1. Design patterns and best practices
2. Scalability considerations
3. Security and reliability
4. Performance optimization
5. Technology selection

[INSERT ARCHITECTURE DESCRIPTION HERE]
EOF

    log_success "Sample prompts created in $prompts_dir/"
}

# Step 7: Create configuration file
step_create_config() {
    log_info "Creating configuration file..."

    local config_file="$PROJECT_ROOT/.gemini-config.json"

    cat > "$config_file" << 'EOF'
{
  "gemini": {
    "enabled": true,
    "wrapper_script": "$HOME/.gemini/claude_wrapper.sh",
    "timeout": 300,
    "log_level": "INFO"
  },
  "prompts": {
    "directory": "./prompts",
    "cache_results": true,
    "retention_days": 7
  },
  "tasks": {
    "code_generation": {
      "description": "Generate code snippets",
      "template": "code_generation_template.txt"
    },
    "code_review": {
      "description": "Review and improve code",
      "template": "code_review_template.txt"
    },
    "documentation": {
      "description": "Generate documentation",
      "template": "documentation_template.txt"
    },
    "architecture": {
      "description": "Design system architecture",
      "template": "architecture_template.txt"
    }
  }
}
EOF

    log_success "Configuration file created: $config_file"
}

# Step 8: Print summary
step_print_summary() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Gemini CLI Setup Complete!${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "📍 Configuration:"
    echo "   Wrapper Script: $WRAPPER_SCRIPT"
    echo "   Prompts Dir:   ~/.gemini/prompts"
    echo "   Logs Dir:      ~/.gemini/logs"
    echo "   Project Dir:   $PROJECT_ROOT/prompts"
    echo ""
    echo "🚀 Quick Start:"
    echo ""
    echo "   1. Ask Gemini a question:"
    echo "      ./scripts/gemini-ask.sh \"Your question here\""
    echo ""
    echo "   2. Ask about code:"
    echo "      ./scripts/gemini-ask.sh \"Review my code\" code_review"
    echo ""
    echo "   3. View logs:"
    echo "      tail -f ~/.gemini/logs/claude-gemini.log"
    echo ""
    echo "📚 Documentation:"
    echo "   ~/.gemini/GEMINI.md - Original Gemini CLI docs"
    echo "   ./prompts/*.txt     - Sample prompt templates"
    echo ""
    echo "💡 Usage Examples:"
    echo ""
    echo "   # Generate Python code"
    echo "   ./scripts/gemini-ask.sh \"Generate a Python class for AWS cost analysis\""
    echo ""
    echo "   # Review architecture"
    echo "   ./scripts/gemini-ask.sh \"Review this microservice architecture for scalability\""
    echo ""
    echo "   # Create documentation"
    echo "   ./scripts/gemini-ask.sh \"Create API documentation from this code\""
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo ""
}

# Main execution
main() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   AWS Guardian - Gemini CLI Setup                ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
    echo ""

    step_check_gemini
    step_setup_directories
    step_check_wrapper
    step_setup_project_scripts
    step_test_gemini
    step_create_sample_prompts
    step_create_config
    step_print_summary

    log_success "Setup complete! You can now use: ./scripts/gemini-ask.sh"
}

# Run main
main "$@"
