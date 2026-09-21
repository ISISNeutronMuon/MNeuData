---
status: "{proposed | rejected | accepted | deprecated | … | superseded by ADR-NNNN}"
date: "{YYYY-MM-DD when the decision was last updated}"
decision-makers: "{everyone involved in the decision}"
consulted: "{subject-matter experts consulted, with two-way communication}"
informed: "{people kept up to date, with one-way communication}"
---

<!--
Authoring conventions for this repo's ADRs:
- Do not hard-wrap prose at a character limit. Each line is a paragraph / logical
  item; a new line starts only when a new thing starts.
- Keep the "N." numeric prefix in the H1 title (matches filenames + cross-refs).
- Group Considered Options and Pros and Cons by competing decision when an ADR
  makes more than one independent decision. Use "### <decision group>" with
  "#### <option>" beneath it. For a single decision, drop the group subheadings
  and list options directly under "### <option>".
- Mark the selected option's heading with "(Chosen option)".
- Use Good / Neutral / Bad bullets. Do not add "Change needed to adopt" bullets.
-->

# N. {short title, representative of solved problem and found solution}

## Context and Problem Statement

{Describe the context and problem statement in two or three sentences, or as an illustrative story. You may want to articulate the problem as a question. Make the scope explicit by pointing at the structural architecture elements involved.}

## Decision Drivers

* {decision driver 1, e.g. a desired quality, faced concern, constraint or force}
* {decision driver 2}
* … <!-- numbers of drivers can vary -->

## Considered Options

<!-- Single decision: list options directly. -->
* {title of option 1}
* {title of option 2}
* {title of option 3}

<!-- Multiple competing decisions: group them, e.g.
{Decision group A}:

* {option A1}
* {option A2}

{Decision group B}:

* {option B1}
* {option B2}
-->

## Decision Outcome

Chosen option: **"{title of chosen option}"**, because {justification, e.g. it is the only option meeting a k.o. criterion / resolves force {force} / comes out best (see below)}.

### Consequences

* Good, because {positive consequence, e.g. improvement of a desired quality}
* Neutral, because {consequence that weighs neither for good nor bad}
* Bad, because {negative consequence, e.g. compromising a desired quality}
* … <!-- numbers of consequences can vary -->

### Confirmation

{Describe how implementation / compliance of the ADR can be confirmed — an automated or manual fitness function, a design/code review, a test, a `kubectl`/`curl` check, a `terraform plan` showing no drift, etc.}

## Pros and Cons of the Options

<!-- Single decision: use "### <option>" per option.
     Multiple competing decisions: use "### <decision group>" then
     "#### <option>" per option, mirroring Considered Options. -->

### {title of option 1} (Chosen option)

* Good, because {argument a}
* Good, because {argument b}
* Neutral, because {argument c}
* Bad, because {argument d}

### {title of other option}

* Good, because {argument a}
* Neutral, because {argument b}
* Bad, because {argument c}

## More Information

{Optional. Additional evidence/confidence for the outcome, team agreement, when/how the decision should be realised or re-visited, and links to related decisions and resources.}
