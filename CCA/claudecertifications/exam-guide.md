<!-- source: https://claudecertifications.com/claude-certified-architect/exam-guide -->

# Claude Certified Architect – Foundations Exam Guide

## Exam Overview

**Certification Name:** Claude Certified Architect – Foundations

**Issued By:** Anthropic

**Exam Format:** Multiple choice, scenario-based

**Passing Score:** 720 / 1000

**Scenarios:** 4 of 6 scenarios randomly selected

**Target Audience:** Solution architects building production applications with Claude

**Cost:** Free for first 5,000 partner company employees

**Availability:** Available now for Anthropic partners

### Registration

Access the exam through Anthropic's official Skilljar portal at https://anthropic.skilljar.com/claude-certified-architect-foundations-access-request

---

## 5 Exam Domains

### Domain 1: Agentic Architecture & Orchestration (~25%)

Covers designing and implementing agentic systems using Claude's Agent SDK, including agentic loops, multi-agent orchestration, hooks, workflows, session management, and task decomposition patterns.

### Domain 2: Tool Design & MCP Integration (~20%)

Focuses on designing effective tools and integrating with Model Context Protocol servers, including tool descriptions, error responses, tool distribution, MCP configuration, and Claude's built-in tools.

### Domain 3: Claude Code Configuration & Workflows (~20%)

Addresses configuring Claude Code for development workflows, covering CLAUDE.md hierarchy, custom commands and skills, plan mode, iterative refinement, CI/CD integration, and batch processing.

### Domain 4: Prompt Engineering & Structured Output (~20%)

Emphasizes prompt engineering techniques for production systems, including explicit criteria, few-shot prompting, tool_use for structured output, JSON schema design, validation-retry loops, and multi-pass review strategies.

### Domain 5: Context Management & Reliability (~15%)

Covers managing context effectively in production systems, addressing progressive summarization risks, context positioning, escalation patterns, error propagation, context degradation, human review, and information provenance.

---

## 6 Exam Scenarios

You'll encounter 4 randomly selected from these 6 scenarios:

### 1. Customer Support Resolution Agent

Design an AI-powered customer support agent handling inquiries, issue resolution, and escalation. Tests Agent SDK implementation, escalation pattern design, hook-based compliance enforcement, and structured error handling.

### 2. Code Generation with Claude Code

Configure Claude Code for development team workflows. Tests CLAUDE.md hierarchy setup, plan mode versus direct execution, custom slash commands and skills, and TDD iteration patterns.

### 3. Multi-Agent Research System

Build a coordinator-subagent system for parallel research tasks. Tests hub-and-spoke architecture, context isolation and passing, error propagation patterns, and information provenance.

### 4. Developer Productivity with Claude

Create developer tools using the Claude Agent SDK with built-in tools and MCP servers. Tests built-in tool selection, MCP server integration, codebase exploration strategies, and tool distribution.

### 5. Claude Code for CI/CD

Integrate Claude Code into continuous integration and delivery pipelines. Tests -p flag usage, structured output with --output-format json, Batch API integration, and session isolation.

### 6. Structured Data Extraction

Build a structured data extraction pipeline from unstructured documents. Tests JSON schema design, validation-retry loop implementation, few-shot prompting for consistency, and field-level confidence with human review.

---

## Key Anti-Patterns (Common Wrong Answers)

| Anti-Pattern | Better Approach |
|---|---|
| Parsing natural language for loop termination | Check stop_reason ('tool_use' vs 'end_turn') |
| Arbitrary iteration caps as primary stopping | Let the agentic loop terminate naturally via stop_reason |
| Prompt-based enforcement for critical business rules | Use programmatic hooks for deterministic enforcement |
| Self-reported confidence scores for escalation | Use structured criteria and programmatic checks |
| Sentiment-based escalation | Escalate based on task complexity and policy gaps |
| Generic error messages ('Operation failed') | Include isError, errorCategory, isRetryable, and context |
| Silently suppressing errors | Distinguish access failures from genuinely empty results |
| Too many tools per agent (18+) | Keep to 4-5 tools per agent for optimal selection |
| Same-session self-review | Use separate sessions to avoid reasoning context bias |
| Aggregate accuracy metrics only | Track accuracy per document type to catch masked failures |

---

## Official Resources

- **12-Week Study Plan:** Structured week-by-week preparation covering all 5 domains
- **Anti-Patterns Cheatsheet:** 18 common wrong answers with severity ratings
- **Scenario Walkthroughs:** Deep dive into all 6 architectural scenarios
