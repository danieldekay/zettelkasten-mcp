# Project Agents

This project uses **OpenSpec** for spec-driven development.

## OpenSpec Workflow

OpenSpec provides a structured approach to feature development with these phases:

1. **Explore** - Investigate and think through problems before building
2. **New** - Create a change container with a kebab-case name
3. **Proposal** - Capture WHY (problem/opportunity + what changes)
4. **Specs** - Define WHAT with testable WHEN/THEN/AND scenarios
5. **Design** - Decide HOW (technical approach, tradeoffs)
6. **Tasks** - Break into implementation checklist
7. **Apply** - Implement tasks, checking them off
8. **Archive** - Preserve the decision record

## Commands

| Command | Description |
|---------|-------------|
| `/opsx-explore` | Think through problems before committing to a direction |
| `/opsx-new` | Start a new change step-by-step |
| `/opsx-propose` | Create a change and generate all artifacts at once |
| `/opsx-continue` | Continue working on an existing change |
| `/opsx-apply` | Implement tasks from a change |
| `/opsx-archive` | Archive a completed change |
| `/opsx-verify` | Verify implementation matches artifacts |

## Skills

The OpenSpec skills are in `.claude/skills/openspec-*/SKILL.md`. Load them with the `skill` tool when working on OpenSpec tasks.

## Project Context

Tech stack: Python, MCP (Model Context Protocol), pytest
Domain: Zettelkasten note-taking system with MCP server
Conventions: Follow existing code patterns in `src/`
