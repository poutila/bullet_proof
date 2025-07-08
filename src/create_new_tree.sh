#!/bin/bash

# create_new_tree.sh - Automate creation of multiple git worktrees for parallel development
# Usage: ./create_new_tree.sh <feature-name> <number-of-approaches>
# Example: ./create_new_tree.sh database 3

set -e  # Exit on any error

# Function to display usage
usage() {
    echo "Usage: $0 <feature-name> <number-of-approaches>"
    echo ""
    echo "Creates multiple git worktrees for parallel feature development"
    echo ""
    echo "Arguments:"
    echo "  feature-name          Name of the feature (e.g., 'database', 'auth', 'ui')"
    echo "  number-of-approaches  Number of parallel approaches to create (1-10)"
    echo ""
    echo "Examples:"
    echo "  $0 database 3         # Creates: feature-database-1, feature-database-2, feature-database-3"
    echo "  $0 auth 2             # Creates: feature-auth-1, feature-auth-2"
    echo ""
    echo "Directory structure created:"
    echo "  trees/"
    echo "  ├── database-1/"
    echo "  ├── database-2/"
    echo "  └── database-3/"
    exit 1
}

# Function to validate inputs
validate_inputs() {
    if [ $# -ne 2 ]; then
        echo "Error: Exactly 2 arguments required"
        usage
    fi

    if [ -z "$1" ]; then
        echo "Error: Feature name cannot be empty"
        usage
    fi

    if ! [[ "$2" =~ ^[0-9]+$ ]] || [ "$2" -lt 1 ] || [ "$2" -gt 10 ]; then
        echo "Error: Number of approaches must be between 1 and 10"
        usage
    fi

    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo "Error: Not in a git repository"
        exit 1
    fi
}

# Function to create trees directory if it doesn't exist
create_trees_dir() {
    if [ ! -d "trees" ]; then
        echo "Creating trees/ directory..."
        mkdir -p trees
    fi
}

# Function to check for existing worktrees
check_existing_worktrees() {
    local feature_name="$1"
    local num_approaches="$2"

    for i in $(seq 1 "$num_approaches"); do
        local branch_name="feature-${feature_name}-${i}"
        local dir_path="./trees/${feature_name}-${i}"

        # Check if branch already exists
        if git show-ref --verify --quiet "refs/heads/$branch_name"; then
            echo "Warning: Branch '$branch_name' already exists"
            read -p "Continue anyway? This will fail if the branch is checked out elsewhere. (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Aborted"
                exit 1
            fi
        fi

        # Check if directory already exists
        if [ -d "$dir_path" ]; then
            echo "Error: Directory '$dir_path' already exists"
            echo "Please remove it first or choose a different feature name"
            exit 1
        fi
    done
}

# Function to create worktrees
create_worktrees() {
    local feature_name="$1"
    local num_approaches="$2"

    echo "Creating $num_approaches worktrees for feature: $feature_name"
    echo "Base directory: $(pwd)/trees/"
    echo ""

    for i in $(seq 1 "$num_approaches"); do
        local branch_name="feature-${feature_name}-${i}"
        local dir_path="./trees/${feature_name}-${i}"

        echo "Creating worktree $i/$num_approaches:"
        echo "  Branch: $branch_name"
        echo "  Path: $dir_path"

        if git worktree add -b "$branch_name" "$dir_path"; then
            echo "  ✅ Created successfully"
        else
            echo "  ❌ Failed to create worktree"
            echo "  Cleaning up partial creation..."
            cleanup_on_failure "$feature_name" "$i"
            exit 1
        fi
        echo ""
    done
}

# Function to cleanup on failure
cleanup_on_failure() {
    local feature_name="$1"
    local failed_at="$2"

    # Remove any successfully created worktrees
    for i in $(seq 1 $((failed_at - 1))); do
        local branch_name="feature-${feature_name}-${i}"
        local dir_path="./trees/${feature_name}-${i}"

        if [ -d "$dir_path" ]; then
            echo "Removing: $dir_path"
            git worktree remove "$dir_path" 2>/dev/null || true
        fi

        if git show-ref --verify --quiet "refs/heads/$branch_name"; then
            echo "Removing branch: $branch_name"
            git branch -D "$branch_name" 2>/dev/null || true
        fi
    done
}

# Function to display success summary
display_summary() {
    local feature_name="$1"
    local num_approaches="$2"

    echo "🎉 Successfully created $num_approaches worktrees!"
    echo ""
    echo "Branches created:"
    for i in $(seq 1 "$num_approaches"); do
        echo "  • feature-${feature_name}-${i}"
    done
    echo ""
    echo "Directories created:"
    for i in $(seq 1 "$num_approaches"); do
        echo "  • trees/${feature_name}-${i}/"
    done
    echo ""
    echo "Next steps:"
    echo "  1. cd trees/${feature_name}-1"
    echo "  2. Start developing your first approach"
    echo "  3. Use 'cd ../${feature_name}-2' to switch to another approach"
    echo ""
    echo "Useful commands:"
    echo "  git worktree list                    # List all worktrees"
    echo "  git worktree remove <path>           # Remove a worktree"
    echo "  git branch -d feature-${feature_name}-X      # Delete branch after merge"
}

# Main function
main() {
    local feature_name="$1"
    local num_approaches="$2"

    echo "Git Worktree Creator"
    echo "==================="
    echo ""

    validate_inputs "$@"
    create_trees_dir
    check_existing_worktrees "$feature_name" "$num_approaches"
    create_worktrees "$feature_name" "$num_approaches"
    display_summary "$feature_name" "$num_approaches"
}

# Handle help flags
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    usage
fi

# Run main function with all arguments
main "$@"