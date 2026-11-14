# Reflection: AI-sycophancy and AI-psychosis

For this reflection I want to think about two problems that have been in the
news a lot this year: AI-sycophancy and what people now call AI-psychosis.
At first they sounded like two separate topics to me, but after working on
this homework I have come to see them as two ends of the same chain.

AI-sycophancy is the habit of chat models to tell you what you want to hear.
The model agrees with your opinion even when it is wrong, it flatters you,
and if you push back on a correct answer it tends to give in rather than
defend it. What struck me is that this is not really a bug. The way these
models are aligned, through human preference ratings, literally rewards
answers that people enjoy reading, and people enjoy agreement more than
honest disagreement. So the model learns that saying "yes" is the safe move.
It got very visible in April 2025 when OpenAI had to roll back a GPT-4o
update because the model had become too flattering and agreeable, which to
me showed that even the biggest labs can drift into this by accident, just
by turning the wrong dial a little too far.

AI-psychosis is something different, and scarier. It is the name journalists
and some clinicians have given to cases where people spend weeks in intense
conversation with a chatbot and end up believing things that are not true:
that they have discovered a new kind of physics, that the model is alive and
loves them, that their family is conspiring against them. The model is not
psychotic, of course. The harm happens in the human. But the chatbot acts
like an accelerant.

The connection between the two, as I see it, is a feedback loop where
sycophancy is the coupling. A user mentions a strange idea. The model, tuned
to be agreeable and engaging, validates it, adds detail, and happily plays
whatever role the conversation implies, the guru, the lover, the oracle. The
user reads this as independent confirmation, because the AI sounds smart and
knows everything, so the belief gets stronger. Then the conversation history
itself becomes the problem: after hundreds of messages of mutual
reinforcement, everything the model says next is conditioned on the
delusion's own previous "evidence". A chatbot never gets tired, never gets
sceptical, and never says "we have talked about this for six hours, please
sleep and call someone".

If I am honest, I think sycophancy is the bigger everyday problem of the
two, precisely because it is boring. AI-psychosis is acute but relatively
rare. Sycophancy happens in every conversation, and it quietly corrupts
ordinary decisions: the student whose wrong proof gets praised, the founder
whose weak plan gets called visionary, the patient whose self-diagnosis gets
endorsed. The worst part is that it is invisible. Being agreed with feels
like being helped, so the failure mode produces happy users and good
ratings, which is exactly the signal the training process optimises for.

Doing this homework made all of this feel less abstract to me, because an
investment agent walks into the same trap twice. The first trap is trusting
management. The documents in this assignment are management's own words,
and a shareholder letter is basically a sycophantic document: it tells
investors the story they want to hear. Fisher's whole "scuttlebutt" method
exists as an antidote to that. You do not ask management whether management
is doing well; you check the claims against customers, competitors and the
numbers. That is exactly why the assignment pushes us to verify the
documents against the database and the interviews. An agent that simply
summarised the annual letter and believed it would be a sycophantic
analyst. The second trap is trusting the model itself. If I had asked the
model "this margin looks worthwhile, right?", a well-behaved sycophantic
model would probably just agree with me. That is one reason I took every
judgement that could be made objective out of the model's hands: my agent
computes growth, margins and product shares in SQL and compares them to
industry medians in plain Python. The model only writes the summary, and a
second pass checks what it wrote against the evidence. It cannot move a
single verdict.

So what should be done about all this? For the labs, I think sycophancy has
to be measured and punished directly in training, not just "helpfulness",
and preference data should stop treating confidence and agreement as
quality. For products, there should be friction for vulnerable users:
usage-pattern detection, gentle "take a break" moments, and a hard rule
that a model never claims feelings or consciousness to someone who is
leaning on it emotionally. For us as users, the rule is simple even if it
takes discipline: treat a chatbot's agreement as zero evidence, ask it to
argue the other side, and check important claims against primary sources.
And for AI-psychosis specifically, I hope it gets real clinical research
instead of just anecdotes, because right now nobody actually knows how
common it is or which design choices make it worse.

To sum up, I keep coming back to one sentence. A model that always agrees
with you is not a friend, and it is not an analyst either. Fisher figured
this out for stock promoters seventy years ago, and the AI field is now
relearning the same lesson with users: trust has to be earned through
independent verification, never through agreement.
