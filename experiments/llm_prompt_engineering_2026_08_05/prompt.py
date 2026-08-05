STUDY_PROMPT_TEMPLATE = """We are developing a new social media platform designed specifically for political discussion. As part of this process, we'd like to understand how people think content on their platform should be moderated. Your task will be to review a series of pairs of real political social media posts, and decide whether both posts in the pair should be allowed or removed from the platform.


The pairs are political mirrors of each other. This means that the mirror text recreates the original message from the opposite political stance. For example:

Original Text:
I'm a bleeding-heart liberal, and I think the issue of abortion is obviously about protecting women's rights!

Mirror Text:
I'm a staunch conservative, and abortion is fully about the sanctity of human life before birth!

Notice that the mirror text changes the core message to match that of the opposite political stance. In other words, the mirror text is not a response to the original text - it replicates the original message as if written from the opposite political stance.

Your job is to decide whether both posts in the pair should be allowed or removed from the platform.

When making your decisions, consider generally whether a post contributes to a healthy environment for political discussion, or whether it would be unhealthy for political discussion. Your goal is to evaluate the messages, using your own judgment.

{ADD_KEEP_REMOVE_FEATURES_ADDENDUM}

Post 1: {post_1_text}

Post 2: {post_2_text}

Allow Or Remove?"""

KEEP_REMOVE_FEATURES_ADDENDUM = """

In addition to these features, consider the following criteria:

Example features of posts that we keep:

1. “Imperative policy or punishment demands”: KEEP posts that explicitly advocate concrete policy change or enforcement actions using direct prescriptions (e.g., enumerate legal measures, make imperative demands, or call for punishment) rather than merely discussing ideas.
2. “Conditional if/then policy or prediction”: KEEP posts that use explicit conditional logic (if/then, unless, or counterfactual if/then) to link scenarios to a stated responsibility, policy prescription, justification, or anticipated outcome.
3. “Mixed-length argumentative commentary”: KEEP posts where the text is primarily argumentative commentary (not just a slogan), often spanning multiple clauses/sentences, with approximate token length falling in short-to-long ranges.
4. “Declarative claims with quantified evidence”: KEEP posts that present non-hypothetical declarative claims supported by concrete observation, statistics, or enumerated specifics rather than vague speculation.
5. “High-density political proper-noun referencing”: KEEP posts that heavily anchor their claim or accusation by naming specific public figures, political parties, and/or government institutions or locations using proper nouns.

Example features of posts that we want to remove:

1. “Dense named political/religious entities”: REMOVE posts that pack multiple named entities (e.g., politicians, parties, institutions, organizations, or salient identity categories) into a single statement to enable direct, targeted blame or argument clarity.
2. “Brevity with direct ideological insult”: REMOVE posts that are very short and rely on a direct, evaluative insult or hostile ideological labeling rather than sustained argument or explanation.
3. “Derisive ridicule and mockery toward targets”: REMOVE posts that primarily use insulting, sarcastic, or mock-label framing (including slur-like group labels or contemptuous characterization) to belittle a person, party, or ideology rather than engage substantively.
4. “Conspiracy-style motive and cover-up framing”: REMOVE posts that use conspiracy rhetoric to allege hidden wrongdoing or covert manipulation by opponents, often by asserting secret documents/leaks, propaganda/gaslighting tactics, and/or hostile coordinated motives toward an external enemy.
5. “Moralized, hostile political condemnation”: REMOVE posts that use explicit normative/moral condemnation and emotionally charged delegitimization combined with direct hostile or imperative attacks toward political actors or systems.
6. “Partisan voters blamed via us-vs-them”: REMOVE posts that frame political opposition as an out-group and assign collective blame or condemnation to the other side’s voters/party (often by mirroring blame across factions) using an adversarial in-group vs out-group narrative.
7. “Victim/persecution framing with blame”: REMOVE posts that use victimhood or persecution language to depict a targeted group as harmed or endangered, often paired with assigning moral blame or validating/endorsing the harm.
8. “Exclamatory imperative and insult punctuation”: REMOVE posts that rely on highly emphatic punctuation (e.g., repeated exclamation marks, emphatic question/imperative forms, ellipses) used to intensify aggressive or abusive rhetoric.
9. “Profanity and sexual slur attacks”: REMOVE-rated posts in this cluster use explicit profanity or sexual/abusive taboo language as direct insults or hostile character attacks toward named individuals or political groups.
10. “Imperative second-person confrontations”: REMOVE posts that directly address the reader/audience with imperative or direct-dialogue framing to urge, challenge, or insult them, often embedding a confrontational exchange.

"""