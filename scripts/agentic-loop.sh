#!/bin/bash
# Agentic Loop: Claude Code ↔ Gemini Bidirectional Collaboration
# Enables structured iteration: propose → review → iterate → converge

set -euo pipefail

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Directories
AGENTIC_DIR="${HOME}/.agentic"
AGENTIC_LOGS="${AGENTIC_DIR}/logs"
AGENTIC_HISTORY="${AGENTIC_DIR}/history"
SESSION_DIR="${AGENTIC_LOGS}/$(date +%Y%m%d-%H%M%S)"

# Create directories
mkdir -p "$AGENTIC_LOGS" "$AGENTIC_HISTORY" "$SESSION_DIR"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" | tee -a "${SESSION_DIR}/session.log"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*" | tee -a "${SESSION_DIR}/session.log"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $*" | tee -a "${SESSION_DIR}/session.log"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "${SESSION_DIR}/session.log"
}

log_proposal() {
    echo -e "${PURPLE}[PROPOSAL]${NC} $*" | tee -a "${SESSION_DIR}/session.log"
}

# Usage
usage() {
    cat << EOF
${BLUE}Agentic Loop: Claude Code ↔ Gemini Collaboration${NC}

Usage: $0 <action> [options]

Actions:
  ${GREEN}start${NC}            Start new agentic session
  ${GREEN}propose${NC}           Save Claude Code proposal for Gemini review
  ${GREEN}review${NC}            Get Gemini review of proposal
  ${GREEN}iterate${NC}           Show iteration history and next steps
  ${GREEN}converge${NC}          Final review and sign-off
  ${GREEN}status${NC}            Show current session status
  ${GREEN}history${NC}           List all past sessions

Options for 'propose':
  --task "task name"       Task name for this iteration
  --file <file>           File with proposed changes
  --description "text"    Description of proposal

Options for 'review':
  --aspect code|arch|test|perf   Aspect to review (default: all)
  --feedback-file <file>         Save feedback to file

Options for 'iterate':
  --show-proposal         Show previous proposal
  --show-feedback         Show previous feedback
  --next-action "action"  Suggested next action

Examples:
  # Step 1: Propose code
  $0 propose --task "refactor handler.py" --file handler.py

  # Step 2: Get Gemini review
  $0 review --aspect code

  # Step 3: See iteration history
  $0 iterate --show-feedback

  # Step 4: Final convergence
  $0 converge

EOF
}

# Initialize session
init_session() {
    local session_id=$(basename "$SESSION_DIR")
    cat > "${SESSION_DIR}/metadata.json" << EOF
{
  "session_id": "$session_id",
  "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "iterations": 0,
  "status": "active",
  "proposals": [],
  "reviews": [],
  "converged": false
}
EOF
    log_success "Agentic session started: $session_id"
    log_info "Session directory: $SESSION_DIR"
}

# Propose: Save Claude Code proposal
propose() {
    local task_name="${TASK_NAME:-unnamed}"
    local proposal_file="${PROPOSAL_FILE:-}"
    local description="${DESCRIPTION:-}"

    local proposal_id=$(date +%s)
    local proposal_dir="${SESSION_DIR}/proposal-${proposal_id}"
    mkdir -p "$proposal_dir"

    # Save proposal metadata
    cat > "${proposal_dir}/metadata.json" << EOF
{
  "proposal_id": "$proposal_id",
  "task": "$task_name",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "description": "$description"
}
EOF

    # Copy proposed files
    if [ -n "$proposal_file" ] && [ -f "$proposal_file" ]; then
        cp "$proposal_file" "${proposal_dir}/proposed.py"
        log_proposal "File: $(basename "$proposal_file")"
    fi

    # Save proposal text
    if [ -n "$description" ]; then
        echo "$description" > "${proposal_dir}/description.txt"
    fi

    log_success "Proposal saved: $proposal_id"
    echo "${proposal_dir}"

    # Increment iterations
    update_metadata "iterations" "$(($(get_metadata iterations) + 1))"
}

# Review: Call Gemini to review proposal
review() {
    local aspect="${REVIEW_ASPECT:-code}"
    local latest_proposal=$(get_latest_proposal)

    if [ -z "$latest_proposal" ]; then
        log_error "No proposal found. Run 'propose' first."
        return 1
    fi

    log_info "Reviewing proposal (aspect: $aspect)..."

    # Build Gemini prompt
    local prompt="Review this code proposal for $aspect quality:

Proposal Task: $(cat "${latest_proposal}/metadata.json" | grep '"task"' | cut -d'"' -f4)

Description:
$(cat "${latest_proposal}/description.txt" 2>/dev/null || echo "None provided")

Code:
\`\`\`python
$(cat "${latest_proposal}/proposed.py" 2>/dev/null || echo "N/A")
\`\`\`

Provide:
1. Strengths (what's good)
2. Issues (what needs fixing)
3. Improvement suggestions
4. Ready to implement? (yes/no)

Be concise but specific."

    # Call Gemini
    local review_id=$(date +%s)
    local review_dir="${SESSION_DIR}/review-${review_id}"
    mkdir -p "$review_dir"

    if ./scripts/gemini-ask.sh "$prompt" "code_review" > "${review_dir}/feedback.txt" 2>&1; then
        log_success "Review completed: $review_id"
        log_info "Feedback:"
        cat "${review_dir}/feedback.txt" | head -30
        echo "${review_dir}"
    else
        log_error "Gemini review failed"
        return 1
    fi
}

# Iterate: Show iteration history and suggestions
iterate() {
    local show_proposal="${SHOW_PROPOSAL:-false}"
    local show_feedback="${SHOW_FEEDBACK:-false}"

    local iteration_count=$(get_metadata iterations)
    log_info "Iteration count: $iteration_count"

    # List all proposals and reviews
    echo -e "\n${PURPLE}=== Iteration History ===${NC}"
    ls -1d "${SESSION_DIR}"/proposal-* 2>/dev/null | while read proposal; do
        local timestamp=$(stat -f %Sm -t "%Y-%m-%d %H:%M:%S" "$proposal" 2>/dev/null || echo "N/A")
        echo -e "${YELLOW}Proposal:${NC} $(basename "$proposal") [$timestamp]"

        if [ "$show_proposal" = "true" ]; then
            echo "Task: $(cat "$proposal/metadata.json" | grep '"task"' | cut -d'"' -f4)"
            echo "Description: $(cat "$proposal/description.txt" 2>/dev/null | head -1)"
        fi
    done

    ls -1d "${SESSION_DIR}"/review-* 2>/dev/null | while read review; do
        local timestamp=$(stat -f %Sm -t "%Y-%m-%d %H:%M:%S" "$review" 2>/dev/null || echo "N/A")
        echo -e "${GREEN}Review:${NC} $(basename "$review") [$timestamp]"

        if [ "$show_feedback" = "true" ]; then
            cat "$review/feedback.txt" | head -10
            echo "---"
        fi
    done

    # Suggestions
    if [ $iteration_count -eq 0 ]; then
        log_warning "No iterations yet. Start with: ./scripts/agentic-loop.sh propose --task 'your task'"
    elif [ $iteration_count -lt 3 ]; then
        log_info "Next: Get Gemini review: ./scripts/agentic-loop.sh review"
    else
        log_warning "Many iterations. Consider converging soon."
    fi
}

# Converge: Final review and sign-off
converge() {
    local latest_review=$(get_latest_review)

    if [ -z "$latest_review" ]; then
        log_error "No reviews found. Run 'review' first."
        return 1
    fi

    log_info "Convergence check..."

    # Final prompt to Gemini
    local prompt="Final convergence check for this proposal. Based on our iterations:

$(cat "${latest_review}/feedback.txt")

Should we converge and implement this code? Respond with:
- READY: Implementation can proceed
- NEEDS_WORK: List specific items
- BLOCKED: Explain why

Be direct and concise."

    local final_review="${SESSION_DIR}/final-review-$(date +%s)"
    mkdir -p "$final_review"

    if ./scripts/gemini-ask.sh "$prompt" "code_review" > "${final_review}/convergence.txt" 2>&1; then
        log_success "Convergence decision:"
        cat "${final_review}/convergence.txt"

        # Check decision
        if grep -qi "READY" "${final_review}/convergence.txt"; then
            log_success "✅ CONVERGED - Ready to implement"
            update_metadata "converged" "true"
            update_metadata "status" "ready"
        else
            log_warning "⚠️ MORE WORK NEEDED - Review feedback and iterate"
            update_metadata "status" "iterating"
        fi
    else
        log_error "Convergence check failed"
        return 1
    fi
}

# Status: Show current session state
status() {
    local session_id=$(basename "$SESSION_DIR")
    local metadata="${SESSION_DIR}/metadata.json"

    echo -e "\n${PURPLE}=== Session Status ===${NC}"
    echo "ID: $session_id"
    echo "Directory: $SESSION_DIR"

    if [ -f "$metadata" ]; then
        echo "Started: $(cat "$metadata" | grep started_at | cut -d'"' -f4)"
        echo "Iterations: $(cat "$metadata" | grep iterations | grep -o '[0-9]*' | tail -1)"
        echo "Status: $(cat "$metadata" | grep '"status"' | cut -d'"' -f4)"
        echo "Converged: $(cat "$metadata" | grep converged | cut -d':' -f2 | tr -d ' ,')"
    fi

    echo -e "\n${PURPLE}=== Available Files ===${NC}"
    find "$SESSION_DIR" -type f -name "*.json" -o -name "*.txt" -o -name "*.py" | sed "s|$SESSION_DIR/||" | sort
}

# History: List all sessions
history() {
    echo -e "\n${PURPLE}=== Agentic Session History ===${NC}"
    ls -1dt "${AGENTIC_LOGS}"/*/ 2>/dev/null | head -20 | while read session_dir; do
        local session_id=$(basename "$session_dir")
        local metadata="${session_dir}/metadata.json"
        if [ -f "$metadata" ]; then
            local started=$(cat "$metadata" | grep started_at | cut -d'"' -f4)
            local iterations=$(cat "$metadata" | grep iterations | grep -o '[0-9]*' | tail -1)
            local status=$(cat "$metadata" | grep '"status"' | cut -d'"' -f4)
            printf "%-20s Iterations: %-2s Status: %-10s Started: %s\n" \
                "$session_id" "$iterations" "$status" "$started"
        fi
    done
}

# Helper functions
get_metadata() {
    local key=$1
    if [ -f "${SESSION_DIR}/metadata.json" ]; then
        cat "${SESSION_DIR}/metadata.json" | grep "\"$key\"" | grep -o '[0-9]*\|true\|false' | head -1
    fi
}

update_metadata() {
    local key=$1
    local value=$2
    if [ -f "${SESSION_DIR}/metadata.json" ]; then
        # Simple JSON update (not bulletproof, but works for our use)
        sed -i '' "s/\"$key\": [^,}]*/\"$key\": \"$value\"/" "${SESSION_DIR}/metadata.json"
    fi
}

get_latest_proposal() {
    ls -1dt "${SESSION_DIR}"/proposal-*/ 2>/dev/null | head -1
}

get_latest_review() {
    ls -1dt "${SESSION_DIR}"/review-*/ 2>/dev/null | head -1
}

# Main
main() {
    if [ $# -eq 0 ]; then
        usage
        exit 0
    fi

    local action=$1
    shift || true

    # Parse options
    TASK_NAME=""
    PROPOSAL_FILE=""
    DESCRIPTION=""
    REVIEW_ASPECT="all"
    SHOW_PROPOSAL="false"
    SHOW_FEEDBACK="false"

    while [ $# -gt 0 ]; do
        case $1 in
            --task) TASK_NAME="$2"; shift 2 ;;
            --file) PROPOSAL_FILE="$2"; shift 2 ;;
            --description) DESCRIPTION="$2"; shift 2 ;;
            --aspect) REVIEW_ASPECT="$2"; shift 2 ;;
            --show-proposal) SHOW_PROPOSAL="true"; shift ;;
            --show-feedback) SHOW_FEEDBACK="true"; shift ;;
            *) shift ;;
        esac
    done

    # Initialize for new sessions (except 'history')
    if [ "$action" != "history" ]; then
        init_session
    fi

    # Execute action
    case $action in
        start)
            log_success "Session ready. Next step: propose or review"
            ;;
        propose)
            propose
            ;;
        review)
            review
            ;;
        iterate)
            iterate
            ;;
        converge)
            converge
            ;;
        status)
            status
            ;;
        history)
            history
            ;;
        *)
            log_error "Unknown action: $action"
            usage
            exit 1
            ;;
    esac
}

# Trap errors
trap 'log_error "Script failed at line $LINENO"' ERR

# Execute
main "$@"
