---
title: "Zoyd"
date: 2024-12-15
draft: false
description: "An autonomous PRD-driven development agent that iterates through tasks until completion."
tags: ["Python", "AI", "Automation", "Developer Tools", "Agentic Systems"]
showHero: false
showTableOfContents: true
---

{{< lead >}}
Zoyd is an autonomous development agent that reads a Product Requirements Document, invokes Claude Code to complete tasks, and iterates until all checkboxes are marked complete. Set it running and watch your PRD become reality.
{{< /lead >}}

## Features

{{< keywordList >}}
{{< keyword icon="document" >}} PRD Parsing {{< /keyword >}}
{{< keyword icon="chart" >}} Progress Tracking {{< /keyword >}}
{{< keyword icon="refresh" >}} Autonomous Loop {{< /keyword >}}
{{< /keywordList >}}

---

## What it does

{{< timeline >}}

{{< timelineItem icon="search" header="Task Detection" subheader="Markdown Parsing" >}}
Parses PRD files to find checkbox tasks (`- [ ]` / `- [x]`), tracking completion status and line numbers for precise updates.
{{< /timelineItem >}}

{{< timelineItem icon="code" header="Claude Integration" subheader="AI-Powered Development" >}}
Invokes Claude Code with the PRD context and progress history, enabling intelligent task completion with full codebase access.
{{< /timelineItem >}}

{{< timelineItem icon="refresh" header="Iteration Management" subheader="Until Complete" >}}
Tracks iterations, handles failures gracefully, and continues looping until all tasks are complete or limits are reached.
{{< /timelineItem >}}

{{< /timeline >}}

---

## Architecture

{{< mermaid >}}
graph TD
    A["PRD.md"]

    A --> B["Task Parser"]
    B --> C["Loop Runner"]
    C --> D["Claude Code"]
    D --> E["Progress Log"]
    E --> B

    C --> F["Auto Commit"]
    F --> G["Git Repository"]
{{< /mermaid >}}

---

## Highlights

{{< alert icon="fire" >}}
**Truly autonomous** - Point Zoyd at a PRD and walk away. It will invoke Claude Code repeatedly, tracking progress and committing changes until every task is complete.
{{< /alert >}}

- Configurable iteration limits and cost budgets
- Automatic git commits after each completed task
- Rich TUI with live progress tracking and spinners
- Fail-fast mode for CI/CD integration
- JSON output for machine-readable status

---

## Tech Stack

{{< keywordList >}}
{{< keyword icon="code" >}} Python {{< /keyword >}}
{{< keyword icon="code" >}} Claude Code {{< /keyword >}}
{{< keyword icon="code" >}} Markdown {{< /keyword >}}
{{< /keywordList >}}
