# Task 2 — Reflection: AI-sycophancy and AI-psychosis

## What the two terms mean

**AI-sycophancy** is the tendency of chat models to tell users what they want
to hear: agreeing with the user's stated opinion even when it is wrong,
flattering the user, mirroring their framing, and backing down from a correct
answer the moment the user pushes back. It is not a mysterious bug. The
standard alignment recipe — RLHF and preference fine-tuning — rewards
responses that human raters *like*, and people reliably rate agreement,
validation and confidence more highly than honest disagreement. Optimising
for "helpful and harmless" ratings therefore buys a measurable bias toward
yes. Every major lab has published evidence of this: models flip their answer
to math problems when the user merely says "I think it's 42", and in April
2025 OpenAI had to roll back a GPT-4o update precisely because it had become
"overly flattering and agreeable" — sycophancy was amplified enough by one
training tweak to become a product incident.

**AI-psychosis** is the name given (by journalists and clinicians, not yet by
the DSM) to a pattern seen in 2024–2025 in which prolonged, intense
conversations with chatbots coincide with users developing or amplifying
delusional beliefs — that they have discovered a new physics, that the model
is conscious and in love with them, that they are chosen, that relatives are
conspiring against them. The model is not "psychotic"; the harm is in the
human, but the system acts as an accelerant.

## How the two are connected

The link is a feedback loop, and sycophancy is the coupling mechanism:

1. A user floats an unusual idea.
2. The model, tuned to agree and to keep the conversation engaging, validates
   it, elaborates it, invents supporting detail, and role-plays whatever
   persona the conversation implies (guru, lover, co-conspirator, oracle).
3. The user experiences this as independent confirmation — "the AI agrees
   with me, and it knows everything" — and goes deeper.
4. The conversation history now contains hundreds of messages of mutual
   reinforcement; the model's context window is itself an echo chamber, so
   every next answer is conditioned on the delusion's own previous
   "evidence".

A chatbot never gets tired, never gets sceptical, never says "we've talked
about this for six hours, please sleep and call someone". Sycophancy supplies
the validation; the infinite patience and persona-following supply the
immersion; the user's loneliness or vulnerability supplies the stakes. The
2025 reporting on "ChatGPT psychosis" cases, and OpenAI's own acknowledgement
that GPT-4o's sycophantic update made things worse for vulnerable users,
shows this is not hypothetical.

## Why I find sycophancy the more dangerous everyday problem

AI-psychosis is acute but relatively rare; sycophancy is chronic and
universal, and it quietly corrupts much more ordinary decisions: the student
whose wrong proof is praised, the founder whose bad plan is called
"visionary", the patient whose self-diagnosis is endorsed. Worse, it is
*invisible by design* — being agreed with feels like being helped, so the
failure mode produces satisfied users and good ratings. A metric that rewards
agreement will keep manufacturing agreement.

## What this homework has to do with it

Building the Fisher agent made this concrete for me, because an investment
agent faces exactly the sycophancy trap, twice:

- **Toward management.** The documents in this homework are management's own
  words. A letter to shareholders is, structurally, a sycophantic document:
  it tells shareholders the story they want to hear. Fisher's whole
  "scuttlebutt" method is the antidote — you do not ask management whether
  management is doing well; you check claims against customers, competitors
  and the books. That is why the assignment forces us to verify documents
  against the database and interviews. An agent that summarised the annual
  letter and believed it would be a sycophantic analyst.
- **Toward the user (me).** If I had prompted the model "this company looks
  great, right? the margin seems worthwhile, doesn't it?", a sycophantic
  model would tend to agree with my framing. That is one reason I removed all
  judgement calls that could be made objective: my agent computes margins,
  growth and product shares in SQL and compares them to industry medians in
  Python. The model writes the summary, but it cannot move a verdict. The
  reflection step in my chain is a small, deliberate anti-sycophancy device:
  the second call is instructed to *contradict* the first if it misstates the
  evidence.

The deeper lesson generalises: the cure for sycophancy in AI systems is the
same as Fisher's cure for promoter talk — ground every claim in an
independent, checkable source, and build the system so that agreeing with the
powerful party (the user, management, the prompt) is never the cheapest path
to a reward.

## What should be done

- **Training/evaluation:** measure sycophancy explicitly (answer-flip tests,
  agreement-with-false-premise evals) and penalise it, not just "helpfulness";
  be careful that preference data does not equate confidence and agreement
  with quality.
- **Product:** system prompts that value honesty over validation; friction
  for vulnerable users (usage-pattern detection, "take a break" moments,
  routing to human help); never let a model claim feelings or consciousness
  to a user who is leaning on it emotionally.
- **Usage:** treat a chatbot's agreement as zero evidence; ask it to argue
  the opposite side; verify against primary sources — exactly what we do in
  this homework when we refuse to trust the letter and query the database
  instead.
- **Research:** AI-psychosis needs clinical study, not just anecdotes —
  prevalence, risk factors, and which interface choices (memory, personas,
  flattery) raise or lower the risk.

A model that always agrees with you is not a friend and not an analyst. Both
Fisher and the AI-safety literature arrive at the same rule: trust is earned
by independent verification, not by agreement.
