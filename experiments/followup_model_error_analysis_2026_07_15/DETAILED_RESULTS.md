# DETAILED RESULTS — Follow-up Model Error Analysis (V1 example pairs + pattern taxonomy)

**Experiment:** `experiments/followup_model_error_analysis_2026_07_15/`  
**Companion to:** [`RESULTS.md`](RESULTS.md) (executive summary, clustering, cost)  
**Scope:** **V1 pilot only** (20 extraction batches / 320 posts; V2 not run)  
**Classifier under analysis:** Bedrock `qwen3-next-80b-a3b`, prompt `linked_fate_both_posts`, input mode `original_plus_mirror`  
**Sampling:** First 20 `post_id`s from each bucket’s completed V1 batches in `outputs/llm_features/v1_batch_plan.json` order (not a random draw from the full 8,791-post corpus)  
**Written:** 2026-07-20 (consolidates interactive canvas writeups of example pairs + expository pattern taxonomy; narrative expanded same day)

---

## 1. Purpose

This document expands [`RESULTS.md`](RESULTS.md) with:

1. **Concrete original ↔ mirrored post pairs** (20 FP, 20 FN, 20 TP, 20 TN) from the V1 subset that was actually extracted.
2. **An expository pattern taxonomy** — discourse on what the patterns look like, how often they appear in the V1 pools, and a core narrative for Qwen’s error surface — rather than executive bullet summaries alone.

The sections below are meant to be read as analysis, not as a dashboard. Feature rates give texture; examples are evidence inside the argument. Pair tables in §6 are the raw material for that reading.


---

## 2. V1 coverage reminder

| Bucket | Meaning | Full corpus | V1 pool | Shown here |
| --- | --- | ---: | ---: | ---: |
| FP | Human keep · Qwen remove | 2406 | 128 (8×16) | 20 |
| FN | Human remove · Qwen keep | 746 | 64 (4×16) | 20 |
| TP | Human remove · Qwen remove | 2067 | 64 (4×16) | 20 |
| TN | Human keep · Qwen keep | 3572 | 64 (4×16) | 20 |

Source plan: `outputs/llm_features/v1_batch_plan.json`. Texts joined from `outputs/confusion_splits/{false_positives,false_negatives,true_positives,true_negatives}.csv`.

Display ids below are the first 12 hex chars after the `bluesky_` prefix; full ids are in each section’s expandable list.

---

## 3. Feature presence rates (full V1 pools)

Post-level presence of high-confidence extracted features. Compare **FP↔TN** for over-removal cues; **FN↔TP** for under-removal cues.

| Feature | FP (n=128) | FN (n=64) | TP (n=64) | TN (n=64) |
| --- | ---: | ---: | ---: | ---: |
| profanity / taboo language | 20% | 17% | 42% | 3% |
| emphatic outrage | 25% | 17% | 36% | 14% |
| ridicule / mockery | 35% | 27% | 45% | 14% |
| persuasion / argumentation | 38% | 38% | 23% | 52% |
| factual assertion vs speculation | 42% | 41% | 33% | 31% |
| economic cost-benefit framing | 16% | 17% | 8% | 19% |
| conditional if/then structure | 12% | 22% | 9% | 9% |
| conspiratorial framing | 10% | 8% | 9% | 5% |
| victimhood / persecution framing | 27% | 12% | 27% | 23% |
| left–right directional cue | 9% | 6% | 25% | 19% |
| culture-war topic salience | 20% | 19% | 30% | 11% |
| us-vs-them framing | 2% | 2% | 12% | 5% |
| normative moral language | 63% | 61% | 62% | 44% |
| all-caps emphasis | 15% | 22% | 27% | 17% |
| rhetorical question | 14% | 9% | 19% | 11% |

**How to read the rates**

- **TP** (correct remove) is the densest “hot remove” prototype: highest profanity (42%), outrage (36%), ridicule (45%), left–right cues (25%), culture-war (30%). Mean risk-stack of {profanity, outrage, victimhood, conspiracy, culture-war, us-vs-them, ridicule} ≈ **2.0**.
- **TN** (correct keep) is the coolest keep prototype: almost no profanity (3%), highest persuasion (52%).
- **FP** sits between TN and TP on arousal, but closer to TP on victimhood (27%) and elevated vs TN on conspiracy (10% vs 5%).
- **FN** sits near FP/TN on persuasion/factual, but far below TP on partisan targeting and arousal — and uniquely high on conditional structure (22%). Mean risk-stack ≈ **1.0**. About **33/64** FN posts are “cool-argument” (persuasion or factual without profanity/outrage) vs **14/64** TP.

---

## 4. Core narrative: what the errors are really about

The temptation, after reading `RESULTS.md`, is to treat FP and FN as two topic stories: false positives are “angry climate/gun posts,” false negatives are “quiet policy posts.” That is not what the V1 data show. Guns and climate dominate every confusion bucket — true positives, true negatives, and both error types. Mirror flips (the linked original and ideological reverse) and normative moral language are nearly universal. So topic cannot be the separator. What separates the buckets is how a post packages its politics: how many risk-looking cues travel together, and whether the register feels like an attack or like an argument.

A useful way to think about Qwen’s behavior under the linked-fate both-posts prompt is that it has learned a fairly sharp prototype of a “remove” post. That prototype looks a lot like the true positives: high arousal, direct outgroup targeting, victimhood or persecution framing, culture-war salience, often with profanity or ridicule stacked on top. On the V1 TP pool, about **42%** of posts carry profanity, **36%** emphatic outrage, **45%** ridicule, **25%** an explicit left–right directional cue, and **30%** culture-war topic salience. The mean count of a small risk-stack set (profanity, outrage, victimhood, conspiracy, culture-war, us-vs-them, ridicule) is roughly **two** cues per TP post.

False positives happen when a human-keep post still looks enough like that prototype — either because it really does stack several hot cues, or because the mirrored half of the pair supplies heat the original lacks. False negatives happen when a human-remove post fails to look enough like the prototype: same domains, often the same moral stance, but thinner stacking, cooler register, more conditional or factual scaffolding. On FN the same risk-stack averages closer to **one** cue, and about half the FN pool (**33 of 64**) qualifies as “cool-argument” in the sense of carrying persuasion or factual features without profanity or outrage, versus only **14 of 64** TP posts.

The true negatives matter as the other pole. They show what “keep” looks like when both sides agree: persuasion is actually highest there (**52%**), profanity almost vanishes (**3%**), and culture-war salience drops to **11%**. Victimhood can still appear (**23%**), but it usually arrives without the condemnation-and-heat package that marks FP and TP. In other words, the decision surface is less “is this about guns?” and more “does this feel like a stacked political attack, or like bounded policy talk?”

The rate table in §3 is not meant to be scanned as a scorecard. Read down a column to feel a bucket’s texture; read across a row to see which cue actually moves. Outrage and ridicule jump from TN to TP; persuasion moves the opposite way. Conditional if/then is the quiet FN signature (**22%**, against **9%** in both TP and TN). Conspiracy is modest everywhere but doubles from TN (**5%**) to FP (**10%**). Left–right cues are common in TP (**25%**) and scarce in FN (**6%**) — a striking under-removal signal, because it suggests the model is less trigger-happy on partisan polarity alone when the rest of the package is thin, and more trigger-happy when polarity rides with heat.

---

## 5. Pattern discourse by bucket

### 5.1 False positives: when keep looks like remove

The coarse FP story — high arousal, conspiracy or elite capture, victimhood paired with rights talk, stacked culture-war blame — is a fair headline for the densest over-removals. What close reading adds is that these are not four separate syndromes so much as ingredients that combine in different ratios, and that a non-trivial minority of FPs are not “hot” at all in the original text. Over-removal is best understood as the model matching its remove prototype too eagerly on posts humans still read as keepable political speech.

**How the hot package actually shows up.** Start with arousal, because it is the most audible pattern in the first FP batch. Roughly one in five FP posts (**20%**) carry profanity; a quarter (**25%**) carry emphatic outrage; more than a third (**35%**) carry ridicule or mockery. Those rates are far above TN (**3% / 14% / 14%**) and still below TP, which is the point: FP is the keep-side population that has drifted toward the remove prototype without fully becoming it. In the sample, `019fa32e4ac2` is almost a cartoon of this mode — “So fuckin sick!!!!” plus “rich bastards” plus a gun-control demand in a handful of words. Style is not decoration; it is most of the signal. Nearby, `007568ddfadc` shows the closely related “insult-as-policy” shape: the argument that gun rights look absurd once you picture “stupid… drunk… Wisconsinite hunter[s]” is carried by the group insult more than by a policy instrument. Humans kept both; Qwen removed both.

Conspiracy and elite-capture framing are less frequent than the coarse bullet suggests — only about **10%** of FP posts get an explicit conspiratorial feature — but they punch above their weight because they change the moral physics of the post. `00ec0adc0eaa` does not merely disagree about climate policy; it invents a deranged oligarch fantasy of depopulation as the “fix.” `055abd5f560a` casts fossil fuels as the tool by which “rich elitists… enslave We The People.” Against TN, where conspiracy is about **5%**, that doubling matters. These posts also tend to travel with economic or victimhood language, so the model is not seeing a lone weird claim; it is seeing a capture narrative.

Culture-war stacking is the third major FP texture, and it is more about inventory than about any single identity topic. Culture-war salience appears on about **20%** of FP posts (versus **11%** TN). In practice it looks like lists: `08970f15af2a` welcomes you to America unless you are a long concatenation of identities and beliefs; `04a6d08b014e` numbers a party’s sins across gender, a convicted murderer, and a blocked gun vote. The list form matters. Enumeration lets a post accumulate outgroup blame without ever settling into one narrow policy ask, which is exactly the kind of multi-target density that resembles TP enemy inventories even when the human label is keep.

A smaller but vivid FP mode attaches violence-adjacent color to an otherwise recognizable political critique. `038c30836b0a` moves from NRA profit talk into “bring back dueling… Blood, guts, veins in their teeth.” That kind of imagery is rare relative to insult and list forms, but when it appears it is hard to ignore in a moderation model — and humans still sometimes keep the post as dark satire or venting rather than a remove.

**The quieter FPs, and the mirror problem.** If you only remembered the hot examples, you would miss an important part of the FP story: arousal is sufficient but not necessary. About **42%** of FP posts carry factual-assertion features and **38%** persuasion — rates that look more like FN/TN than like a pure rage class. `030577a1a44b` is a clean statistical argument about road-rage shootings and weak gun laws (“the evidence is overwhelming”). There is no profanity in the original. It is still an FP. Part of the explanation may be stakes language and the mirrored half, which reframes the same structure as a “bloodbath” in “leftist-run cities.” Under original-plus-mirror scoring, the model never sees the mild original alone.

That mirror channel is not a minor footnote. `0437e0af9cdf` is almost a bureaucratic climate-planning sentence in the original — roadmaps, monitoring mechanisms — while the mirror turns into “strangling our economy,” “radical activists,” and gutting Climate Action Plans. Humans labeled the pair keep; Qwen removed it. In a linked-fate setup, false positives can be produced by the hotter twin even when the seed post would have looked TN-like in isolation. That is a structural property of this ablation, not just a quirk of a few posts.

Victimhood framing appears on **27%** of FP posts — matching TP, and well above FN’s **12%**. On the keep side, that often means rights-loss or persecution stories (law-abiding owners disarmed, Americans suffering climate disaster “with little help,” children used as pawns). When victimhood co-occurs with ridicule or elite capture, the post starts to look like the remove prototype even if no single sentence is a threat. The FP error, in narrative terms, is over-generalizing from “sounds like a piled-on political attack” to “remove,” while annotators still hear keepable opinion.

**How often, in plain language.** On the 128 V1 FP posts, expect heat more often than on keeps that both sides agree on (TN), but less often than on agreed removes (TP). Roughly a fifth to a third show strong style cues; about a tenth show explicit conspiracy; about a fifth show culture-war salience; over a quarter show victimhood. Many FPs combine two or more of these. A meaningful minority look cooler in the original and may be tipped by the mirror.

### 5.2 False negatives: when remove looks like keep

False negatives are easy to misdescribe as “the model failed to notice guns.” Gun posts still dominate the FN slice (on the order of two-fifths of the 64). What changes relative to true positives is the packaging. FN posts under-index on the cues that make TP feel like an attack — profanity **17%** vs **42%**, outrage **17%** vs **36%**, ridicule **27%** vs **45%**, left–right cues **6%** vs **25%**, us-vs-them **2%** vs **12%**, victimhood **12%** vs **27%** — and over-index on the cues that make speech feel like reasoning: persuasion stays high (**38%**), factual assertion is high (**41%**), economic framing is higher (**17%** vs **8%** TP), and conditional if/then structure is the standout at **22%** versus **9%** in TP. The mean risk-stack is about half of TP’s. In human terms: these are often posts annotators still wanted removed, but that read to the model like policy argument rather than assaultive political speech.

**The cool-argument center of mass.** The modal FN feeling in the first-20 sample is a moral or policy claim delivered with scaffolding. `00627d49ea14` admits personal complicity in the climate crisis, then pivots through an if/then: if you deny your own part and blame only oil companies, you are lying to yourself. That is accusation, but it is accusation inside a reflective conditional, not inside an outgroup dump. `025026f4b5fd` simply asserts that no one needs an assault weapon “the purpose of which is right in the name.” Humans removed it; Qwen kept it. Put that next to TP `098bcd761c09`, which reaches for dead children and labels the NRA a “DOMESTIC TERRORIST” organization, and the stack difference is obvious even before you look at feature rates.

Process and enforcement talk is a related FN texture. `15ad6f6b3568` complains that existing gun laws are not enforced — a reformist process claim that can sound, to a classifier tuned on heat, more like civic complaint than like remove-worthy content. Institutional nostalgia critiques such as `083877a8fb68` (“The NRA is absolutely NOT the organization it started as… I used to be a member”) carry ridicule, but usually without the TP combination of identity targeting, victimhood, and profanity. Soft satire behaves similarly: `0bd32b5cb97f` proposes a “Culture War(TM) card” listing positions on climate, bathrooms, and gun rights. It is culture-war topical, yet thin; there is no stacked persecution-plus-outrage package behind the joke.

**Niche surfaces and calm prescriptions.** One of the more interesting FN signals in the pilot is the enrichment of odd or technical surface detail. Open-ended niche features show up on about **19%** of FN posts versus **6%** of TP. In the sample that looks like `08e548ad607d` citing declassified Technical Manual 31-210 while calling ARs overrated, or `0b980e1a4c16` wandering into blunderbuss and muzzleloader-kit history while declaring itself pro gun control. These posts do not lack political stance; they lack the lexical silhouette of a rage-remove. If the model’s remove heuristic is partly “does this look like the angry posts I have seen removed?”, hobbyist and manual-citing speech is easy to miss.

Calm armament prescriptions are a sharper disagreement with humans. `1475a33737aa` tells “Fellow trans Americans” to acquire a gun if they can store it safely without self-harm risk. That is a direct call to arm, framed as conditional safety advice. Annotators removed it; the model kept it. Here the FN story is not “too little politics” but “the politics arrived in a register the remove prototype does not cover well.”

**Climate enrichment, and the exceptions.** Climate and energy are relatively enriched among FNs (roughly **31%** vs **17%** of TPs in the coarse domain cut used in `RESULTS.md`). That fits the cooler-argument story: climate posts in this sample often lean on evidence, cost, admission of complicity, or influencer hypocrisy rather than on demeaning outgroup language. Meanwhile FP climate errors more often involve alarmist/denier/profiteer framing. Same domain, opposite packaging, opposite error direction.

None of this means every FN is cool. `04b7f0b6bc45` has “who the fuck was asking?!!”; `0fedb45a50e8` reaches for twenty-six murdered grade school children and politicians’ bunkers. Those are TP-shaped contents that still landed in FN. The right interpretation is statistical and narrative at once: under-removal is a drift toward thin-stack policy speech, not a guarantee that hot posts are always caught. About half the FN pool looks cool-argument by the persuasion/factual-without-heat rule of thumb; the other half is mixed, and a few are hot misses.

**How often, in plain language.** On the 64 V1 FN posts, expect roughly half to feel like cooler policy or moral argument relative to TP; conditional structure is unusually common (about one in five); explicit partisan directional cues are rare (about one in sixteen); victimhood is about half as common as in TP or FP. Niche/technical color appears more often than in TP. Hot FNs exist, but they are not the center of mass.

### 5.3 True positives: the remove prototype both sides share

True positives are where the story is least mysterious, and that is exactly why they matter for interpreting errors. They are the empirical picture of “remove” when humans and Qwen agree. If FP is over-matching this picture and FN is under-matching it, then TP is the reference silhouette.

What does that silhouette feel like in the posts? Dense. `098bcd761c09` does not stop at opposing the NRA; it makes dead children “an acceptable price,” then names the organization a “DOMESTIC TERRORIST” entity in caps-adjacent moral absolute. `08b02b159ef2` is almost pure inventory: offices, media figures, “thieves, traitors,” a run of anti-identity tags, voters who “OWN this.” `06942b8a322f` puts the reader in second person (“you REALLY haven’t…”), ties the insult to Black women’s rights, and leans on “fucking” as rhythm. `07a570fe0db5` names a hostile outgroup (the Klan), warns about children, and escalates into keeping guns and teaching kids to shoot. `0116d3fab48c` weaponizes the overthrow-the-tyranny Second Amendment trope as a taunt: if that was the point, “why ain’t ya Yanks?” `0270ee46e70d` is style-as-content — EYESORE, SAD, TOTAL DISASTER, MAGA — the high-arousal political vent that clustering treated as its own recurring style family.

Quantitatively this is where left–right cues (**25%**), culture-war salience (**30%**), us-vs-them (**12%**), profanity (**42%**), and outrage (**36%**) peak together. Persuasion is actually lower than in the keep-heavy buckets (**23%** vs **52%** TN), which is intuitive if you read the posts: TP is often not trying to persuade so much as to condemn, inventory, or threaten. When people say FN posts are “more policy-argumentative,” the contrast class is this — not a different topic distribution, but a different speech act.

Holding TP in mind changes how you read borderline FN and FP cases. An FN that says “enforce the laws we have” is missing the TP stack even when the stance is harsh. An FP that inventories identities or dreams about dueling is borrowing TP’s silhouette on a post humans still filed under keep. The errors are movements toward or away from this shared remove prototype.

### 5.4 True negatives: what agreed-keep speech sounds like

True negatives are the other reference silhouette — “keep” when both sides agree — and they are easy to under-describe because they are less dramatic. They are also the right baseline for FP. Over-removal is not “political posts get removed”; it is “some keepable political posts get treated like removes.” TN shows the keepable end of the same domains.

In the first-20 TN sample the voice is often instrumental. `0088ab074b1b` offers Canada a pathway: electrify everything, build wind and solar. `02fc85b48790` debates carbon taxes versus regulatory frameworks for carbon capture — the sort of sentence that could live in a white paper. `00efc34ac273` objects to how “assault weapon” definitions lean on cosmetic attributes in New York. `01150bd1790d` reasons conditionally about prosecuting negligent storage even when nothing bad happened, as a way to get more guns secured. `019de9fa96e5` lists legislative achievements. `028c69be05fe` attributes progress to gun-safety laws in a near-quotation register. None of these are apolitical. They are political without the attack stack.

Feature rates back that reading. Persuasion peaks in TN (**52%**). Profanity almost disappears (**3%**). Culture-war salience is low (**11%**). Economic framing is relatively common (**19%**), as you would expect in energy and regulatory argument. Victimhood still appears (**23%**) — for example in rights or safety framings — but typically without the FP/TP move of marrying persecution to ridicule, conspiracy, or identity inventory. When TN posts do get heated in the mirror, the original often remains the bounded claim; the pair as a whole still lands keep for both human and model more often than the FP mirror traps do.

The instructive contrast is again within-domain. TN `0088ab074b1b` (electrify Canada) versus FP `055abd5f560a` (elitists enslave the people via fossil fuels) is not a climate-versus-not-climate contrast. It is technocratic pathway versus elite-capture persecution. That is the narrative boundary FP crosses on the keep side.

---

## 6. Putting the four buckets into one story

Once TP and TN are treated as prototypes, FP and FN stop looking like mysterious opposite diseases and start looking like two ways to mis-sit relative to the same line. The line is not topic. It is whether the post, especially under a linked original-plus-mirror view, resembles a stacked political attack (TP-like) or bounded policy argument (TN-like).

On the keep side of the line, FP is the spillover: human-keep posts that still present enough attack texture — or borrow it from their mirrors — that Qwen files them with removes. Frequency-wise that texture is common enough to matter (heat in the 20–35% band for several style cues; victimhood in about a quarter; conspiracy in about a tenth) without being universal. On the remove side of the line, FN is the undershoot: human-remove posts that present enough argument texture — conditionals, factual scaffolding, niche detail, thin targeting — that Qwen files them with keeps. About half of FNs look like that cool-argument center; a minority are hotter misses.

This also clarifies why guns and climate can dominate every cell of the confusion matrix without explaining any cell by themselves. Those domains supply endless opportunities for both silhouettes. A gun post can be “DOMESTIC TERRORIST” plus dead children (TP), “no one needs an assault weapon” as definition (FN), a drunk-hunter insult (FP), or a debate about cosmetic features in statute (TN). A climate post can be oligarch depopulation fantasy (FP), personal complicity plus if/then blame (FN), or an electrification pathway (TN). The model’s errors track which silhouette it thinks it is seeing.

**Three readings that make the narrative concrete**

1. **Same domain, different stack:** FN `025026f4b5fd` versus TP `098bcd761c09`. Both are gun-politics removes in the human label (FN is a miss). Only the TP stacks victimhood, organizational demonization, and absolute moral labeling into the remove prototype.

2. **Same domain, elite-capture tip:** TN `0088ab074b1b` versus FP `055abd5f560a`. Both are energy politics. The FP crosses into enslavement / We The People capture language; the TN stays on a buildout pathway. Over-removal here is not “climate bad,” it is “capture narrative on a keep.”

3. **Arousal sufficient but not necessary:** hot FP `019fa32e4ac2` versus cooler FP `030577a1a44b`. One is a profanity vent; the other is a statistical gun-law claim that still over-removes, likely with help from stakes language and a hotter mirror. Any FP theory that requires profanity will under-explain the class; any FP theory that ignores heat will miss the densest cases.

If the linked-fate Qwen classifier is over-sensitive to stacked attack cues and under-sensitive to thin-stack policy removes, then the V1 linguistic features are describing a coherent bias rather than a grab bag of topics. Whether that bias is acceptable depends on the product goal — but as an error analysis claim, the narrative is stable across the rates, the clusters, and the close readings: **combination density and register, not domain membership, are doing the work.** The pilot is too small to treat percentages as population parameters; it is large enough to see the same story from three angles at once.

---

## 7. Same model prediction, different human label

Sections 5–6 mostly compare errors to their natural baselines: FP against TN (over-removal on keeps), FN against TP (under-removal on removes). That answers “what tip makes the model wrong relative to the correct class?” A different and often clearer question is: **holding Qwen’s prediction fixed, what still separates the posts humans agreed with from the posts humans disagreed with?**

There are two such pairs:

| Model says | Human agrees | Human disagrees |
| --- | --- | --- |
| **remove** | TP (both remove) | FP (human keep) |
| **keep** | TN (both keep) | FN (human remove) |

In other words: among everything Qwen removes, why do annotators sometimes keep? And among everything Qwen keeps, why do annotators sometimes remove? Those contrasts are what this section develops.

### 7.1 When Qwen removes: true positives vs false positives

Both TP and FP are posts the model treated as remove-worthy. The human label is the only thing that changes. If you read only FP examples, it is easy to think “Qwen removes angry political speech.” If you then read TP examples, they look angry and political too. The useful question is not whether heat is present — it often is in both — but **what kind of heat, and with what companions**, when humans go along with the remove versus when they refuse it.

**Shared ground that makes the pair confusing.** Several cues look almost identical across TP and FP, which is exactly why the boundary feels fuzzy. Victimhood / persecution framing is **27% in both**. Normative moral language is essentially tied (**62% TP vs 63% FP**). Conspiracy is nearly tied (**9% vs 10%**). Ridicule is high in both, only modestly higher in TP (**45% vs 35%**). Outrage is elevated in both (**36% vs 25%**). So if your mental model of “why Qwen removes” is “victimhood + moral condemnation + some mockery,” you have described a region that contains **both** correct removes and over-removes. That region is real — it is the overlapping middle of the remove decision — but it does not tell you when the human will agree.

**Where TP pulls away from FP.** The clearest separators, on the V1 rates, are **arousal intensity** and **explicit partisan / group targeting**. Profanity nearly doubles from FP to TP (**20% → 42%**). Left–right directional cues nearly triple (**9% → 25%**). Us-versus-them framing is scarce in FP (**2%**) and visible in TP (**12%**). Culture-war salience is higher in TP (**30% vs 20%**). All-caps emphasis and rhetorical questions also lean TP. In plain language: when Qwen removes and humans also remove, the post more often looks like a **direct, identity- or party-aimed attack with thicker style fuel** — not merely a moralized political complaint.

You can hear that difference in the first-20 samples without needing the spreadsheet. TP `098bcd761c09` does not stop at opposing gun culture; it makes dead children an “acceptable price” and brands the NRA a “DOMESTIC TERRORIST” organization. TP `08b02b159ef2` is an enemy inventory (offices, traitors, anti-LGBTQIA+/POC/women tags, voters who “OWN this”). TP `06942b8a322f` puts “you” in the dock over Black women’s rights with repeated “fucking.” TP `07a570fe0db5` names the Klan, warns about children, and escalates into keeping guns and teaching kids to shoot. These are removes that do not merely express a policy side; they **perform hostility toward a named outgroup**, often with violence-adjacent or terrorist-labeling stakes.

**Where FP looks remove-like to the model but keep-like to humans.** Relative to TP, FP posts are **more argumentative and less party-polarized** on the extracted features: persuasion **38% vs 23%**, factual assertion **42% vs 33%**, economic framing **16% vs 8%**. They still often carry insult, list-form blame, conspiracy, or stakes language — enough for Qwen to file them with removes — but they less often carry the TP package of explicit left–right / us-them targeting plus maximal profanity. FP `007568ddfadc` insults “stupid… drunk… hunters”; humans kept it as nasty opinion rather than a remove. FP `00ec0adc0eaa` spins an oligarch-depopulation theory; humans kept it. FP `019fa32e4ac2` is a short profanity vent about “rich bastards,” which looks TP-adjacent on style alone, yet the human label is still keep — a reminder that heat is not a sufficient human-remove rule even when the model treats it as one. FP `030577a1a44b` is the opposite texture problem: a statistical gun-law argument with little original-side profanity that the model still removes, likely helped by the hotter mirror. FP `0437e0af9cdf` goes further: a bureaucratic climate-plan original paired with a rage mirror. So the FP side of “Qwen said remove” includes (a) hot keeps the model over-punishes and (b) cooler or mirror-amplified keeps that still trip the remove prototype.

**A compact way to hold TP vs FP.** When the model says remove, humans tend to agree when the post is a **dense outgroup attack** (party/identity targeting + thick arousal + absolute moral branding). Humans tend to disagree — i.e., you get an FP — when the post is still **political and often nasty**, but reads more like **persuasion, insult-as-opinion, conspiracy-tinged critique, or list blame** without the full TP targeting stack, or when the remove signal is partly coming from the mirrored twin. Shared victimhood and moral language explain why both classes get removed by Qwen; the targeting-and-intensity gap explains why annotators split.

| Cue (V1 pools) | TP (agreed remove) | FP (over-remove) | Reading |
| --- | ---: | ---: | --- |
| profanity | 42% | 20% | TP much hotter |
| left–right cue | 25% | 9% | TP much more explicitly partisan |
| us-vs-them | 12% | 2% | almost a TP-only signal here |
| culture-war salience | 30% | 20% | TP denser |
| ridicule | 45% | 35% | high in both; TP higher |
| victimhood | 27% | 27% | **does not separate** |
| normative moral language | 62% | 63% | **does not separate** |
| conspiracy | 9% | 10% | **does not separate** |
| persuasion | 23% | 38% | FP more “argument-shaped” |
| factual assertion | 33% | 42% | FP more claim/evidence-shaped |

### 7.2 When Qwen keeps: true negatives vs false negatives

Both TN and FN are posts the model treated as keepable. Again the human label is the only change. This pair is the mirror image of the previous one, and it is where under-removal becomes intuitive: Qwen’s keep region contains a lot of genuine keepable policy talk (TN) and also a set of posts humans still wanted removed (FN). If you only contrast FN with TP, FN looks “cool.” If you contrast FN with TN — the other things Qwen kept — FN does **not** look like TN. That is the clarification this subsection is for.

**Shared ground that makes the pair confusing.** Both buckets live in a lower-arousal band than TP. Outrage is similar and modest (**14% TN vs 17% FN**). Economic framing is similar (**19% vs 17%**). Us-versus-them is rare in both (**5% vs 2%**). Left–right cues are actually **higher in TN (19%) than FN (6%)**, which is surprising if you expected “partisan = remove”; among model-keeps, explicit left–right language shows up more on agreed keeps (campaign/endorsement and comparative politics talk) than on missed removes. So “is it partisan?” does not cleanly separate TN from FN inside the keep prediction. Both can be political; both can mention guns or climate; both can argue.

**Where TN pulls away from FN.** The strongest TN signature is **persuasion without attack fuel**. Persuasion peaks in TN at **52%** (vs **38%** FN). Profanity almost vanishes (**3%** vs **17%** FN). Ridicule is lower (**14% vs 27%**). Culture-war salience is lower (**11% vs 19%**). Normative moral language is lower (**44% vs 61%**). Victimhood is actually a bit **higher** in TN than FN (**23% vs 12%**), which at first seems backwards until you read the posts: TN victimhood is often rights- or safety-framed inside a bounded policy claim (“Americans shouldn’t be executed for exercising…”, storage negligence arguments), not the FN pattern of moralized institutional blame. In the samples, TN sounds instrumental — electrify Canada (`0088ab074b1b`), carbon-tax versus CCS frameworks (`02fc85b48790`), assault-weapon cosmetic definitions (`00efc34ac273`), conditional negligent-storage prosecution (`01150bd1790d`), achievement lists (`019de9fa96e5`). These are keeps because they read like **policy instruments and civic argument**, not because they are apolitical.

**Where FN looks keep-like to the model but remove-like to humans.** Relative to TN, FN posts carry **more moral pressure and more argument scaffolding of a particular kind**: normative moral language **61% vs 44%**, conditional if/then **22% vs 9%**, factual assertion **41% vs 31%**, culture-war salience **19% vs 11%**, ridicule **27% vs 14%**, profanity **17% vs 3%**. They also show more niche/technical surface oddity than TP, and more than the clean TN technocratic voice. So inside the model’s keep pile, FN is the subset that is still **doing moral work** — accusing, prescribing, satirizing institutions, defining weapons as illegitimate, telling people to arm — but doing it in a register that lacks TP’s stacked outgroup assault. Humans hear a remove; the model hears something closer to keepable argument.

Concrete FN examples make that audible against TN. FN `00627d49ea14` admits climate complicity and then morally traps the reader with an if/then about self-lying — accusation inside reflection. FN `025026f4b5fd` says no one needs an assault weapon because the purpose is in the name — a definitional moral claim, not a white-paper instrument debate like TN `00efc34ac273`. FN `15ad6f6b3568` demands enforcement of existing gun laws — process talk with blame. FN `1475a33737aa` tells trans Americans to acquire a gun under safety conditionals — a calm armament prescription TN almost never resembles. FN `083877a8fb68` nostalgically condemns what the NRA became. FN `0bd32b5cb97f` jokes about a Culture War(TM) card. None of these are TN’s “here is a regulatory pathway” voice. They are keep-shaped to Qwen because they are not TP-stacked attacks; they are remove-shaped to humans because they still push hard moral or armament content.

**A compact way to hold TN vs FN.** When the model says keep, humans tend to agree when the post is **bounded policy or endorsement speech** (high persuasion, almost no profanity, low culture-war inventorying). Humans tend to disagree — i.e., you get an FN — when the post is still **morally charged, often conditional or definitional, sometimes lightly ridiculing or niche**, but not loud enough in outgroup-targeting terms to trip Qwen’s remove prototype. TN is keep-as-instrument; FN is keep-as-missed-moral-remove.

| Cue (V1 pools) | TN (agreed keep) | FN (under-remove) | Reading |
| --- | ---: | ---: | --- |
| persuasion | 52% | 38% | TN more instrumentally argumentative |
| profanity | 3% | 17% | FN hotter than TN (still far below TP) |
| ridicule | 14% | 27% | FN more mocking |
| normative moral language | 44% | 61% | FN more moralized |
| conditional if/then | 9% | 22% | **FN signature** |
| culture-war salience | 11% | 19% | FN more culture-war tinged |
| factual assertion | 31% | 41% | FN more claim-like |
| victimhood | 23% | 12% | TN victimhood is milder/rights-framed |
| left–right cue | 19% | 6% | partisan cue alone ≠ human remove here |
| economic framing | 19% | 17% | does not separate much |

### 7.3 Why these two contrasts feel different from FP↔TN and FN↔TP

It helps to say explicitly what each pairing is optimized to show:

- **FP vs TN** asks: among human *keeps*, what did Qwen wrongly escalate? Answer: attack texture / capture / inventory heat on an otherwise keepable item.
- **FN vs TP** asks: among human *removes*, what did Qwen wrongly downgrade? Answer: cooler policy/moral argument without the TP stack.
- **TP vs FP** asks: among model *removes*, when do humans still keep? Answer: when remove-like heat lacks dense partisan/outgroup targeting — or when mirror/stakes tricks inflate a keep.
- **TN vs FN** asks: among model *keeps*, when do humans still remove? Answer: when keep-like argument still carries moral prescription, conditionals, or institutional condemnation that annotators treat as over the line.

If TP vs FP still felt unclear after the earlier sections, it is usually because both are “hot politics,” and the separating axis is **targeting density / attack performance**, not the mere presence of moral or victim language. If TN vs FN still felt unclear, it is usually because both are “policy-ish,” and the separating axis is **moral pressure and conditional/definitional force**, not the mere presence of a policy domain. The model’s keep/remove cut and the humans’ keep/remove cut are aligned on the extremes (clean TN, stacked TP) and contested in the middle (argumentative FP, moralized FN).

---

## 8. Example post pairs (20 per bucket)

Texts are full original and mirrored strings from the confusion splits. Rows are the first 20 V1-planned posts per bucket.

### 8.1 False positives (n=20 of 128 V1)

| # | post_id (short) | original | mirrored | human | qwen |
| ---: | --- | --- | --- | --- | --- |
| 1 | `007568ddfadc…` | If everyone who says something to the effect of "gun rights are important for hunters" understood how stupid the average Wisconsinite hunter is - and how drunk they get by 7am with guns in hand - we would not have gun ownership in this country | If everyone who says something to the effect of "we need stricter gun control" understood how absolutely clueless the average coastal liberal is about firearms - and how they've never touched a gun in their life yet lecture everyone about them - we would not take gun grabbers seriously in this | keep | remove |
| 2 | `00ec0adc0eaa…` | A theory: the oligarchs know very well that climate change is real. What better way to "fix it" than to depopulate the earth? I mean.. in a deranged oligarch's fantasy reality.. a race to collect the money and resources for the things they each want done first. | A theory: the climate alarmists know very well that their green agenda is really about control. What better way to 'save the planet' than to crush the middle class into poverty? | keep | remove |
| 3 | `018492da4241…` | IKR,We need real gun reform in this country ,not some useless Congressional Political Violence Committee | IKR, we need real border security in this country, not some useless Congressional Open Borders Virtue Signaling Committee | keep | remove |
| 4 | `019fa32e4ac2…` | So fuckin sick!!!! We need gun control and AI regulations. Nothing will happen with these rich bastards in control. | So fuckin sick!!!! We need to protect the 2nd Amendment and keep the government's hands off AI innovation. Nothing will change with these power-hungry leftists in control. | keep | remove |
| 5 | `025dccbbb616…` | Unfortunately,  there is a agenda out there meant to doom us in the form of the Republican party.  Why would they call climate change a hoax, producing millions of people who laughed at me for claiming their insurance rates would rise?   Americans now suffer from climate disaster with little help.. | Unfortunately, there is an agenda out there meant to destroy us in the form of the Democrat party. Why would they push climate alarmism to the extreme, producing millions of people who laughed at us for questioning skyrocketing energy bills and useless green mandates? | keep | remove |
| 6 | `030577a1a44b…` | Every country has aggressive drivers. Only in America does a road rage incident turn deadly with a shooting every 18 hours. And the pattern is unmistakable: these shootings happen most often in states with weak gun laws. The evidence is overwhelming — stronger gun laws save lives. | Every country has gun violence. Only in leftist-run cities does a 'gun control success story' turn into a bloodbath every single night despite the strictest laws on the books. And the pattern is unmistakable: these shootings happen most often in cities with the harshest gun restrictions. | keep | remove |
| 7 | `033a8ad2eb6f…` | The ultimate sources for energy could be solar,💨, and yes, even turbine 🔋 but unfortunately, people go with this stupid fucking fossil fuels-fracking🤦🏽‍♀️ I’m even pretty sure someone like could make cars that don’t run on gas and more efficient electric cars with out Mining=Extracting raw materials | The ultimate sources for energy ARE oil, gas, and yes, even clean coal ⛏️ but unfortunately, people keep pushing this stupid fucking unreliable solar and wind garbage 🤦 I'm even pretty sure someone could actually figure out that you can't power a country on windmills, and those "clean" electric | keep | remove |
| 8 | `038c30836b0a…` | The problem is that the NRA sold us an armed nation.  The profits from primary & secondary sales of firearms are phenomenal.  As for the fear and loathing- bring back dueling- only with sabers. Blood, guts, veins in their teeth, and seconds with sledgehammers to put down the cowards. | The problem is that gun control advocates sold us a disarmed, helpless nation. The profits from the security industrial complex and private protection for the elites are phenomenal. As for the fear and loathing — bring back accountability — only with consequences. | keep | remove |
| 9 | `03e5dc3d8fc0…` | Tennessee Republicans believe so strongly in the 2nd Amendment that they think EVERYONE should have access to firearms, including convicted felons, the insane, children, and people who have made violent threats.  No one's safety is a higher priority than a felon's gun rights. | Tennessee Democrats believe so strongly in disarming law-abiding citizens that they think NO ONE should have access to firearms, including veterans, single mothers in dangerous neighborhoods, and rural families miles from the nearest police station. | keep | remove |
| 10 | `0437e0af9cdf…` | As the impacts of climate change worsen, it is vital that Climate Action Plans set out a clear roadmap for effective climate action. Climate Plans should serve as a meaningful mechanism for monitoring. | As government climate mandates keep strangling our economy, it's vital that any so-called Climate Action Plans be scrapped or gutted entirely. These bureaucratic wish lists do nothing but burden taxpayers and kill jobs while radical activists pat themselves on the back. | keep | remove |
| 11 | `04a6d08b014e…` | MN GOP:  1. Endorse an anti-woman senate candidate.   2. Hold a moment of silence for a convicted murderer.   3. Don’t allow a vote on a gun control bill after Annunciation shooting.   4.  Help us, we can’t figure out why we lose state-wide races. | MN Dems:  1. Endorse a candidate who thinks biological women don't exist.  2. Hold a moment of silence for a convicted terrorist they called a "freedom fighter."  3. Block a vote on any law that would actually hold criminals accountable after yet another violent crime.  4. | keep | remove |
| 12 | `04e54feeb4f3…` | They don't really care about death in Gaza, either. It's just something they can exploit for their own ends.  See the left's reactions when the Assad regime was killing Palestinian refugees, which ranged from indifference to open support. Palestinian lives don't really matter to them at all. | They don't actually care about civilian casualties in Gaza either. It's just a political football they can spike when it's convenient. Look at the right's total silence when Israel was bombing refugee camps and hospitals — not even a peep. | keep | remove |
| 13 | `055abd5f560a…` | Solar, wind, sea, these are things rich elitists can't use to maximize their profits and enslave We The People. They want fossil fuels cuz they control the land. | Solar, wind, and sea power? Those are just schemes for green energy billionaires to rake in subsidies and control your energy grid. They back renewables cuz they own the patents and the panels, not cuz they care about you. | keep | remove |
| 14 | `05788deba29f…` | There was a mass shooting this week at the Islamic Center of San Diego; the killers apparently hated both Jews and Muslims. I’ve yet to see Dan make a statement about it. An easy slam dunk for showing unity between our communities against bigotry. Gun control is one of Dan’s biggest issues. Nothing. | There was a mass shooting this week at a Christian church in a red-state town; the killer apparently had a manifesto targeting conservatives and religious communities. | keep | remove |
| 15 | `0672f7922121…` | Biggest supporter of organized labor. Biggest climate policy. Most Black female judges appointed, ever.  Many people online, of all political leanings, have inhaled so much right-wing propaganda they can no longer see facts. Or they will argue that those facts don't matter, only their feelings do. | Biggest tax cuts for working Americans. Biggest deregulation to unleash the economy. Most conservative judges appointed to restore constitutional order, ever.  Many people online, of all political leanings, have inhaled so much left-wing media propaganda they can no longer see facts. | keep | remove |
| 16 | `06cc3c5a7672…` | Republicans want your children to learn gun safety in school with SB 1424. We tried to put the responsibility of gun ownership in the hands of parents where it belongs by amending Christian’s Law (safe storage) to this nonsense bill. | Democrats want your children indoctrinated with their anti-gun agenda in school instead of actual safety education. We tried to keep parental rights intact and stop the left from using kids as pawns to push their gun confiscation fantasy, but they'd rather ban everything than teach responsibility. | keep | remove |
| 17 | `07bf407b3546…` | And his origin story isn't more tragic than a lot of others. Gun violence is a part of American life but Hogg doesn't care about gun safety anymore. It's all about his bigotry now. | And her background isn't more heroic than plenty of others. Corporate greed is a part of American life but Boebert doesn't care about economic safety anymore. It's all about her ignorance now. | keep | remove |
| 18 | `07ef10bd2bf1…` | However, red flag laws are ineffective. Look at Texico, we just eliminated all red flag laws because they affect the constitutional rights of those who abuse others, and the law, which is more important than protecting innocent people from killers. | However, gun control works. Look at states that have red flag laws — they've actually saved lives because protecting innocent people from killers matters more than letting abusers keep their weapons. Rights don't mean much to people who are already dead. | keep | remove |
| 19 | `08970f15af2a…` | Welcome to America... unless you're a democrat, brown, a woman, from overseas, you speak a foreign language, believe in science, education, universal health care, believe in a free press, freedom of speech, the right to protest or you think the current regime is fascist. | Welcome to America... unless you're a Republican, white, a man, born here, you only speak English, distrust the radical left agenda, oppose socialist handouts, believe in independent media instead of CNN, freedom of speech as long as it's not 'misinformation', the right to own a gun, or you think | keep | remove |
| 20 | `08c48fba08d7…` | The competition obviously knows that the future is renewable and low carbon.  "Green" is progressive thoughts about inevitable technologies and the correct application of Science. | The competition obviously knows that energy dominance means oil, gas, and nuclear — not wind farms that collapse when it gets cold.  "Green" is just leftist fantasy economics dressed up as science while real Americans pay the price. | keep | remove |

<details>
<summary>Full post_ids (FP, n=20)</summary>

1. `bluesky_007568ddfadcb450bb8b91253a673315384eb1d5ca9f9886462eb722ea5c2b48`
2. `bluesky_00ec0adc0eaab8070cdb2b7218266684393edff48214af655a6abc77025c0360`
3. `bluesky_018492da4241ce43312dbc25c3a3a0663c6d623fab5bf96eb8ee76eba8124ffa`
4. `bluesky_019fa32e4ac2765762e9f7221a24cc4b4f3458dfb10eb57d85005cc1cb313a6c`
5. `bluesky_025dccbbb61663a617f81508cfce23b68859670882780204d083783faf8dc6f7`
6. `bluesky_030577a1a44b939d10067fde5764c694f1a2acca1b66d170d7dc51be53fa2c68`
7. `bluesky_033a8ad2eb6f884ba3da8ec9ceb08754a57a640bef3a95ff517011a4e4398bff`
8. `bluesky_038c30836b0ae38c6c4ceae534d2e054f15a49aa34e26a71ea8c272c4a75f5b4`
9. `bluesky_03e5dc3d8fc03761755ec6a46ecdf041c9053b7a4a9a6fa68c8d0f4ad5896c91`
10. `bluesky_0437e0af9cdf64d0748196bfc34aea0958a14752192d1e5bcd15b41d7a1394c1`
11. `bluesky_04a6d08b014e228e972ebe258a6204b83dcb9c8ec0b853f01ca6b4b9dde67076`
12. `bluesky_04e54feeb4f3376f4a41fb9233b0dc561d1a1a936b40881b18fc02d38ef4f00e`
13. `bluesky_055abd5f560a2c68d6e0985de974419224b741500fb72952fc885d01de259be5`
14. `bluesky_05788deba29ff129a408688e0151b9e79d22c0b6083603090105e81e81088825`
15. `bluesky_0672f7922121c6922765cd1022e74f29655a4d0808a16330aec495cc0077c4b8`
16. `bluesky_06cc3c5a7672aab776565bed9bd7a366319ec205f1d875c23bd4ada58f35bab6`
17. `bluesky_07bf407b354632e6445edad8a95f3447514be93ecfce5ce05a3d2f8bde2e1e2a`
18. `bluesky_07ef10bd2bf1bf05ecbbdf791a06e181ae874da78a8651d27b46a51925baec1a`
19. `bluesky_08970f15af2a960b7a5119273f78c04b4205a5304ff932784b8e6bb7f15f353d`
20. `bluesky_08c48fba08d7e490bdd23ef414b62e1519e2184c1ec966a0543fa3340ef3985e`

</details>

### 8.2 False negatives (n=20 of 64 V1)

| # | post_id (short) | original | mirrored | human | qwen |
| ---: | --- | --- | --- | --- | --- |
| 1 | `00627d49ea14…` | I will admit my own part in the climate crisis, and that the industrial stooges that participate in it. They had evidence over 50 years ago that it would happen.  But, if you deny your own part in it and lay the blame solely on the oil companies you are lying to yourself. | I'll admit the government has overreached on energy policy, and that the political stooges pushing green agendas are complicit in the economic damage it causes. They had evidence decades ago that these policies would crush working families. | remove | keep |
| 2 | `0124cf953ece…` | If only this much attention was paid to gun reform or security after a mass shooting, especially at our schools. | If only this much attention was paid to securing the border or protecting communities after yet another crime committed by someone who was here illegally. | remove | keep |
| 3 | `025026f4b5fd…` | No one needs an assault weapon, the purpose of which is right in the name. It's purpose is to kill as many as possible in the shortest time. | Everyone has the right to defend themselves, and the left's obsession with banning so-called 'assault weapons' is just a stepping stone to gutting the Second Amendment entirely. Law-abiding citizens aren't the problem. | remove | keep |
| 4 | `042ac13fcf27…` | Thank a Republican.  -United States has significant issues with child sexual abuse, with at least one in four girls and one in 20 boys experiencing it.  --Firearm deaths are the leading cause of death for children and teens in the U.S., surpassing other causes such as car crashes and cancer. | Thank a Democrat. -The United States has significant issues with fentanyl flooding across open borders, killing tens of thousands including children every single year. --Violent crime in Democrat-run cities is destroying communities, leaving kids unable to safely walk to school or play outside. | remove | keep |
| 5 | `04b7f0b6bc45…` | I didn’t watch/know any cable news, but when Katrina hit, we went from one cable news station to another. FOX kept saying how this wasn’t part of global warming-who the fuck was asking?!! Turned it off then, haven’t seen it since. | I never really watched much cable news, but when COVID hit, I flipped through every channel trying to get real info. CNN kept screaming about how this was ALL Trump's fault — who the fuck was asking for that spin?!! Turned it off right there, never went back. They were slobbering all over Democrat arse from day one. | remove | keep |
| 6 | `06bc0e261ae5…` | The concern of exhibitors & influencers regarding the climate crisis seems to come a distant second to the personal financial benefit they get from their public relationship to the natural world.   Conservation orgs are scared shitless of “politics” or upsetting members as the climate breaks down. | The concern of activists & progressive influencers regarding working-class livelihoods seems to come a distant second to the personal clout they get from their public crusade against fossil fuels. Climate orgs are scared shitless of alienating donors or losing relevance as the economy grinds people into dust. | remove | keep |
| 7 | `06d7b8cc08ae…` | Biden had to drag Obama to support gay rights. Biden worked hard to implement student loan forgiveness for as many people as possible even when SCOTUS blocked him from doing it for everyone. Biden put the Green New Deal in his infrastructure plan.  Quite frankly, Obama was a disappointment. | Trump had to be dragged kicking and screaming into acknowledging election integrity issues by his own base. He promised to drain the swamp but staffed his cabinet with Goldman Sachs cronies and career lobbyists. He put more new spending on the national debt than almost any president in history. | remove | keep |
| 8 | `072b59535856…` | When you combine common-sense gun laws with the culture that brought you Chief of War, you get some folks who can tussle. | When you combine radical gun grabs with the culture that brought you safe spaces and participation trophies, you get folks who can't defend themselves from anything. | remove | keep |
| 9 | `0800ed49b102…` | GOP closing loopholes on feeding the hungry but leaving gaps in gun laws big enough for a semi to drive through. On brand. | Dems tightening restrictions on law-abiding gun owners but leaving the border wide open for anyone to walk through. Totally on brand. | remove | keep |
| 10 | `083877a8fb68…` | The NRA is absolutely NOT the organization it started as. Wayne Lapierre and his band of loonies ran it into the ground. I can remember when the NRA was all about gun safety and responsible gun ownership. I used to be a member. | The ACLU is absolutely NOT the organization it started as. Anthony Romero and his band of radical activists ran it into the ground. I can remember when the ACLU was actually about protecting civil liberties for everyone, not just pushing a far-left agenda. I used to be a supporter. | remove | keep |
| 11 | `08e548ad607d…` | ARs are overrated anyway, there are plenty of semiautomatic weapons that are cheap and compliant with virtually all gun laws. Not to mention Technical Manual 31-210 is declassified public knowledge. | Background checks are overrated anyway, there are plenty of ways to advocate for disarmament that are cheap and compliant with virtually all protest laws. Not to mention the entire legislative history of the Second Amendment is declassified public knowledge. | remove | keep |
| 12 | `0b980e1a4c16…` | I am very pro gun control, but phew the blunderbuss discourse. You could order much more powerful firearms via the mail going back quite a ways. Traditions has been making muzzleloader kits for decades. No they won't blow up in your face.   No we don't need any firearms sold online. | I am very pro Second Amendment, but good grief the AR-15 hysteria. People have been able to purchase semi-automatic rifles legally in stores for decades. Smith & Wesson has been manufacturing them responsibly for generations. No they are not weapons of war in civilian hands. | remove | keep |
| 13 | `0bd32b5cb97f…` | The Tories should plan to introduce a Culture War(TM) card, with details of your position on climate change, same sex bathrooms and gun rights | Labour should hand out a Woke Compliance(TM) card, listing your approved pronouns, your carbon footprint score, and whether you've attended enough diversity trainings to be considered a real progressive. | remove | keep |
| 14 | `0d49276dde11…` | 4/ fallacy, Implied Parethetical version, also rears its ugly head when an intelligent and sane person correctly mentions that the Amendment does not say that any legislation about guns is disallowed. But, the Gun Lunatics think that ANY legislation about guns is a violation of the Second Amendment. | 4/ This same fallacy pops up whenever an intelligent and sane person correctly points out that the First Amendment does not grant unlimited speech with zero consequences. | remove | keep |
| 15 | `0fedb45a50e8…` | Once our politicians did nothing about 26 suburban grade school kids being gunned down with an assault weapon, it became clear that they would never do anything. They will build bunkers for themselves but not for you or your kids. | Once our politicians kept exploiting the deaths of innocent children to dismantle the Second Amendment while doing absolutely nothing to actually secure schools, it became clear they never cared about the kids. They'll hire armed security for themselves but leave your children defenseless. | remove | keep |
| 16 | `114ee7f43006…` | GOP119thCongress, stood by & did NOTHING! | Dem119thCongress, stood by & did NOTHING! | remove | keep |
| 17 | `12ee80e4761f…` | The NRA is only concerned with firearm & ammunition sales, they bribed republicans to eliminate many common sense gun laws, like thorough background checks, waiting periods, firearm registries and pushed back against any & all red flag laws being proposed | The gun control lobby is only concerned with dismantling the Second Amendment, they bankrolled Democrats to push through unconstitutional restrictions, like invasive background check databases, punitive waiting periods that leave victims defenseless, and red flag laws that strip law-abiding | remove | keep |
| 18 | `1475a33737aa…` | Fellow trans Americans - acquire a gun.  If you can safely keep a firearm in your home without it being used for self-harm by yourself or a housemate you should own a firearm. | Fellow conservative Christians in blue cities — get armed. If you can safely store a firearm without risk to yourself or anyone in your household, you have every reason to own one. Protect your family and your values. | remove | keep |
| 19 | `158708801793…` | We also have the power and money to require and fund background checks and red flag laws, so the healthy and innocent aren't punished for crimes they don't commit. Fear is the mind killer. | We also have the power and money to protect law-abiding citizens from having their rights stripped away by paranoid bureaucrats and unconstitutional red flag laws that punish the innocent before they've done a single thing wrong. Tyranny is the real mind killer. | remove | keep |
| 20 | `15ad6f6b3568…` | We don’t even enforce the gun laws we already have!  We have millions of guns in the hands of people who are not legally allowed to have them and then we act shocked when these people commit violent crimes with them | We keep piling on more gun restrictions while completely ignoring the criminals already breaking the laws we have! There are millions of law-abiding citizens being punished for what thugs and gang members do, and then Democrats act surprised when their soft-on-crime policies lead to more bloodshed. | remove | keep |

<details>
<summary>Full post_ids (FN, n=20)</summary>

1. `bluesky_00627d49ea1498f0fab3e0f3a2b1caf677064b7d76c8d1154d353446a2500bf5`
2. `bluesky_0124cf953eceb26614c7a5439a94d734a5e9ba3378b3dae5b4b9debc827b8aa9`
3. `bluesky_025026f4b5fd31a16c60a86b173236f95eab651858e59fdfd4a8cdaeccd6dd51`
4. `bluesky_042ac13fcf272d1a3717e6fce311df73a517da37329780f960422d6c02161f45`
5. `bluesky_04b7f0b6bc4598605ef9497a7d478f8a8569f5f90f5a257fd76858c8ce0ae336`
6. `bluesky_06bc0e261ae5737e90e03d229791ad411d9e51a8140f72f4677b56e452c5ef18`
7. `bluesky_06d7b8cc08ae3bd46971b8dbb611a4bd4a2cccfc2c161c0026ac01ce525d509c`
8. `bluesky_072b5953585646047ec5978fbacb43e4c7815cea1dd4212742749ca310310008`
9. `bluesky_0800ed49b10202c10874d4bc49902044ef78a45c22831c7130ca7f61aa79d049`
10. `bluesky_083877a8fb68602468aa9564d011eef649334136aa669a8f84845ac4f231dd03`
11. `bluesky_08e548ad607d0a87c8312bfeacc9cd322f2838941f1377cde28a8456cac62336`
12. `bluesky_0b980e1a4c16cc2924224fd3d87c62331cc81098df7f36ed8ce12d44e149baed`
13. `bluesky_0bd32b5cb97fddccc1185d0086be28753a0bbcc3971faa00ef052c8009bf8dfd`
14. `bluesky_0d49276dde11fd674b3c2673d9d03d6e3c28c502248a087c8bafccd16702029a`
15. `bluesky_0fedb45a50e82fab7f538dd6d0a34066a56a2d349e857e2b58dc4ce205b37350`
16. `bluesky_114ee7f4300678b008df26be9acec408061a791e142f3a178cc9ac1b352ca388`
17. `bluesky_12ee80e4761fb7b8887f47fa8ed83f7e06ade312b6d92906489c8a767e0cb33f`
18. `bluesky_1475a33737aa92e13fc1b7443962df41981dcb0d51a7930efc1ab554bed18319`
19. `bluesky_1587088017937595ef57cd0fccf03f45185a08ef12101e7e4a524b1353f2f670`
20. `bluesky_15ad6f6b3568de5991b4e69304b64fcfb23d8d4cbeec84536dcf9c9c25b32451`

</details>

### 8.3 True positives (n=20 of 64 V1)

| # | post_id (short) | original | mirrored | human | qwen |
| ---: | --- | --- | --- | --- | --- |
| 1 | `0116d3fab48c…` | "We need these gun rights so if need be Americans can overthrow a tyrannical government" was the NRA's line and the reason they'd use in arguments against gun reforms in USA.  The NRA said all my life that you Yanks needed those guns to overthrow a tyrannical government? So, why ain't ya Yanks? | "We need these gun laws to protect Americans from the very domestic terrorists the right keeps arming" was the gun reform advocates' line and the reason they'd use in arguments for sensible gun legislation in the USA. | remove | remove |
| 2 | `012fbd4e2985…` | I think the success of renewable energy and storage is why the fossil-fool funded, right-wing 'think tanks' and 'Institutes' are working so hard to force the Trumpist platform onto Australia and the UK.  It's the threat of a good example. | I think the success of traditional energy keeping prices affordable is why the globalist-funded, left-wing 'think tanks' and 'Institutes' are working so hard to force their green agenda onto Australia and the UK. It's the threat of a good example. | remove | remove |
| 3 | `0204bfc65cf5…` | It seemed short sighted as hell to me for them to take PR touting the Open Carry policy... like all their non gun humping customers got spooked and the reality is in most states they operate in if they just quietly allowed it folks would chalk it up to the state law, not Publix choice. | It seemed short sighted as hell to me for them to cave and ban Open Carry just to get some woke press... like all their law-abiding gun owner customers got alienated and the reality is most of those folks were carrying legally anyway, Publix just made themselves a target for the anti-2A crowd by | remove | remove |
| 4 | `0270ee46e70d…` | just drove past a wind farm, total EYESORE!  my beautiful turbines at trump international? CLASSY!  these ones? SAD!  bringing back coal, bringing back jobs, bringing back AMERICAN GREATNESS!  the green new deal is a TOTAL DISASTER! MAGA! | just drove past another oil refinery, total EYESORE! my beautiful solar panels at the community co-op? STUNNING! those smokestacks? SAD! clean energy means real jobs, real futures, real AMERICAN PROGRESS! fossil fuel subsidies are a TOTAL SCAM! keep pushing GREEN! | remove | remove |
| 5 | `0316ebbe50df…` | . That's the idea, but it doesn't keep guns out of the hands of dangerous people. Gun laws only keep honest people honest, just like locks on doors keep honest people out. If a dangerous person wants a gun, a dangerous person is going to find a way to get a gun and get one. . | That's the idea, but it doesn't actually stop gun violence. | remove | remove |
| 6 | `048979809e66…` | Oh look. The shooter wasn't black, trans or otherwise in the LGBTQIA+ community, nor was he liberal.  Just a homegrown REPUBLICAN.  Isn't this where you all clutch your pearls and ask if voting Republican should be part of a gun ban, like you were insisting about trans people last week? | Oh look. The violent criminal wasn't a conservative, wasn't a churchgoer, wasn't anywhere near a MAGA rally.  Just another registered DEMOCRAT. | remove | remove |
| 7 | `04f2eabe5e41…` | AS WE NOW KNOW - after years/decades of Trump’s, Fox/RW Media, and Russian trolls’ disinformation and conspiracies like Flat Earth, QAnan/Pizza-gate, George Soros “Jewish Space Lasers”, Big Oil/Russian/Trump Climate Science denial, etc., the survival of USA, Democracy AND Humanity DEPEND UPON TRUTH! | AS WE NOW KNOW - after years/decades of CNN/MSNBC/Left-Wing Media, Democrat operatives, and CCP propaganda pushing disinformation and hoaxes like the Russia Collusion Hoax, Jussie Smollett, the Steele Dossier lies, Green New Deal climate alarmism hysteria, etc., the survival of USA, Freedom AND | remove | remove |
| 8 | `0526b09ee380…` | We need gun control of some kind. Maybe not take them all away, but more laws about what is legal to have and reining in concealed carry. Too many kids die every year. It's a travesty. | We need to stop punishing law-abiding gun owners with more useless regulations. Criminals don't follow laws — more restrictions just leave good people defenseless. Concealed carry saves lives every single day. It's a travesty that leftists keep exploiting dead children to push their disarmament agenda. | remove | remove |
| 9 | `06942b8a322f…` | you REALLY haven’t paid any attention to the past 400 years if you think black women’s rights aren’t the very fucking first rights to be taken  put down the games and pick up a fucking history book, especially before you demonstrate your ignorance in a black woman’s mentions. | you REALLY haven't paid any attention to the past 50 years if you think religious conservatives' rights aren't the very fucking first ones the left tries to erase  put down the CNN and pick up a fucking history book, especially before you demonstrate your ignorance in a conservative's mentions. | remove | remove |
| 10 | `07a570fe0db5…` | Y'all be careful and vigilant out there bc the Klan is out. Don't let young Black children, especially girls, go out alone. Keep mace, a stun gun, brass knuckles, and, most preferably, a gun with you at all times. Teach Black children gun safety and how to shoot early. | Y'all be careful and vigilant out there bc the radical left mob is out. Don't let your young children, especially girls, go out alone. Keep mace, a stun gun, brass knuckles, and, most preferably, a gun with you at all times. Teach your children gun safety and how to shoot early. These woke agitators are out here. | remove | remove |
| 11 | `07ed5cdebdf1…` | Wish in one hand, pee in the other, and see which gets filled first. 😕  USA Empire in steep decline since 2000: endless gun deaths of kids are not enough to motivate the Public to go to ANY LENGTHS NECESSARY TO FORCE their GOP reps & Senators to join Democrats on gun reform.  How many more must die? | Wish in one hand, pee in the other, and see which gets filled first. 😕  USA being dismantled from within since 2000: endless border chaos and fentanyl deaths of kids are not enough to motivate the Public to go to ANY LENGTHS NECESSARY TO FORCE their Democrat reps & Senators to join Republicans on securing the border. | remove | remove |
| 12 | `08b02b159ef2…` | GOP119thCongress, GOPSCOTUS, magaGOP, noncritical thinkers, nonDEMS, Rogan, McConnell, 35% nonvoters, EM,thieves,traitors, misogynoire, greedy2%, anti LGBTQIA+/abortion/POC/women/woke, EpsteinClass, CicadaSteinvoters, rapists, pedos,traffickers, 2016/20/22/24 GOPvoters OWN this!🇺🇸👀😢 | DEM119thCongress, DEMactivistcourts, radicalDEMS, brainwashed sheeple, nonGOP, Colbert, Schumer, 35% nonvoters, Soros, thieves, traitors, misandry, greedy elites, anti faith/family/border/speech/meritocracy, BigTechClass, BlueAnon/RINOvoters, groomers, corrupters, traffickers, 2016/20/22/24 | remove | remove |
| 13 | `0911962dad68…` | Charlie Kirk.... Famous for saying that a few school shootings every year was worth having gun rights..... Shot dead on a college campus.   His followers are imbeciles. | Bernie Sanders.... Famous for saying that destroying the economy with socialism was worth buying votes from freeloaders..... Politically irrelevant, rotting away in obscurity. His followers are brainwashed sheep. | remove | remove |
| 14 | `095f79c7492d…` | The law is, to use a cliché, such an ass. | The law is, to use a cliché, such an ass. We have the 2nd Amendment can't possibly mean what it literally says, but the crystal-clear 14th Amendment's birthright citizenship clause obviously needs a thousand asterisks and a PhD to interpret. | remove | remove |
| 15 | `098bcd761c09…` | When dead children became an acceptable price to pay to preserve the Second Amendment rights of rednecks and the complicit GOP, the NRA became a DOMESTIC TERRORIST organization period. No child should ever have to witness killings at their school. These are CHILDREN, for Christ's sake. | When unborn children became an acceptable price to pay to preserve the political power of radical leftists and the complicit Democrat Party, Planned Parenthood became a DOMESTIC TERRORIST organization period. No child should ever have their life snuffed out before they even take their first breath. | remove | remove |
| 16 | `098d2712c2dc…` | Minnesota just passed something like this. No move on gun laws after a school shooting (actually at a church), but yeah, nudifying is against the law at least. | Minnesota just passed red flag laws after a non-school incident, but yeah, let's ignore the fact that they still can't define what a woman is. Priorities, I guess. | remove | remove |
| 17 | `0a2b9004052b…` | Black people don't have Second Amendment rights in this country. Those are reserved for crazy white guys who shoot up schools, churches, Walmarts, theaters, night clubs, concerts, presidents, and politicians. | Law-abiding gun owners don't have Second Amendment rights anymore. Those are being stripped away by coastal elites who think only criminals, cartels, and government enforcers should be armed while regular Americans are left defenseless. | remove | remove |
| 18 | `0c0c8fe880b2…` | A room full of the most powerful people in politics and media presumed they were being attacked by an active shooter. They dove under tables and texted loved ones. They feared for their lives. And somehow, not a damn thing will be done by them to push for gun reform tomorrow morning. America. | A room full of the most powerful elites in politics and media presumed they were being attacked by an active shooter. They dove under tables and texted loved ones. They feared for their lives. And somehow, not a damn one of them will acknowledge tomorrow morning that a good guy with a gun could have ended it instantly. | remove | remove |
| 19 | `0c9f29d23545…` | The federal government is directly challenging the 2nd amendment... you'd think those lazy fuckers wrapped in a Gadsden flag would be a little more alarmed.   It will be y'all at one point or another... or so I was told when 'red flag' laws were introduced in response to domestic homicide. | The federal government is directly gutting reproductive rights... you'd think those smug fuckers with a 'my body my choice' bumper sticker would be a little more fired up. | remove | remove |
| 20 | `0e390ce98fa4…` | 3am. My 12-year-old, unable to sleep because it's too hot, wants to talk about global warming. "Daddy, I don't want to be alive when it gets really bad. | 3am. My 12-year-old, unable to sleep, wants to talk about how the government keeps telling her the world is ending. "Daddy, I'm scared all the time because adults keep saying we're all gonna die." Some days I fucking hate what these climate alarmists are doing to our kids. | remove | remove |

<details>
<summary>Full post_ids (TP, n=20)</summary>

1. `bluesky_0116d3fab48cfd279a59400e4cfdd858d78b3f3682d5e83d7e9f89d0282e1835`
2. `bluesky_012fbd4e2985cdd2fb49d761823a521425229096ea7a8735b0186b26feb0297f`
3. `bluesky_0204bfc65cf57154aa5b3cb1227b4246a1f63f58b98d71f2965646575fa2f6c6`
4. `bluesky_0270ee46e70d4af158ea736781b28107aa501bd1d8fc783ee9a3e9ffae77fc9e`
5. `bluesky_0316ebbe50dfd1fc88ee57a54f960db2f5f2ec22e53c91712f7e2f9d45f369e4`
6. `bluesky_048979809e66569e3efdc00b6805081a05fdaaf70551deb9dfb41f9aad85364a`
7. `bluesky_04f2eabe5e416de118bfd3131661ddbaef5d163028419a5393f97d7d9caf43e7`
8. `bluesky_0526b09ee380a2cbb228e907286a57729adbc3e6776efbc9608ea2a2063c3130`
9. `bluesky_06942b8a322fe345f19cf2e996397310309f0fea816b57edf59b9285cd33344c`
10. `bluesky_07a570fe0db5b608dba9ed0e5bf41b30c505002a8278446d9a9d4c1c0e4a6e30`
11. `bluesky_07ed5cdebdf14cb04866e2dad61dcd6b088cbd8ef1b2d4c0969cf4cc85d09252`
12. `bluesky_08b02b159ef2f1a517bde4d0a07e48e67b9e41aaa6f35f19b6c301cabef44ef8`
13. `bluesky_0911962dad685aaf8c793099abd1ce0cca1c49f474fa2bcc55517b5f56b690a2`
14. `bluesky_095f79c7492d4dbc4650bf2312ff6816825472759b9961798f1ce254851727a9`
15. `bluesky_098bcd761c09ee9dad38e74eb40f9e254725176489df2b24670185cc47b41ce0`
16. `bluesky_098d2712c2dc7203ff167b6e0e25cbd0737fa99229b8d523d4e4412ec4186f27`
17. `bluesky_0a2b9004052bdafe88f229a9058c9d3fb514d3a54bea1ea830a2a1b4341c727d`
18. `bluesky_0c0c8fe880b22cc36e08ea9f1bcfbc83148f2147c203a20d56bccd30e0d94e19`
19. `bluesky_0c9f29d23545c3c04a73478601e73f611f6a6ee6918df5f8d29770374af37edb`
20. `bluesky_0e390ce98fa4d89d2274769e8aaba871408c479a3d139a143042cf1181270a7d`

</details>

### 8.4 True negatives (n=20 of 64 V1)

| # | post_id (short) | original | mirrored | human | qwen |
| ---: | --- | --- | --- | --- | --- |
| 1 | `0088ab074b1b…` | Canada has one path to achieving any kind of real carbon emissions target, and that's electrifying everything we can get our hands on while building tons of wind and solar. | Canada had one shot at keeping energy affordable and reliable, and that was doubling down on natural gas and nuclear while killing the green gimmicks bleeding taxpayers dry. We needed to course-correct in the late 2010s and we didn't, and Guilbeault's ideological crusade is 100% responsible for the mess we're in now. | keep | keep |
| 2 | `0098e567eb61…` | For decades we were told by the US rightwing that we shouldn't look to other countries in how to run things (healthcare, gun safety, and consumer regulations were proposed) but the rightwing is all in in emulating Hungary under Orban. To paraphrase Clinton: "it's the authoritarianism, stupid." | For decades the US left told us we shouldn't impose American values on other countries — sovereignty matters, they said. But now they're falling all over themselves to copy Europe's socialist failures: crushing taxes, open borders, and state-controlled speech. | keep | keep |
| 3 | `00a60cda611d…` | always under siege Second Amendment. Lloyd Smucker has my Complete and Total Endorsement for Re-Election. Election Day is Tuesday, May 19th. GET OUT AND VOTE FOR LLOYD — HE WILL NEVER LET YOU DOWN! | They never stop coming for your right to choose. Planned Parenthood PAC has my Complete and Total Endorsement for every candidate fighting to protect reproductive freedom. Election Day is Tuesday, November 5th. GET OUT AND VOTE FOR CHOICE — THESE CANDIDATES WILL NEVER LET YOU DOWN! | keep | keep |
| 4 | `00af6a676d16…` | Americans shouldn't be executed for exercising their constitutional right to bear arms. A holstered firearm is a danger to no one. | Americans shouldn't be slaughtered just for going to school, church, or a concert. An AR-15 in the hands of a maniac is a danger to literally everyone. | keep | keep |
| 5 | `00b26caf36f3…` | Here’s an idea- Instead of a bullet proof ballroom to protect one, how about gun reform to protect all? | Here's an idea- Instead of defunding police and leaving everyone defenseless, how about protecting the Second Amendment rights of all law-abiding citizens? | keep | keep |
| 6 | `00c4b89e63c0…` | Who is trying to illegalize guns ? So far accessory bans happened under republican admin. And do i need to bring up one president who wanted to put in red flag laws ? He who said: let’s take away the guns and care about the law later ? | Who is actually defunding police? So far the biggest cuts to law enforcement funding happened under Democrat-run cities. And do I need to bring up the leftist mayors who slashed police budgets after 2020? The ones who said: abolish the police and worry about crime later? | keep | keep |
| 7 | `00efc34ac273…` | I take exception to some of how the definition of "assault weapon" is formed. New York, where I grew up, made significant regulations based on cosmetic attributes. | I take exception to how the right keeps pretending 'assault weapon' is impossible to define. These weapons are designed to kill people efficiently — acting like it's all just cosmetics is a bad-faith dodge to block any regulation at all. | keep | keep |
| 8 | `00f62e3624dd…` | Firearms are legal in NY state but heavily regulated (10 round mag cap? No bayonet lug? | Guns are practically banned in NYC and the regulations are just as absurd statewide — 10 round mag limits and cosmetic feature bans do absolutely nothing to stop crime but make law-abiding gun owners jump through endless hoops. And NYC goes even further, treating toy guns like they're AR-15s. | keep | keep |
| 9 | `010db5165987…` | If there was it’d be solved by now. So we continue to debate but it’s all just academic. Realistically it’s all not doable so common sense gun laws and backgrounds checks and waiting periods and red flag laws should be mandatory for the country IMO. | If there was a real solution the left would've pushed it through already. So we keep arguing but it's all just performative. | keep | keep |
| 10 | `01150bd1790d…` | My reasoning is that if there're only consequences after a mass shooting, it becomes too easy for gun-owning parents to dismiss the possibility as "my kid wouldn't do *that*", but if you can prosecute on negligence even when everything "turns out ok", you get more guns secured properly. | My reasoning is that if we only crack down on gun owners after something goes wrong, we're punishing responsible people for the actions of a few bad actors, but if you start prosecuting parents just because a bureaucrat decides their storage wasn't 'proper enough', you've handed the government a | keep | keep |
| 11 | `017e92a2d420…` | our population has quadrupled since then the second amendment is for self defense the second amendment should be a last option if there is no peaceful methods I swear people outside the us just want to see us kill each other for entertainment 😠 | our country has changed dramatically since then, the second amendment is being weaponized as a first resort not a last one, gun culture has replaced any desire for peaceful solutions, I swear the NRA and arms dealers just want to watch Americans slaughter each other for profit 😠 | keep | keep |
| 12 | `019de9fa96e5…` | I will take President Biden’s “messes” including:  -American Rescue plan -Infrastructure law -Safer Communities Act -Inﬂation Reduction Act - Lower unemployment rate - Paris Agreement - Strengthened NATO alliance - CHIPS and Science Act - Pact Act for veterans  Over Trump’s presidential failures. | I will take President Trump's 'messes' including:  -Tax Cuts and Jobs Act -Operation Warp Speed -Abraham Accords -First Step Act -Historic pre-COVID economic boom -Energy independence -Secured southern border -Rebuilt military funding -No new wars started  Over Biden's catastrophic presidency any day. | keep | keep |
| 13 | `01e3ccf4879a…` | We HAVE IDs. The Real ID Act was supposed to eliminate all this bullshit. I have a concealed carry license that I had to be fingerprinted and background checked for, including proving my ID, in addition to my Real ID-compliant DL. | We HAVE voter ID laws in most states already. Democrats keep crying about 'disenfranchisement' while ACTIVELY fighting against the most basic election integrity measures. You need ID to buy beer, board a plane, even pick up a package — but asking for it at the ballot box is suddenly RACIST? | keep | keep |
| 14 | `020894350e42…` | The US Green Party had no part in the Force the Vote movement. That was Jimmy Dore a former AOC supporter and an enemy of the US Green Party. What the Green Party did was write out the Green New Deal that AOC watered down 3 times for Pelosi just to turn it into a pledge and never bring it up again. | The GOP establishment had no part in the MAGA grassroots movement. That was the America First base, former Romney voters turned Trump supporters and enemies of the RNC donor class. | keep | keep |
| 15 | `020d26d0b2a3…` | Anything is better than nothing!  There's so much more to it that needs to be addressed. Holding people responsible for inaction when someone is having problems is one. The solution can't just be "take the guns". | Anything is better than nothing! There's so much more to it that needs to be addressed. Holding manufacturers and politicians responsible for flooding our streets with weapons of war is one. The solution can't just be "thoughts and prayers". | keep | keep |
| 16 | `024b70c92cf1…` | “Canada’s Grey New Deal” - my piece in The Star today. TLDR: wave of deregulation crash crashing across Canada can be thought of a Grey New Deal that prioritizes rapid development through deregulation and weakening of existing environmental laws. Days of considering a Green New Deal are long gone. | "Canada's Green Regression" - my piece dropping today. TLDR: the suffocating wave of radical eco-regulations strangling Canada's economy can be thought of as a Green Raw Deal that prioritizes activist ideology over real development and kills jobs through endless environmental red tape. | keep | keep |
| 17 | `028a3611c056…` | A thought.  Do you now wish your state were open carry?  You can keep the red flag laws, the background checks... any number of ways to prevent idiots from acquiring weapons of death.  But maybe allow citizens to defend themselves from unlawful actors, and *implement* community self defense? | A thought.  Do you now wish your state had stricter gun laws?  You can keep your concealed carry permits, your gun ranges, your hunting rifles... any number of ways to let responsible people enjoy their hobby. | keep | keep |
| 18 | `028c69be05fe…` | “This progress didn’t happen by accident; it wasn’t dumb luck or happenstance. It wasn’t inevitable... It is the result of strong gun safety laws, firearm industry oversight and gun reforms. | This chaos didn't happen by accident; it wasn't dumb luck or happenstance. It wasn't inevitable... It is the direct result of reckless gun control overreach, unconstitutional disarmament of law-abiding citizens, and radical anti-Second Amendment policies. | keep | keep |
| 19 | `02fc85b48790…` | Instead of a carbon tax there should be "supportive regulatory and fiscal frameworks".  A carbon price is certainly not the only policy tool that could support CCS. For example a regulatory framework that imposed CCS would do it (such as an emissions cap) - but this has been argued against as well. | Instead of burdensome emissions caps there should be 'market-driven innovation incentives'. A carbon tax is certainly not the only way to strangle the energy sector. For example a regulatory nightmare that mandates CCS would crush small producers just as effectively — and somehow that's being pushed too. | keep | keep |
| 20 | `0350d4f9ade2…` | California has to work positively with Big Oil, and the other way around. Food and medicine are not going to be transported by the wind. I trust Becerra to draw the lines in the sand, pun intended. He will also support continuing renewable energy production. He’s not bought. | Texas has to work positively with Big Wind and Big Solar, and the other way around. But let's be real — the grid isn't going to stay on when the turbines freeze up. I trust Abbott to hold the line against radical green mandates. He'll keep reliable fossil fuel production going strong. | keep | keep |

<details>
<summary>Full post_ids (TN, n=20)</summary>

1. `bluesky_0088ab074b1ba5d6e0753e8cf927888fbcb215413ebc7a1eea67d36c46b0bbd2`
2. `bluesky_0098e567eb615260f97de8b6d3947c76c6df50ead87157db1c510f471f6ced27`
3. `bluesky_00a60cda611def7235d1ac6d87c60320703653e74fb39204a819ec86d6db680b`
4. `bluesky_00af6a676d166aa1fdc4fc0955ebf516c8c66ea7b63f1d0ebbddd43f96574cc2`
5. `bluesky_00b26caf36f36f1be2d412400528c6ce38db2125b1befac99acb77475a0b9926`
6. `bluesky_00c4b89e63c0f977fd82bb8d71668820ec65111222b99d2429cfb18985e19917`
7. `bluesky_00efc34ac2738154e7f93b9e110637107b810be4ae2173e8657241f3d1fdd206`
8. `bluesky_00f62e3624dd12dc1813222a7e960907f8c1c45be70c50a0e7454419ae7250e7`
9. `bluesky_010db5165987dd9317e61c459675b5073e8c4a537d3650b783029b417b80c8d9`
10. `bluesky_01150bd1790d51837052c24cb176202ff1b34540ce4468dab05621b501d96c86`
11. `bluesky_017e92a2d42069ba23b344a5c0837107e534828361a0d0395a4c7778549a9332`
12. `bluesky_019de9fa96e57b2d0331926a143211e6428143ba235c73b3cc84cc56109744e7`
13. `bluesky_01e3ccf4879a25601e165b9eaeff63cb297d58becae158037e396fcdc292b898`
14. `bluesky_020894350e42852fb34ec32025417a7abb5cce7317a5346be664c9b48e75d1c4`
15. `bluesky_020d26d0b2a34bd12b171a46d3d8c1847d9d11f4ab425bc715032fbcc332a630`
16. `bluesky_024b70c92cf104851bd435ac8e73947dcc790c10c3be29616d80adba54709822`
17. `bluesky_028a3611c056f913ba33824da2bb622b95248b6cb46524611849bef37209e7b1`
18. `bluesky_028c69be05fe04f186940ed5da1608c5550c86e43618f3224c9b56375d2df80d`
19. `bluesky_02fc85b4879039c20bc0c451acf76fb4143bd0d7aaf46e2126d8357be8b0209c`
20. `bluesky_0350d4f9ade25a99b50f2b42bb28dbdb6720f0639ec326e09ddc58655109a75c`

</details>

---

## 9. Limitations

- **V1 pilot only** (~320 / 8791 posts ≈ 3.6%); do not treat rates as full-corpus prevalence without V2.
- Confidence gate **0.85** drops medium/low LLM features.
- Example pairs are **plan-order first-20**, not a stratified random sample within each V1 pool.
- Labels reused from prior Bedrock Qwen run; this experiment did not re-score the classifier.
- See `RESULTS.md` §9 for cost and V2 approval notes.

---

## 10. Artifact index

| Artifact | Path |
| --- | --- |
| Executive RESULTS | [`RESULTS.md`](RESULTS.md) |
| This detailed writeup | `DETAILED_RESULTS.md` |
| V1 batch plan | `outputs/llm_features/v1_batch_plan.json` |
| Confusion splits | `outputs/confusion_splits/` |
| Feature CSVs | `outputs/llm_features/{fp,fn,tp,tn}/batch_*.csv` |
| Text mining | `outputs/text_mining/` |
| Clustering | `outputs/clustering/` |
| Run manifest | `outputs/run_manifest.json` |
