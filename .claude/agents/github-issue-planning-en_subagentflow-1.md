---
name: github-issue-planning-en_subagentflow-1
description: subagentflow-1
model: sonnet
memory: user
---
```mermaid
flowchart TD
    start-1778149239463([Start])
    end_1778149239464([End])
    prompt-1778149435380[Enter your prompt here.]
    prompt-1778149743286[Enter your prompt here.]
    prompt-1778149783660[Enter your prompt here.]

```

## Workflow Execution Guide

Follow the Mermaid flowchart above to execute the workflow. Each node type has specific execution methods as described below.

### Execution Methods by Node Type

- **Rectangle nodes (Sub-Agent: ...)**: Execute Sub-Agents
- **Diamond nodes (AskUserQuestion:...)**: Use the AskUserQuestion tool to prompt the user and branch based on their response
- **Diamond nodes (Branch/Switch:...)**: Automatically branch based on the results of previous processing (see details section)
- **Rectangle nodes (Prompt nodes)**: Execute the prompts described in the details section below

### Prompt Node Details

#### prompt-1778149435380(Enter your prompt here.)

```
Enter your prompt here.

You can use variables like {{variableName}}.
```

#### prompt-1778149743286(Enter your prompt here.)

```
Enter your prompt here.

You can use variables like {{variableName}}.
```

#### prompt-1778149783660(Enter your prompt here.)

```
Enter your prompt here.

You can use variables like {{variableName}}.
```
