# We Hired an AI Junior DevOps

Someone in the company sends a message: "I need a Kafka UI STG with URL kafka-ui.stg.example.com." Five minutes later, two pull requests appear: one with Helm values and ingress config, and one with a Route53 record in Terraform. No engineer opened their IDE. No one hand-edited YAML or HCL.

This is our AI Junior DevOps at work. And the surprising thing isn't that it works — it's *why* it works. The answer has almost nothing to do with AI.

## The Real Problem Isn't Intelligence — It's Workflow

Every DevOps team deals with the same grind: a steady stream of well-defined infrastructure requests. Add an ingress rule. Deploy a new service to the staging cluster. Update Helm values. Create a DNS record in Route53.

These tasks share a pattern. The inputs are clear (resource type, environment, parameters). The outputs are clear (Terraform code or Kubernetes manifests). The process is clear (write the code, open a PR, review, merge). There's very little ambiguity.

And yet, each one still requires an engineer to context-switch out of deeper work, write boilerplate code, and push a PR. It's not hard work. It's *interruptive* work — and it adds up to hours per week across the team.

The instinct is to throw AI at this: give an LLM access to your cloud APIs and let it generate infrastructure. But that's starting from the wrong end.

Here's what we learned: **AI doesn't fix a broken workflow. It amplifies whatever workflow you already have.** If your process is messy — requests coming through five different channels, no standard format, tribal knowledge about where things live — AI will amplify that mess. If your process is structured, AI will amplify that structure.

The job isn't to build a smart AI. The job is to build a workflow so clear that even a dumb AI can follow it.

## Our Design and Implementation

Our handoff chain is simple:

```
Slack -> AI PM (OpenClaw) -> Jira Ticket -> GitHub Copilot
```

Each hop has one responsibility:

1. **Slack** is the intake layer. People ask for changes in natural language.
2. **AI PM (OpenClaw)** triages the request, enriches context, and turns it into a structured work item.
3. **Jira ticket** is the contract artifact. It stores the explicit fields the downstream coding agent needs.
4. **GitHub Copilot** picks up the ticket context and generates the implementation PRs.

This design keeps routing logic in one place, keeps context in a durable ticket, and keeps code generation deterministic.

**Why Jira?** When I first built this chain, it didn't automate anything. OpenClaw just managed the Jira board — triaging requests, writing structured tickets, assigning work to the right person on my team. It was an AI project manager, nothing more. But something clicked once every request had a clean, structured ticket sitting in the backlog. I looked at the queue and thought: half of these are the same kind of infra change, over and over. If the ticket already spells out the repo, the resource type, and the parameters — why is a human still writing the code? That's when we plugged GitHub Copilot into the other end. Now, if a request is about infrastructure — a Helm chart, an ingress rule, a DNS record — the coding agent picks up the ticket and generates the PR. The team stopped being a ticket-processing factory and started focusing on the work that actually needs a human.

If you want to see how we deploy AI PM with OpenClaw in practice, see [this walkthrough](https://www.linkedin.com/posts/hmquan1996_ai-pm-activity-7444338782897696768-oXrO/).

## The Checklist Test

Before introducing any AI, we applied a simple test to every task we considered automating:

> *Could a new junior engineer, given a written checklist, complete this task correctly on their first day?*

If yes, an AI can probably handle it. If no — if the task requires asking someone in Slack which repo to use, or knowing an undocumented naming convention, or making a judgment call about hostname and TLS settings — then the workflow isn't ready for automation.

Most tasks failed this test the first time. Not because they were genuinely complex, but because the process lived in people's heads. The ingress naming convention was "obvious" to the team but written nowhere. The distinction between which changes go in the Terraform repo versus the ArgoCD repo was "just something you know."

The work of making AI effective was, almost entirely, the work of documenting and structuring what humans already did implicitly. Writing down the routing rules. Creating templates. Making the implicit explicit.

This is the unsexy truth about AI automation: the value isn't in the AI layer. It's in the process design layer that makes AI possible.

## Designing the Handoff Chain

Once the workflow is structured, the architecture becomes obvious. You don't need a monolithic AI system that does everything. You need a chain of simple handoffs, where each step has clear inputs and clear outputs.

For infrastructure requests, our chain looks like this:

```
Request → Triage → Structured Work Item → Code Generation → Human Review
```

Some requests need a fan-out. One request can produce multiple work items, each routed to a different repository.

Each step is handled by a different system, and each system does exactly one job:

1. **Triage agent** receives the request, determines what type of infrastructure change it is, and routes it to the right context (which repo, which resource type, which environment).

2. **Work item** captures the request in a structured format — resource type, environment, parameters, target repository. This is the critical artifact. It serves as both the audit trail and the prompt for the next step.

3. **Code generation agent** reads the work item and produces a pull request with the corresponding code.

4. **Human review** — an engineer reviews the PR, adjusts if needed, and merges.

The key insight: **the work item is the contract between the triage agent and the code generation agent.** Its quality determines everything downstream. A vague ticket produces vague code. A structured ticket with explicit parameters, environment context, and repo target produces code that's usually correct on the first pass.

This is why the ticket template matters more than the AI model. We spent more time refining the template than configuring the AI.

## The Structured Ticket as a Prompt

Most teams think of tickets as records for humans. In an AI-augmented workflow, the ticket serves a dual purpose: it's a record *and* it's a prompt.

When a code generation agent picks up a ticket, it reads the title and description as its entire context. Everything the agent needs to produce correct code must be in that ticket. This changes how you write tickets.

A traditional ticket might say:

```
Summary: Add Kafka UI in staging
Description: As discussed, please deploy it.
```

Fine for a human who was in the conversation. Useless for an AI that wasn't.

A ticket designed for AI consumption looks different:

```
Summary: Deploy Kafka UI in STG with URL kafka-ui.stg.example.com
Description:
  Work Item A (Cluster Bootstrap Repo):
    Repository: org/cluster-bootstrap-stg
    Resource: Helm release + Kubernetes Ingress
    Environment: STG
    Namespace: data-platform
    Service Name: kafka-ui
    Hostname: kafka-ui.stg.example.com
    TLS: Enabled via cert-manager cluster issuer letsencrypt-stg
    Exposure: Internal only (private ingress class)
    Upstream Kafka Bootstrap Servers: msk-data.stg.example.internal:9092

  Work Item B (Terraform Repo):
    Repository: org/terraform-non-prod
    Resource: AWS Route53 Record
    Environment: STG
    Hosted Zone: stg.example.com
    Record Name: kafka-ui.stg.example.com
    Record Type: CNAME
    Target: internal-ingress.stg.example.internal
    TTL: 300

  Create two PRs: one for Helm/Ingress and one for Route53 Terraform.
```

Same request. But now every piece of context is explicit: the repo, the resource type, the environment, the network parameters, and what action the agent should take. The agent doesn't need to infer anything. It just executes.

This is a general pattern that applies beyond infrastructure. **Whenever you're building a workflow where AI handles a downstream step, design the handoff artifact (ticket, message, event) as if the receiver has zero context.** Because it does.

## Why Routing Matters More Than You Think

A subtlety that tripped us up: not all infrastructure changes go to the same place.

In most organizations, infrastructure code is split across repositories. Terraform for cloud resources. Kubernetes manifests or Helm charts for application deployment. Possibly separate repos for different environments or teams.

The triage agent needs to know which repo to target. Get this wrong, and the code generation agent produces correct code in the wrong place. For this Kafka UI request, writing only Helm without DNS leaves the URL broken. Writing only Route53 without ingress leaves the endpoint dead.

We use two categories:

- Cloud infrastructure (VPC, SG, RDS, MSK, IAM, Route53 DNS records) goes to the Terraform repository.
- Application deployment and cluster config (Helm, ArgoCD, services, ingress) goes to the cluster bootstrap repository.

For the request "I need a Kafka UI STG with URL kafka-ui.stg.example.com," routing should create two work items: cluster bootstrap for deployment + ingress, and Terraform for Route53.

The routing logic is straightforward once you write it down. But "straightforward" doesn't mean "obvious." Before we codified these rules, engineers just *knew* which repo to use. That knowledge was invisible — and invisible knowledge is exactly what breaks AI workflows.

If you're designing a similar system, map out every routing decision your team makes implicitly. Where does this type of change go? Who handles it? What format does it need? Write it all down. The AI needs it, and honestly, your new hires need it too.

## The Integration Gap Nobody Warns You About

Here's where theory hits reality. You've designed the workflow, structured the tickets, defined the routing. Now you need to connect the systems. And this is where you'll burn time you didn't plan for.

The obvious approach was to trigger the code generation agent directly from Slack — the triage agent creates a ticket and simultaneously asks the code agent to start working. Simple. Elegant. Doesn't work.

Bot-to-bot communication is a minefield. Most AI integrations — Slack apps, Jira integrations, GitHub Apps — are designed for human interaction. They respond to human @mentions, human assignments, human comments. When another bot tries the same interactions programmatically, things break in subtle ways.

We tried three approaches before finding one that worked:

**Approach 1: Mention the code agent in Slack.** The Slack API supports bot mentions using the `<@BOT_ID>` format. But the receiving app (GitHub Copilot, in our case) is designed for human triggers. Bot-to-bot mentions don't activate it.

**Approach 2: Mention the code agent in a Jira comment.** Jira supports @mentions in comments. But the CLI posts plain text. Jira's comment system uses Atlassian Document Format (ADF) — a rich JSON structure — to create real, actionable mentions. Plain text `@agent-name` renders as literal text. No trigger fires.

**Approach 3: Assign the code agent as the ticket assignee.** Assignment is a simple field update — no rich text required. The code agent monitors for assignments, reads the ticket context, and starts working.

Option 3 worked. It was also the least "clever" approach, which should have been our first clue.

> **The principle:** When integrating AI agents across systems, prefer the simplest trigger mechanism available. Rich interactions (mentions, threaded replies, interactive messages) are designed for humans. Simple state changes (assignment, status transition, label) are more reliable for machine-to-machine handoffs.

This applies broadly. If you're chaining multiple AI systems together, find the dumbest, most reliable trigger at each boundary. Clever integrations are fragile. Boring integrations are resilient.

## The Human Gate: Where to Put It and Why It Matters

You could make this workflow fully autonomous — request arrives, ticket gets created, code agent generates a PR, tests pass, auto-merge. End to end, no human in the loop.

Don't do that. At least not yet.

The human review step isn't overhead. It's your safety net and your feedback loop.

**Safety:** AI-generated infrastructure code is usually *close* to correct. An 80% correct deployment change is worse than no change at all — it looks right, passes basic checks, and still ships subtle misconfigurations. A human reviewing the PR catches these edge cases: wrong hostname, missing TLS, ingress exposed too broadly, or a Route53 record in the wrong hosted zone.

**Feedback:** Every PR that needs correction is a signal. If the code agent keeps getting the naming convention wrong, the template needs updating. If it consistently misses a required tag, the ticket description template needs a new field. The human review step generates the feedback that makes the system better over time.

**Trust:** Teams adopt AI automation faster when they can see what it's doing. A PR is visible, reviewable, and reversible. "The AI created a PR, please review" is a much easier sell than "the AI changed your infrastructure."

Position the human gate at the code review step. Everything before that — triage, ticket creation, code generation — can be automated. The PR review is where human judgment adds the most value per minute spent.

## What a Junior Engineer Can — and Can't — Handle

We call this system a "Junior DevOps" for a reason. Like a real junior engineer, it's productive within its competence zone and unreliable outside of it.

**Where it excels:**
- Single-service changes with explicit parameters (ingress rules, Helm values, service exposure)
- Single DNS changes with explicit parameters (Route53 hosted zone, record name, record type, target)
- Standard configurations that follow established templates
- Environment-specific variations of existing patterns (deploy in staging what already exists in dev)

**Where it struggles:**
- Multi-resource changes with dependencies (VPC + subnets + route tables + NAT gateway with cross-references)
- Changes that require reading and understanding existing infrastructure state
- Architectural decisions (should this be a managed service or self-hosted?)
- Production infrastructure (we deliberately limit to non-production)

This boundary matching is intentional. A well-scoped AI that handles 60% of requests reliably is far more valuable than an ambitious AI that attempts 100% and fails unpredictably.

The temptation is to expand the scope — handle more complex requests, reduce human involvement, automate production changes. Resist this until the simple cases are bulletproof. Build trust iteratively. Expand scope gradually.

## Three Patterns That Transfer to Any Domain

The specifics of our setup — Terraform, ArgoCD, Jira, Slack — are less important than the patterns underneath. These transfer to any domain where you're integrating AI into an operational workflow.

**Pattern 1: Workflow-First, AI-Second.** Design the workflow as if AI doesn't exist. Make every step documented, every routing decision explicit, every handoff structured. Then add AI to individual steps. If the workflow is sound, each AI component is simple. If the workflow is broken, no amount of AI sophistication will fix it.

**Pattern 2: The Handoff Artifact Is the Prompt.** Whatever artifact passes between your systems — ticket, event, message, file — design it as a prompt for the downstream consumer. Include all context. Assume zero prior knowledge. The quality of this artifact determines the quality of everything downstream.

**Pattern 3: Dumb Triggers, Smart Processing.** At system boundaries, use the simplest possible trigger mechanism. Save the intelligence for processing inside each component. Clever cross-system integrations break. Simple field changes, status transitions, and assignments are reliable.

## The Uncomfortable Truth

The hardest part of building an AI Junior DevOps wasn't the AI. It was admitting how much of our existing process relied on implicit knowledge, undocumented conventions, and "everyone just knows."

Making those things explicit — writing down routing rules, creating ticket templates, documenting naming conventions — felt like busywork. It wasn't. It was the foundation that made everything else possible.

If you're evaluating where AI can help your DevOps team, start there. Don't ask "what AI tool should we buy?" Ask "could a new engineer follow our process from a document, without asking anyone?" If the answer is no, that's your first task — and it'll pay off whether you add AI or not.
