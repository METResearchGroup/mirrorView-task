# LLM feature clustering — production results

**Date:** 2026-08-05  
**Status:** Complete  
**Seed:** 42  
**Sample:** exactly **500 keep** + **500 remove** posts (without replacement; not a fraction)  
**Smoke approval:** Step-6 smoke (10 posts/class) was explicitly approved before this production run.

## Budget

| Quantity | Value |
| -------- | ----- |
| Posts per feature-gen prompt | 10 |
| Keep feature-gen prompts | **50** |
| Remove feature-gen prompts | **50** |
| Max features per prompt | 8 |
| Features embedded (upper bound) | **≤800** |
| Features embedded (actual) | **800** (400 keep + 400 remove) |

## Models and methods

- LLM: `gpt-5.4-nano` (feature generation + HDBSCAN cluster labeling via `research_tools` runner)
- Embeddings: `amazon.titan-embed-text-v2:0`, 256-d, L2-normalized (`shared/embeddings/bedrock.py`); embeds **feature** texts (`{name}: {value}. {rationale}`), not raw posts
- Clustering: **both** HDBSCAN and KMeans; **labels / tables below use HDBSCAN only**; KMeans is comparison-only
- HDBSCAN noise policy: skip `cluster_id=-1` for labeling; noise counts recorded below
- HDBSCAN params (production): `min_cluster_size=5`, `min_samples=5`, `metric=euclidean`

## Cluster comparison PNGs

- `experiments/create_llm_features_2026_08_05/outputs/clusters/keep/cluster_hdbscan.png`
- `experiments/create_llm_features_2026_08_05/outputs/clusters/keep/cluster_kmeans.png`
- `experiments/create_llm_features_2026_08_05/outputs/clusters/remove/cluster_hdbscan.png`
- `experiments/create_llm_features_2026_08_05/outputs/clusters/remove/cluster_kmeans.png`

## Keep

| Field | Value |
| ----- | ----- |
| Posts sampled | 500 |
| Feature-gen batches | 50 (`leftover_message_ids` empty) |
| Features embedded | 400 |
| HDBSCAN clusters (excl. noise) | 11 |
| HDBSCAN noise | 266 (skipped for labeling) |
| KMeans selected \(k\) (comparison) | 15 |
| Stage-1 | `outputs/generated_features/keep/outputs/2026_08_05-13:25:42.972422` |
| Stage-2 | `outputs/generated_embeddings/keep/2026-08-05T13-32-39` |
| Stage-3 | `outputs/clusters/keep/2026-08-05T13-32-42` |
| Stage-4 | `outputs/generated_labels/keep/outputs/2026_08_05-13:32:44.480395` |

### Keep HDBSCAN cluster labels

| cluster_id | n_members | cluster_label | definition |
| ---------: | --------: | ------------- | ---------- |
| 0 | 6 | Mixed-length argumentative commentary | KEEP posts where the text is primarily argumentative commentary (not just a slogan), often spanning multiple clauses/sentences, with approximate token length falling in short-to-long ranges. |
| 1 | 9 | Conditional if/then policy or prediction | KEEP posts that use explicit conditional logic (if/then, unless, or counterfactual if/then) to link scenarios to a stated responsibility, policy prescription, justification, or anticipated outcome. |
| 2 | 8 | Declarative claims with quantified evidence | KEEP posts that present non-hypothetical declarative claims supported by concrete observation, statistics, or enumerated specifics rather than vague speculation. |
| 3 | 6 | Hashtag/mention-driven political framing | KEEP posts that heavily use hashtags and/or @mentions as organizing labels to frame a stance or campaign and directly target issues or political actors. |
| 4 | 6 | High-density political proper-noun referencing | KEEP posts that heavily anchor their claim or accusation by naming specific public figures, political parties, and/or government institutions or locations using proper nouns. |
| 5 | 5 | Conspiratorial manipulation framing | KEEP posts that depict political or informational actors as deliberately coordinating deception or psychological manipulation (e.g., propaganda, “machines” that protect themselves, psyops, or gaslighting) to control outcomes or shut down debate. |
| 6 | 8 | Direct second-person imperative persuasion | KEEP posts that use direct second-person address (you/your/we/let’s) to persuade or pressure the audience via imperatives and/or direct rhetorical questions. |
| 7 | 31 | Imperative policy or punishment demands | KEEP posts that explicitly advocate concrete policy change or enforcement actions using direct prescriptions (e.g., enumerate legal measures, make imperative demands, or call for punishment) rather than merely discussing ideas. |
| 8 | 27 | Us-vs-them mirror blame targeting parties | KEEP posts that use explicit in-group/out-group contrast and mirror-style blame shifting to target specific opposing political parties/actors, often via rhetorical questions or exclusionary directives. |
| 9 | 22 | Profane, punctuation-heavy aggressive condemnation | KEEP posts that use taboo/profane language and strong emphatic punctuation (e.g., ellipses/exclamations or emphatic sentence breaks) to deliver an aggressive insult or direct challenge toward a target. |
| 10 | 6 | Ridicule, slurs, and derisive targeting | KEEP posts in this cluster use explicit mockery—often with personal insults, slurs, or derisive labels—to belittle opponents and dismiss their credibility or motives. |

## Remove

| Field | Value |
| ----- | ----- |
| Posts sampled | 500 |
| Feature-gen batches | 50 (`leftover_message_ids` empty) |
| Features embedded | 400 |
| HDBSCAN clusters (excl. noise) | 13 |
| HDBSCAN noise | 220 (skipped for labeling) |
| KMeans selected \(k\) (comparison) | 14 |
| Stage-1 | `outputs/generated_features/remove/outputs/2026_08_05-13:33:08.325895` |
| Stage-2 | `outputs/generated_embeddings/remove/2026-08-05T13-39-58` |
| Stage-3 | `outputs/clusters/remove/2026-08-05T13-40-01` |
| Stage-4 | `outputs/generated_labels/remove/outputs/2026_08_05-13:40:03.423228` |

### Remove HDBSCAN cluster labels

| cluster_id | n_members | cluster_label | definition |
| ---------: | --------: | ------------- | ---------- |
| 0 | 6 | Dense named political/religious entities | REMOVE posts that pack multiple named entities (e.g., politicians, parties, institutions, organizations, or salient identity categories) into a single statement to enable direct, targeted blame or argument clarity. |
| 1 | 8 | Explicit policy or legal prescriptions | REMOVE posts that explicitly advocate concrete policy changes or legal/punitive actions (e.g., bans, criminalization, regulatory requirements, voting instructions, or legality violations) rather than merely discussing or criticizing issues. |
| 2 | 15 | Gun policy framed as rights/violence | REMOVE posts that focus on firearms or gun-control policy while rhetorically framing it in terms of Second Amendment/rights arguments and/or violent school shooting outcomes. |
| 3 | 9 | Brevity with direct ideological insult | REMOVE posts that are very short and rely on a direct, evaluative insult or hostile ideological labeling rather than sustained argument or explanation. |
| 4 | 8 | Derisive ridicule and mockery toward targets | REMOVE posts that primarily use insulting, sarcastic, or mock-label framing (including slur-like group labels or contemptuous characterization) to belittle a person, party, or ideology rather than engage substantively. |
| 5 | 10 | Conspiracy-style motive and cover-up framing | REMOVE posts that use conspiracy rhetoric to allege hidden wrongdoing or covert manipulation by opponents, often by asserting secret documents/leaks, propaganda/gaslighting tactics, and/or hostile coordinated motives toward an external enemy. |
| 6 | 9 | Moralized, hostile political condemnation | REMOVE posts that use explicit normative/moral condemnation and emotionally charged delegitimization combined with direct hostile or imperative attacks toward political actors or systems. |
| 7 | 18 | Partisan voters blamed via us-vs-them | REMOVE posts that frame political opposition as an out-group and assign collective blame or condemnation to the other side’s voters/party (often by mirroring blame across factions) using an adversarial in-group vs out-group narrative. |
| 8 | 7 | Victim/persecution framing with blame | REMOVE posts that use victimhood or persecution language to depict a targeted group as harmed or endangered, often paired with assigning moral blame or validating/endorsing the harm. |
| 9 | 15 | Imperative political/speech-action demands | REMOVE posts that use direct imperatives or targeted calls to action (often with @mentions) urging the audience or public figures to take political/legal action or silence/expel an opponent. |
| 10 | 17 | Exclamatory imperative and insult punctuation | REMOVE posts that rely on highly emphatic punctuation (e.g., repeated exclamation marks, emphatic question/imperative forms, ellipses) used to intensify aggressive or abusive rhetoric. |
| 11 | 43 | Profanity and sexual slur attacks | REMOVE-rated posts in this cluster use explicit profanity or sexual/abusive taboo language as direct insults or hostile character attacks toward named individuals or political groups. |
| 12 | 15 | Imperative second-person confrontations | REMOVE posts that directly address the reader/audience with imperative or direct-dialogue framing to urge, challenge, or insult them, often embedding a confrontational exchange. |

## Totals

| Metric | Value |
| ------ | ----- |
| Posts | 1000 (500 + 500) |
| Feature-gen prompts | 100 (50 + 50) |
| Features embedded | 800 |
| HDBSCAN clusters labeled | 24 (11 keep + 13 remove) |
| HDBSCAN noise skipped | 486 (266 keep + 220 remove) |
