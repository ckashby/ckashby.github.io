# Stop Micro-Managing Files. Start Engineering the Model's Reasoning.

**An argument for AI developers: your leverage moved, and it moved up a layer.**

---

There's a way of working with coding agents that feels productive and is quietly a dead end. You open the chat, point at a file, describe the exact edit, watch the diff, correct the diff, point at the next file, describe the exact edit. Four hours later you've shipped a feature and built nothing. Tomorrow you will do it again, from zero, on a codebase that learned nothing about how you want it to work.

This is the file-by-file era of AI-assisted development, and it's the direct analogue of a senior engineer who refuses to write documentation, refuses to add tests, and insists on reviewing every line personally. It works. It just doesn't scale, and it stops working entirely the moment the volume of generated code exceeds the attention you can spend on it.

The teams getting real leverage out of agents are not typing better prompts. They're doing something structurally different: they've stopped treating the model as a junior developer who needs line-by-line supervision and started treating it as a capable, tireless, highly literal reasoner operating inside an environment *they design*. Their work product isn't a diff. It's the environment that produces good diffs.

OpenAI's Codex team described this shift directly. In a five-month internal experiment they built a product with roughly a million lines of code and about 1,500 pull requests, with **zero lines of manually written code**. Three engineers, later seven, against an estimate of about ten times that with conventional staffing. The lesson they drew was not "prompt harder." It was that humans design environments, specify intent, and build feedback loops — "Humans steer. Agents execute." Their own closing line is the thesis of this article: *the discipline shows up more in the scaffolding rather than the code.*

So let's talk about the scaffolding.

---

## Key Topics

- **Generative AI mechanics** — what you're actually influencing when you "program" a model, and why intent doesn't transfer by itself
- **Steering models through context** — context as a layered, versionable artifact rather than a chat message
- **AI harnesses** — the environment, tools, sensors, and guardrails that turn a probabilistic generator into a dependable system
- **Interface & settings management** — model choice, approval modes, tool allowlists, reasoning effort, and the small number of knobs that change outcomes more than any prompt
- **Context control** — curation, compaction, isolation, and progressive disclosure as first-class engineering concerns
- **Workflow-oriented engineering over tool-stacking** — add capabilities when they remove a measured bottleneck, not because they exist

---

## 1. Generative AI mechanics: you are not writing code, you are conditioning a distribution

The first thing to internalize is what a coding agent actually is when you talk to it.

It is not a compiler. It is not a function that maps a natural-language spec to a correct implementation. It's a next-token predictor conditioned on a token sequence, and every element of that token sequence — your instructions, the repo files it has read, the tool definitions it was given, the error message from the last failed test, the contents of its system prompt, the stale output from eleven minutes ago — is part of the conditioning. There is no separate channel for "what I really meant." Intent only exists in the context if you put it there.

Three consequences follow, and they're the mechanical foundation for everything else in this piece.

**Attention is a finite, competitive budget.** Anthropic describes this as context rot: as context length grows, a model's ability to reliably recall and use what's in it degrades, across model families. Some of this is the quadratic scaling of transformer attention; some of it is the mismatch between long-context training distributions and the messy realities of production. Either way, the practical implication is blunt: *more context is not more information.* Past a point, it's dilution. The goal is the smallest possible set of high-signal tokens that gets the behavior you want.

**Tool calls are context, not side effects.** When you give a model forty tools with sprawling JSON schemas, you've spent tens of thousands of tokens before the user has said anything. Anthropic has documented MCP setups where tool definitions alone consumed 134,000 tokens pre-optimization, and where the dominant failure mode wasn't missing capability but *wrong tool selection* — models confusing `notification-send-user` with `notification-send-channel` because both were in the window. The tool surface is a context design decision, not a plumbing decision.

**Models imitate what they can see, including the bad parts.** OpenAI observed that Codex replicates patterns already present in the repository, "even uneven or suboptimal ones," and that this drift compounds. Their answer wasn't more review. It was encoding opinionated mechanical rules into the repo and running recurring cleanup tasks — functionally garbage collection for code entropy. A model with one good example in context will copy that example. A model with nine mediocre examples and one good one will average them.

If you accept those three properties, the line-by-line workflow starts to look irrational. You're spending the scarcest resource in the system — your own attention — on the exact layer where the model needs it least (individual keystrokes), while leaving the layer where it needs it most (the environment that shapes what it sees and what it can verify) completely unmanaged.

---

## 2. Steering models through context: five layers, not one prompt

"The prompt" is the wrong unit. Production agents are conditioned by a stack of layers, and each one has a different owner, a different update cadence, and a different failure mode. Think of it like this:

**Layer 1 — Durable project truth.** Architecture, conventions, invariants, the shape of the domain. This belongs in the repository, versioned, reviewed like code. Not in a wiki nobody has opened since Q1, not in a Slack thread, not in a senior engineer's head. OpenAI's framing is the sharpest version of this: *knowledge that isn't in the repo doesn't exist to the agent.* They moved their system of record into structured `docs/` — architecture decisions, plans, specs, references — because a model cannot use context it can't retrieve.

**Layer 2 — Task intent.** What "done" means for this specific piece of work, expressed as acceptance criteria rather than implementation instructions. This is the highest-leverage sentence you will write all day. "Add pagination to the users endpoint" is a wish. "Return 50 users per page by default, accept `?limit=` up to 200, return a `next_cursor` that round-trips, and add tests covering boundary pages and an invalid cursor" is a contract — one an agent can satisfy *and* verify. The difference in output quality between those two phrasings is larger than the difference between most model tiers.

**Layer 3 — Retrieved local knowledge.** The files, symbols, and call sites that actually matter. Not the whole repo. Progressive disclosure: a short map at the top, pointers to detail, detail loaded on demand. OpenAI explicitly rejected the giant-instructions-file approach in favor of a ~100-line `AGENTS.md` that functions as a table of contents into deeper documentation.

**Layer 4 — Examples and constraints.** One or two exemplars of the pattern you want, plus the hard boundaries you don't want crossed. Examples carry conventions that prose struggles to describe; constraints prevent the model from inventing a second way to do something the repo already does one way.

**Layer 5 — Feedback artifacts.** Test output, type errors, lint violations, screenshots, logs, traces, review comments. This is the layer people skip, and it's the one that closes the loop. Without it, layers 1–4 describe an intention and layer 5 never contradicts the model. With it, the model gets to be wrong in a way that's cheap, immediate, and self-correcting.

Two engineering principles apply to all five:

- **Front-load, don't repeat.** Anything you find yourself typing into the chat more than twice is a layer-1 artifact waiting to be written. Review comments you leave repeatedly are lint rules you haven't written yet.
- **Promote rules downward as they harden.** Prose in a doc is a suggestion. A test is an enforcement. Anthropic's guidance on system prompts uses the "right altitude" framing: not brittle hardcoded logic, not vague high-level guidance, but the specific principle expressed clearly enough to generalize. OpenAI's version of the same idea: *when documentation falls short, promote the rule into code.*

---

## 3. AI harnesses: the thing you're actually building

A harness is everything around the model that determines whether its output becomes working software: the instructions, the tool surface, the sandbox, the validators, the permissions, the observability, the recovery path. The model is a component. The harness is the system.

A useful split for thinking about it:

- **Inner harness** — the agent loop itself: how it plans, calls tools, observes results, decides when to stop, and what it does when it fails.
- **Outer harness** — everything the organization controls around that loop: repo docs, skills, tests, setup scripts, CI, environments, guardrails, evals.

Most teams invest almost entirely in the inner harness (choosing an agent product) and almost nothing in the outer one, then wonder why the results are inconsistent across repositories. The outer harness is where the durable, transferable leverage is.

### What a real harness contains

- **A repository that is legible to an agent.** Deterministic setup, one command to run the tests, no implied tribal knowledge, no "ask Dana for the staging credentials." Agent legibility is a design property of your codebase, not a property of the model.
- **Verification you can trust.** Fast tests, type checks, linters, structural tests. OpenAI's team enforced architectural boundaries with custom linters and structural tests, and — this is the elegant part — wrote the lint error messages to *inject remediation instructions into the agent's context*. The failure message is the fix instruction. That's a harness doing the teaching so you don't have to.
- **Observability the agent can read.** OpenAI made the running application legible to Codex: worktrees, Chrome DevTools Protocol access, screenshots, DOM snapshots, and query access to logs, metrics, and traces via LogQL/PromQL/TraceQL. The agent could see the failure, not just be told about it. If your agent can't observe the system it's changing, your feedback loop is a rumor.
- **Deterministic guardrails.** Permissions enforced in code, not in the prompt. A model asked politely not to touch `prod/` is a suggestion; a sandbox that makes `prod/` unreachable is a guarantee. Prompt-level restrictions are for guidance; code-level restrictions are for safety.
- **An escalation path.** The loop needs a defined exit for "a human should decide this." OpenAI's system escalates when judgment is required — which only works because everything else is automated. An agent that escalates on every ambiguity is a chat window; an agent that escalates only on genuine judgment calls is a colleague.
- **Evals tied to production traces.** Your harness should get measurably better over time. Pull failures out of real runs, turn them into test cases, and watch the failure rate fall. Without this, "the agent is bad at X" is a vibe, not a backlog item.

### The test of a good harness

Ask: *if the model got twice as good tomorrow, would my workflow get twice as fast?* In a line-by-line supervision workflow, the answer is barely — you remain the bottleneck at review. In a well-built harness, capability improvements compound into throughput, because the environment can absorb and verify more autonomous work.

OpenAI's own experience is the honest version of this. When throughput rose, many conventional engineering norms became counterproductive: minimal blocking merge gates, short-lived PRs, flakes handled with follow-up runs rather than indefinite blocking. Their reasoning is worth quoting in spirit: when agent throughput far exceeds human attention, corrections are cheap and waiting is expensive. That tradeoff would be irresponsible in a low-throughput environment. It becomes correct in a high-throughput one. **Your process has to be redesigned for the throughput you actually have** — and a harness is what changes that throughput.

---

## 4. Interface & settings management: the knobs that outperform your prompt

Developers spend days iterating on prompt wording and minutes on the settings that dominate outcomes. Here's the configuration surface that deserves the attention instead:

- **Instructions files as interface contracts.** `AGENTS.md`, `CLAUDE.md`, and equivalents are user interfaces, not documentation. Keep them short, command-first, and map-like: how to build, how to test, how to run a single test file, where the architecture lives, what "done" means. A thousand-line instructions file is an anti-pattern — it burns context on every turn and gets partially ignored. A hundred-line index into deeper docs is the pattern that worked for OpenAI. Write it for a competent stranger who reads fast and forgets faster.
- **Approval and autonomy modes.** Per-action approval is a great default for a new repository and a terrible default for a mature one. Match autonomy to the strength of your verification: strong tests and a sandbox justify autonomous iteration; weak tests justify gating. Configure this per repository, not per mood.
- **Tool allowlists and MCP scope.** Connect the tools this workflow needs, not every tool the organization owns. Anthropic's numbers on this are stark: in their internal testing, loading tools on demand instead of upfront preserved roughly 95% of the context window and raised MCP evaluation accuracy from 49% to 74% on one model generation and 79.5% to 88.1% on the next. Same models, better interface. That's a settings story, not a model story.
- **Model and reasoning-effort routing.** Use the most capable reasoning settings where ambiguity and architecture live; use faster, cheaper settings for mechanical, well-specified work — test scaffolding, renames, boilerplate, bulk edits. Routing by task shape is free performance. Sending a rename through maximum reasoning effort is as wasteful as sending a schema migration through the fastest tier.
- **Structured outputs and schemas.** Where the agent's output feeds another system, constrain the shape. Every schema you enforce is a class of bug you don't have to review.
- **Skills and commands as reusable interface primitives.** Package repeated workflows — "add a migration," "cut a release," "investigate a Sentry issue" — as named, tested, invocable units. This is how individual knowledge becomes harness capability instead of chat history.

The unifying idea: **settings are how you express intent structurally, and structure survives while instructions decay.** Every turn of the conversation the model re-reads its instructions; it reads its settings, tools, and permissions whether or not anyone is watching. Put your policy where it's always on.

---

## 5. Context control: curation is the job

Once you accept that context is a finite, degrading budget, "context control" becomes an engineering discipline rather than a housekeeping chore.

- **Prune aggressively, and prune deterministically.** Anthropic's context editing clears stale tool results as the window fills while preserving conversational continuity. In a 100-turn web-search evaluation, this let agents complete workflows that would otherwise fail from context exhaustion, with 84% fewer tokens consumed. Combine that with a memory tool and they measured a 39% performance improvement over baseline on their agentic search evaluation. Treat "what should be in the window right now" as a live, managed state, not an append-only log.
- **Isolate with subagents instead of widening one window.** A subagent that reads forty files to answer one question should return a paragraph, not deposit forty files in the parent's context. Fan-out for exploration, summarize for integration. The parent's attention budget is the scarce resource; protect it.
- **Reset at task boundaries.** Long-running sessions accumulate cruft that quietly shapes behavior — abandoned approaches, superseded instructions, error messages from a problem you already solved. A clean context with a well-written handoff artifact beats a rich context with three failed attempts in it. Anthropic's own guidance on long-horizon agents lands here: compaction and structured handoffs, not infinite threads.
- **Prefer pointers to payloads.** Tell the agent where the truth lives and let it fetch. A path, a symbol name, a test command, and a doc index cost tens of tokens; pasting the files costs tens of thousands and buries the signal you cared about.
- **Watch the context cost of your tooling.** Tool definitions, verbose tool results, and MCP server sprawl are context taxes paid before any work happens. Every capability you add should be worth its rent in tokens — and if it isn't used every session, it should be loadable on demand rather than resident.
- **Measure it.** Log token spend per task, the number of turns to completion, and the failure rate by category. Context decisions are engineering decisions, and engineering decisions should have a number attached.

The mental model that makes all of this click: **you are not filling a bucket, you are managing an attention budget with a hard ceiling and a falling exchange rate.** Every token you add should be justified by the behavior it changes.

---

## 6. Workflow-oriented engineering over tool-stacking

There's a particular failure mode that's very easy to fall into right now, because the ecosystem is built to encourage it: **tool-stacking**. New MCP server, new agent framework, new plugin, new model — connect them all, and surely capability follows.

It doesn't, for structural reasons we've already covered. Every tool is a context cost and a selection problem. Anthropic's data on tool bloat shows both failure modes at once: five servers with 58 tools consuming ~55K tokens before the conversation starts, plus measurable accuracy loss from near-duplicate tool names crowding the selection space. Their fix wasn't a better model — it was search-then-load, programmatic tool calling to keep intermediate results out of the window, and usage examples instead of raw schemas.

The disciplined alternative is to design from the workflow backward:

1. **Name the workflow.** "Investigate a production alert and propose a fix," "add a feature behind a flag with tests and a changelog entry," "migrate a dependency across the repo." Concrete, repeatable, and owned by someone.
2. **Write the loop on paper first.** Trigger, steps, artifacts produced, verification at each step, definition of done, escalation conditions. If you can't describe the loop, no amount of tooling will save you — you'll be automating confusion.
3. **Find the actual bottleneck.** Is it missing context, missing capability, or missing verification? These have three completely different fixes. Adding a tool to a verification problem is the most common and most expensive mistake in the space.
4. **Add exactly one capability, then measure.** Did turn count fall? Did failure rate fall? Did token cost rise? If a new integration doesn't move a number, it's context tax. Remove it.
5. **Encode the loop as a repeatable primitive.** A skill, a command, a CI job, a template. The workflow should be invocable by name and identical on every run.
6. **Convert every repeat failure into a structural fix.** A failure that happens twice in the same way is not a prompting problem, it's a missing test, a missing lint rule, a missing doc, or a missing tool. Fix it at the lowest layer that prevents recurrence — and prefer the executable layer over the prose layer.

That last step is the whole game. A team that converts failures into tests and lint rules compounds; a team that converts failures into longer prompts plateaus, because each new instruction is competing for the same attention budget as everything else they've ever written down.

---

## 7. The feedback loop is the unit of work

If you take one thing from this article, take this: **the tight feedback loop is the atomic unit of AI-assisted engineering.** Not the file. Not the prompt. The loop.

A loop has four parts, and all four must exist:

- **Intent** — acceptance criteria precise enough to be wrong about.
- **Action** — the agent's attempt, with enough permission to actually attempt something.
- **Observation** — machine-readable evidence of whether it worked: tests, types, lints, logs, traces, screenshots, runtime behavior.
- **Correction** — an automatic path back to action, or a clean escalation to a human.

Break any link and you're back to micro-management. No intent, and you're reviewing everything by hand because there was never a contract. No observation, and the agent asserts success you must verify yourself. No correction path, and every failure becomes a meeting. This is why "the agent wrote bad code" is almost never an accurate diagnosis — it's usually a missing observation or a vague intent, diagnosed at the wrong layer.

The practical payoff of strong loops is that the economics of being wrong change. When a bad output costs thirty seconds of automated verification, you can let the agent attempt aggressively and iterate. When a bad output costs a human forty-five minutes of review, you must supervise every step. **Autonomy isn't something you grant a model. It's something your verification earns.** Every test you write and every lint rule you add buys back a slice of your own attention.

---

## 8. What this looks like on a Monday

Nothing above requires a re-architecture. It requires a different default for where your next hour goes.

- Take the three things you've corrected most often this month and move them down a layer: a lint rule, a test, or a line in `AGENTS.md`. Stop correcting them in chat.
- Replace your instructions file with a 100-line index — build, test, run one test, architecture map, definition of done, links to deeper docs. Delete the rest; it wasn't helping.
- Pick your highest-volume workflow and write its acceptance criteria as a checklist a machine could evaluate. You will immediately discover which parts of "done" were never defined.
- Add the cheapest missing observation to your loop. If agents can't see the app run, get them a screenshot. If they can't see failures, give them the log query. If it isn't a test they can run, make it one.
- Audit your connected tools. Remove everything not used this week. Note what broke; that tells you what was load-bearing.
- Time-box a session where you don't tell the agent *how*. Give it intent and verification, and see how far it gets. The gap between that result and your usual supervision is the size of the harness you haven't built yet.

---

## The close: the job moved up a layer, and it isn't coming back

The uncomfortable part of this argument is that it asks developers to give up something that feels like craft. Reading every diff, dictating every change, holding the entire implementation in your head — that's the texture of senior engineering as most of us learned it. Letting go feels like lowering standards.

It's the opposite. You're raising them, and relocating them.

You're moving from *"is this line correct?"* to *"is this system capable of producing correct lines and proving it?"* That's a harder question, an older question, and one that scales. It's the question platform teams have always asked — and OpenAI's own summary of the shift is that their hardest problems are now about "designing environments, feedback loops, and control systems" rather than about code.

The developers who will be most valuable over the next few years are not the fastest typists or the people with the longest prompt libraries. They're the ones who can look at a workflow and see where the context is missing, where the verification is absent, and where a constraint should be executable instead of aspirational — then go build that, and let the model do the typing at a volume no human ever could.

Stop managing files. Start designing the loop that writes them.

---

### Further reading

- OpenAI, *Harness engineering: leveraging Codex in an agent-first world* (Ryan Lopopolo) — the case study behind most of the harness claims here: agent legibility, custom linters with remediation messages, repository-as-system-of-record, throughput-driven process change.
- Anthropic, *Effective context engineering for AI agents* — context rot, the finite attention budget, and the "smallest set of high-signal tokens" principle.
- Anthropic, *Introducing advanced tool use* — tool search, programmatic tool calling, and the measured cost of tool-definition bloat (including the 49% → 74% and 79.5% → 88.1% accuracy deltas).
- Anthropic, *Managing context on the Claude Developer Platform* — context editing and the memory tool, with the 29% / 39% performance and 84% token-reduction figures from internal evaluations.
