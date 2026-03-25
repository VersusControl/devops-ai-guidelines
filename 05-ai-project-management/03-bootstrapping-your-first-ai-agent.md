# Chapter 3: Bootstrapping Your First AI Agent

The first time I got the agent to read my JIRA board and respond in Slack, it returned a single sentence: "The current sprint has 14 issues." That was it. No breakdown by status, no risk flags, no useful context. Just a count.

I stared at it for a few seconds, then smiled. It worked. The plumbing was connected. A message in Slack triggered an agent that called the JIRA API, read real data, and posted a response. Everything after that — the smart summaries, the blocker detection, the standup collection — was just better prompts and more tools on top of this foundation.

This chapter gets you to that moment. By the end, you'll have a running OpenClaw agent connected to your JIRA board and living in your Slack workspace. It won't be smart yet. But it will be real.

## What We're Building

Here's the target for this chapter:

1. OpenClaw installed and configured on your local machine.
2. A JIRA API connection that can read your sprint board.
3. A Slack bot that your team can interact with.
4. An agent that ties it all together — receives a question in Slack, reads from JIRA, and responds.

<div align="center" style="border-bottom: none">
  <img alt="End-to-end flow" src="images/03-01-user-agent-jira-flow.png" style="max-width: 900px; width: 100%; height: auto;">
</div>

We'll move through this step by step. Each section ends with a verification — a quick test to confirm that piece is working before moving on. If something breaks, the troubleshooting notes at the end of each section will help you diagnose it.

## Setting Up OpenClaw

> **Need help?** If you get stuck while configuring this chapter, contact me at **hmquan08011996@gmail.com**.

We'll go step by step, starting from zero. If you've never used a terminal before, that's fine — just follow along and type exactly what you see. If you're a developer who's done this kind of thing before, the steps are the same, just faster for you.

### Step 1: Install Node.js

OpenClaw runs on Node.js — a tool that lets programs run on your computer. You need Node 24 (recommended) or Node 22.16+.

**Check if you already have it.** Open a terminal (on Mac, search for "Terminal" in Spotlight; on Windows, search for "PowerShell" in the Start menu) and type:

```bash
node --version
```

If you see something like `v24.1.0`, you're good — skip to Step 2.

**If you get "command not found," install Node:**

**On Mac:**

1. Go to https://nodejs.org
2. Download the LTS (Long Term Support) version for macOS
3. Run the installer — click through the defaults
4. Close and reopen Terminal, then run `node --version` again to confirm

**On Windows:**

1. Go to https://nodejs.org
2. Download the LTS version for Windows
3. Run the installer. Make sure "Add to PATH" is checked
4. Open PowerShell and type `node --version` to confirm

> **Tip:** If you get stuck, OpenClaw has a dedicated guide at https://docs.openclaw.ai/install/node. The OpenClaw team recommends WSL2 on Windows for the smoothest experience, but native Windows with PowerShell also works.

### Step 2: Get an API Key from a Model Provider

The agent needs access to an AI model to think. OpenClaw supports several providers — OpenAI, Anthropic, Google, and others. We'll use OpenAI in this book, but the onboarding wizard will let you pick whichever you prefer.

1. Go to https://platform.openai.com and create an account (or sign in)
2. Go to https://platform.openai.com/api-keys
3. Click "Create new secret key"
4. Give it a name like "AI PM Agent"
5. Copy the key and save it somewhere safe — a password manager, a private note, anywhere you won't lose it. The onboarding wizard will ask for it in a few minutes.

> **Note:** OpenAI charges per API call. For development and testing, expect to spend $5–15 per month. Sprint summaries and standup processing are relatively cheap — most of the cost comes from iterating on prompts during development. Other install methods (Docker, Nix, npm) are documented at https://docs.openclaw.ai/install.

### Step 3: Install OpenClaw

Back in your terminal, run the install script:

**On Mac/Linux:**
```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

**On Windows (PowerShell):**

See the Windows-specific instructions at https://docs.openclaw.ai/platforms/windows.

The script does everything for you: it detects your operating system, installs Node if needed, installs OpenClaw, and then launches the onboarding wizard automatically.

### Step 4: Complete the Onboarding Wizard

The install script opens an interactive wizard right after installation. It walks you through:

1. **Choosing a model provider** — pick OpenAI (or whichever provider you got an API key for).
2. **Entering your API key** — paste the key you saved in Step 2.
3. **Configuring the Gateway** — the Gateway is the background service that keeps your agent running. The wizard sets it up for you.
4. **Installing the daemon** — so the Gateway starts automatically and stays running in the background.

The whole process takes about 2 minutes. Just follow the prompts — the wizard explains each step as you go.

> **Tip:** If you ever need to reconfigure later, run `openclaw configure` to launch the wizard again.

### Step 5: Verify It's Working

Check that the Gateway is running:

```bash
openclaw gateway status
```

You should see a message saying the Gateway is listening on port 18789. Then open the dashboard:

```bash
openclaw dashboard
```

This opens a web page in your browser — the Control UI. If it loads, everything is working. Type a message in the chat and you should get an AI reply.

### What Just Happened?

You installed and configured three things:

1. **Node.js** — the runtime that OpenClaw is built on. You won't need to write JavaScript, but OpenClaw needs it to run.
2. **OpenClaw** — the agent framework itself, installed via the install script.
3. **The Gateway** — a background service that keeps your agent alive and handles communication between the AI model, your tools, and your chat channels.

That's the hard part done. The rest of this chapter is configuration — connecting JIRA and Slack, not writing code.

### How OpenClaw Is Organized

After onboarding, OpenClaw stores everything under `~/.openclaw/`. Here's what matters:

```
~/.openclaw/
├── openclaw.json            # Main configuration (model, channels, settings)
├── workspace/               # Agent workspace
│   ├── AGENTS.md            # Agent behavior and instructions
│   ├── SOUL.md              # Agent personality and identity
│   ├── TOOLS.md             # Tool usage guidelines
│   ├── USER.md              # Info about you (the user)
│   └── .openclaw/           # Internal workspace config
├── agents/                  # Agent profiles
├── completions/             # Completion history
├── identity/                # Agent identity files
├── logs/                    # Log files
└── devices/                 # Device/session tracking
```

You don't need to touch most of this directly. But it helps to know where things live:

- `openclaw.json` — The main config file. This is where your model provider, channel settings (Slack, Telegram, etc.), and agent behavior are defined. It's JSON5 format (JSON with comments allowed).
- `workspace/` — Where the agent's personality and instructions live. The markdown files here shape how the agent behaves — `AGENTS.md` defines its capabilities, `SOUL.md` defines its personality, and `TOOLS.md` guides how it uses tools.
- `logs/` — Log files for debugging. Check here when something goes wrong.

There are three ways to change configuration:

```bash
# Interactive wizard — walks you through options
openclaw configure

# Control UI — edit visually in your browser
openclaw dashboard

# Direct edit — open the file in any text editor
nano ~/.openclaw/openclaw.json    # or use VS Code, vim, etc.
```

After editing the config file directly, OpenClaw picks up changes automatically — it watches the file and hot-reloads most settings without a restart. If something goes wrong, run `openclaw doctor` to diagnose issues.

> **Tip:** If you're not comfortable editing JSON files, stick with `openclaw configure` — the interactive wizard handles everything for you.

### Configuring the Model

The onboarding wizard already set up your model provider and API key. To check or change the default model:

```bash
# See what models are available
openclaw models list
```

For PM tasks, you want a capable model. GPT-4 or Claude 3.5 Sonnet are good choices. Smaller models work for simple queries but struggle with complex sprint analysis.

> **Note:** OpenAI charges per API call. For development and testing, expect to spend $5–15 per month. Sprint summaries and standup processing are relatively cheap — most of the cost comes from iterating on prompts during development.

### Verification: Agent Responds

Let's make sure the basic agent works before adding any integrations. First, check which agents you have:

```bash
openclaw agents list
```

You should see at least one agent — typically `main` (the default). Note the agent name.

Now send a test message:

```bash
openclaw agent --agent main -m "What can you help me with?"
```

You should get a response from the AI. The `--agent main` flag tells OpenClaw which agent to use. If you prefer an interactive chat session, open the dashboard or the terminal UI:

```bash
openclaw dashboard    # browser-based chat
openclaw tui          # terminal-based chat
```

> **Troubleshooting:** If you get an authentication error, run `openclaw doctor` — it checks your configuration and flags issues. If the model test fails, verify your model setup with `openclaw models list` and check that your provider account has access to the model you selected.

## Connecting to JIRA

This is where the agent stops being a chatbot and starts being useful. We're going to give it the ability to read and interact with your JIRA board.

OpenClaw has a community-maintained JIRA skill available on ClawHub. It supports two backends: the `jira` CLI tool and the Atlassian MCP. We'll use the `jira` CLI — it's the simplest to set up.

### Step 1: Install the Jira CLI

The `jira` CLI is an open-source tool that talks to JIRA from the command line. Install it:

**On Mac:**
```bash
brew install ankitpokhrel/jira-cli/jira-cli
```

**On Linux/Windows (WSL2):**
```bash
go install github.com/ankitpokhrel/jira-cli/cmd/jira@latest
```

> **Tip:** If you don't have Homebrew on Mac, install it first from https://brew.sh. If you don't have Go installed for Linux, see the jira-cli GitHub page for alternative install methods: https://github.com/ankitpokhrel/jira-cli

### Step 2: Configure the Jira CLI

Run the setup wizard:

```bash
jira init
```

It will ask you for three things:

1. **JIRA server URL** — your Atlassian domain, e.g., `https://your-domain.atlassian.net`
2. **Email** — the email address associated with your JIRA account
3. **API token** — create one at https://id.atlassian.com/manage-profile/security/api-tokens. Click "Create API token," give it a label like "AI PM Agent," and paste the token when prompted.

That's it. The CLI stores the credentials locally. Verify it works:

```bash
jira me
```

This should print your JIRA username. If it does, try:

```bash
jira sprint list --state active
```

You should see your current sprint. If both commands work, the CLI is ready.

> **Warning:** The API token has the same permissions as your JIRA account. For development, your personal token is fine. For production, create a dedicated service account with only the permissions the agent needs. We'll cover this in Chapter 13.

### Step 3: Install the JIRA Skill

OpenClaw has a skill marketplace called ClawHub. The JIRA skill is already published there. Install it:

```bash
openclaw skills install jira
```

Verify it's loaded:

```bash
openclaw skills list
```

You should see `🎫 jira` in the list with status `✓ ready`. The skill automatically detects that the `jira` CLI is installed and uses it as the backend.

The skill gives the agent a full set of JIRA capabilities: viewing issues, listing tickets, checking sprint status, creating and updating tickets, managing transitions, and more. It's safety-first — it always fetches current state before modifications and asks for approval before making changes.

### Verification: JIRA Connection

Test the JIRA connection by sending a message to the agent:

```bash
openclaw agent --agent main -m "What's in the current sprint?"
```

The agent should use the JIRA skill to query your active sprint and return a list of tickets. Try a follow-up:

```bash
openclaw agent --agent main -m "Show me the details for PROJ-123"
```

Replace `PROJ-123` with an actual ticket key from your board. The agent should return the ticket's summary, status, assignee, and other details.

> **Troubleshooting:** If the agent responds without calling any JIRA tools, the skill might not be installed. Run `openclaw skills list` and check that `jira` shows as `✓ ready`. If it shows `✗ missing`, run `openclaw skills install jira`. If the skill is ready but the agent gets errors, verify the CLI works directly with `jira me` — if that fails, re-run `jira init` to fix your credentials.

## Setting Up the Slack Channel

The agent needs a way to talk to your team. That's Slack. OpenClaw has built-in Slack support — you create a Slack app, grab the tokens, and configure the channel. No custom code, no ngrok tunnels.

### Creating the Slack App

1. Go to https://api.slack.com/apps
2. Click "Create New App"
3. Choose "From scratch"
4. Name it something your team will recognize — "AI PM" or "Sprint Bot" or whatever fits your culture
5. Select your workspace

### Enabling Socket Mode

OpenClaw uses Slack's Socket Mode by default. This means the bot connects *outward* to Slack — no public URL needed, no tunneling tools, no firewall configuration. It just works.

In the Slack app settings:

1. Go to "Socket Mode" in the left sidebar
2. Toggle "Enable Socket Mode" to On
3. You'll be prompted to create an App-Level Token. Name it "openclaw" and add the scope `connections:write`
4. Copy the token — it starts with `xapp-`

### Configuring Bot Permissions

Go to "OAuth & Permissions" and add these Bot Token Scopes:

```
app_mentions:read          — Know when someone @mentions the bot
channels:history           — Read messages in public channels
channels:read              — See channel list and details
chat:write                 — Post messages
groups:history             — Read messages in private channels
groups:read                — See private channel list
im:history                 — Read direct messages
im:read                    — See DM list
im:write                   — Send direct messages
users:read                 — Look up user information
assistant:write            — Show typing indicators in threads
```

Click "Install to Workspace" and authorize the app. Copy the "Bot User OAuth Token" — it starts with `xoxb-`.

### Subscribing to Events

Go to "Event Subscriptions" and subscribe to these bot events:

```
app_mention                — When someone @mentions the bot
message.channels           — Messages in public channels
message.groups             — Messages in private channels
message.im                 — Direct messages
message.mpim               — Group DMs
reaction_added             — When someone reacts to a message
reaction_removed           — When a reaction is removed
```

Also go to "App Home" and enable the "Messages Tab" — this allows DMs with the bot.

### Configuring OpenClaw

Now tell OpenClaw about your Slack app. The easiest way is to edit the config file directly. Open `~/.openclaw/openclaw.json` and add the Slack channel configuration:

```json
{
  "channels": {
    "slack": {
      "enabled": true,
      "mode": "socket",
      "appToken": "xapp-your-app-token",
      "botToken": "xoxb-your-bot-token",
      "groupPolicy": "open",
      "channels": {
        "*": {
          "requireMention": true
        }
      }
    }
  }
}
```

A few things to note about this config:

- `"groupPolicy": "open"` — lets the bot respond in any channel it's invited to.
- `"channels": { "*": ... }` — the wildcard `"*"` means "all channels." This is the simplest setup for getting started. You don't have to list every channel individually.
- `"requireMention": true` — the bot only responds when someone `@mentions` it. This prevents it from jumping into every conversation. Without this, the bot would try to respond to every message in every channel — not what you want.

If the file already has other settings from onboarding, just add the `channels.slack` section inside the existing structure. Don't replace what's already there.

> **Tip:** You can also set the tokens as environment variables in your shell profile instead of putting them in the config file. OpenClaw checks `SLACK_APP_TOKEN` and `SLACK_BOT_TOKEN` as fallbacks when the config file doesn't have the tokens. You can also set them inline in the config using the `env` section:
> ```json
> {
>   "env": {
>     "SLACK_APP_TOKEN": "xapp-your-app-token",
>     "SLACK_BOT_TOKEN": "xoxb-your-bot-token"
>   }
> }
> ```

Alternatively, if you prefer not to edit JSON by hand, run `openclaw configure` and follow the interactive wizard — it has a channels section that walks you through Slack setup.

### Verification: Slack Connection

OpenClaw watches the config file and picks up changes automatically. Check that Slack is connected:

```bash
openclaw channels status
```

You should see the Slack channel listed as connected. Now go to Slack and test it:

1. Invite the bot to a channel: `/invite @AI PM`
2. Mention the bot: `@AI PM hello`

The bot should respond. If it does, try something more useful:

```
@AI PM What JIRA boards do I have?
```

The agent should call the JIRA skill and respond with your board list — right there in Slack.

> **Troubleshooting:** If the bot doesn't respond, check these in order:
> 1. Run `openclaw channels status` — is it showing as connected?
> 2. Run `openclaw doctor` — it checks for common configuration issues.
> 3. Check `openclaw logs` for error messages.
> 4. Make sure Socket Mode is enabled in your Slack app settings.
> 5. Verify the bot is invited to the channel you're messaging in.
>
> The most common issue is a mismatched token. Double-check that the `appToken` starts with `xapp-` and the `botToken` starts with `xoxb-`.

## Wiring It All Together

You now have three pieces working: the agent (LLM), the JIRA connection (skill), and the Slack channel. Let's give the agent proper instructions for its PM role.

### Setting the Agent's System Prompt

OpenClaw uses a file called `SOUL.md` in the workspace to define who the agent is. This is the agent's identity — its role, behavior rules, boundaries, and communication style. The bootstrapping process created a default one during setup, but we want to customize it for PM work.

Open `~/.openclaw/workspace/SOUL.md` and replace its contents (or edit the relevant sections) to shape the agent for project management:

```markdown
# SOUL.md - Who You Are

_You're not a chatbot. You're an AI Project Manager._

## Role

You are an **AI PM**. Your primary job is to help the engineering team
with project management tasks:

- **Sprint status tracking** — Read JIRA boards, summarize sprint
  progress, highlight risks
- **Standup collection** — Collect async standups from team members,
  compile summaries
- **Blocker detection** — Identify tickets stuck, flag blockers before
  they escalate
- **Task management** — Help with ticket creation, priority suggestions,
  workload awareness

## Core Truths

**Be genuinely helpful, not performatively helpful.** Skip the
"Great question!" and "I'd be happy to help!" — just help.

**Have opinions on project health.** If a sprint looks at risk, say so.
If priorities seem misaligned, flag it. A PM without opinions is just
a status board.

**Act on read-only requests immediately.** When asked to list issues,
check sprint status, or show ticket details — run the command and
return the results. Don't ask for confirmation on read operations.

**Earn trust through accuracy.** Never hallucinate ticket statuses or
sprint data. If you're unsure, say so. Wrong data is worse than no data.

## Boundaries

- You start as read-only. Don't create, update, or delete JIRA tickets
  unless explicitly told to.
- Never send notifications to stakeholders without checking first.
- If data looks inconsistent, flag it rather than guessing.
- When in doubt about priority, default to Medium — don't ask.

## Formatting

- Use Slack formatting: *bold* for emphasis, bullet lists for
  multiple items.
- Always reference JIRA ticket keys (e.g., PROJ-123) when discussing
  specific issues.
- When reporting sprint status, group tickets by status category:
  To Do, In Progress, In Review, Done.

## Vibe

Be the PM you'd actually want to work with. Concise when needed,
thorough when it matters. Not a corporate drone. Not a sycophant.
Just... good.
```

This file does several important things:

- **Sets the role.** The agent knows it's a PM, not a general-purpose assistant. This focuses its responses on project management tasks.
- **Defines behavior.** "Act on read-only requests immediately" prevents the agent from asking unnecessary confirmation questions. "Earn trust through accuracy" prevents hallucination.
- **Sets boundaries.** The agent starts read-only. As you build trust, you can loosen these boundaries in later chapters.
- **Defines formatting.** Consistent output formatting builds trust. When the agent always presents data the same way, the team learns to read it quickly.

> **Tip:** `SOUL.md` is the agent's identity file — it reads this at the start of every session. Other workspace files matter too: `AGENTS.md` defines workspace behavior, `USER.md` stores info about you, and `TOOLS.md` has tool-specific notes. You can customize all of them over time.

### Testing the Full Loop

Restart the Gateway to pick up the new system prompt:

```bash
openclaw gateway restart
```

Go to Slack and run through these tests:

**Test 1: Basic greeting**
```
@AI PM Hi, what can you do?
```
Expected: The agent describes its capabilities based on the system prompt.

**Test 2: Board listing**
```
@AI PM What JIRA boards do I have?
```
Expected: The agent calls `list_boards` and returns your board names and IDs.

**Test 3: Sprint status**
```
@AI PM What's the status of our current sprint?
```
Expected: The agent calls `get_active_sprint`, then `get_sprint_issues`, and returns a grouped summary of tickets by status.

**Test 4: Specific ticket**
```
@AI PM Tell me about PROJ-123
```
Expected: The agent calls `get_issue_details` and returns the ticket's summary, status, assignee, and other details.

**Test 5: Boundary test**
```
@AI PM Can you move PROJ-123 to Done?
```
Expected: The agent explains that it's read-only and can't modify tickets.

If all five tests pass, your foundation is solid. The agent can read JIRA, communicate through Slack, and respect its boundaries.

## Common Setup Pitfalls

I hit every one of these during my first setup. Saving you the debugging time:

### API Rate Limits

JIRA's API has rate limits. If you're testing heavily, you might hit them. Symptoms: the agent gets empty responses or errors from JIRA commands. The fix: slow down your testing. The `jira` CLI handles basic retry logic, but sustained rapid-fire calls will still trigger limits.

### Slack Message Formatting

Slack has its own markdown flavor. Some things that trip people up:

- Bold is `*text*`, not `**text**`
- Links are `<url|display text>`, not `[display text](url)`
- Code blocks use triple backticks, same as regular markdown
- User mentions are `<@USER_ID>`, not `@username`

If the agent's messages look weird in Slack, it's usually a formatting mismatch. Update the system prompt to specify Slack formatting conventions.

### Config Hot-Reload and When You Need a Restart

OpenClaw watches `~/.openclaw/openclaw.json` and hot-reloads most changes automatically — no restart needed. Channel settings, model changes, agent config, and automation rules all apply instantly.

The exception: Gateway server settings (port, bind address, authentication mode, TLS). If you change those, you need a manual restart:

```bash
openclaw gateway restart
```

If something feels off after a config change, run `openclaw doctor` to check for issues.

### Use `openclaw doctor` When Stuck

If something isn't working and you can't figure out why, run:

```bash
openclaw doctor
```

It checks your configuration, validates credentials, tests connections, and flags issues. It's the first thing to try when debugging.

## What We Built

Take a step back and look at what you have:

- An OpenClaw Gateway running locally with your chosen LLM as its reasoning engine.
- The JIRA skill from ClawHub, powered by the `jira` CLI, giving the agent full access to your boards, sprints, and tickets.
- A Slack channel connected via Socket Mode with wildcard `"*"` access so the bot works in any channel it's invited to.
- A system prompt that defines the agent's role, capabilities, and boundaries.
- A working end-to-end loop: Slack message → agent reasoning → JIRA data → Slack response.

It's not an AI project manager yet. It's a foundation. It can answer questions about your sprint, but it can't proactively summarize progress, detect blockers, or collect standups. That's what Chapter 4 is for.

But the hard part — the plumbing, the authentication, the integration — is done. Everything from here builds on this foundation.

## Looking Ahead

In the next chapter, we'll turn this foundation into a working prototype. We'll build three features that deliver immediate value:

1. **Automated sprint summaries** — the agent reads the board and posts a daily status update without being asked.
2. **Async standup collection** — the agent DMs team members for updates and compiles the responses.
3. **Blocker detection** — the agent scans for stuck tickets and flags them before anyone notices.

Each feature starts small and grows based on what the team actually uses. The goal isn't to build everything — it's to ship the smallest useful thing and learn from real usage.

Your agent is alive. Let's make it useful.

## Summary

- OpenClaw installs via a one-line script and configures itself through an onboarding wizard. The Gateway runs as a background service on port 18789.
- JIRA connectivity uses the `jira` CLI tool (`brew install ankitpokhrel/jira-cli/jira-cli`) plus the JIRA skill from ClawHub (`openclaw skills install jira`). Setup is `jira init` with your Atlassian credentials.
- Slack integration uses Socket Mode — no public URLs or tunneling needed. Create a Slack app, grab the tokens, and configure the channel in OpenClaw with wildcard `"*"` access for convenience.
- The system prompt defines the agent's identity, capabilities, boundaries, and formatting rules. It's the single most important configuration for agent behavior.
- When stuck, `openclaw doctor` diagnoses issues, `openclaw logs` shows what's happening, and `openclaw gateway restart` picks up config changes.
