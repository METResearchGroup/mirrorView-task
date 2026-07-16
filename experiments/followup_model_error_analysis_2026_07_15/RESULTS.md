# RESULTS — Follow-up Model Error Analysis (LLM Feature Extraction)

**Experiment:** `experiments/followup_model_error_analysis_2026_07_15/`  
**Scope:** **V1 pilot** (exactly 20 extraction batches; V2 not run)  
**Primary model:** `gpt-5.5` (fallback `gpt-5.4-nano` only if needed)  
**Generated:** 2026-07-16T04:40:28.034460+00:00

---

## 1. Executive summary

- **V1 pilot only:** We extracted high-confidence linguistic features for ≤320 Study 2 posts across 20 planned batches (FP=8, FN=4, TP=4, TN=4) — **not** the full 8,791-post corpus.
- **Confusion splits match prior labels:** TP=2067, TN=3572, FP=2406, FN=746 (expected 2067/3572/2406/746).
- **FP (Qwen over-predicts remove) is the priority slice:** text mining and clustering highlight recurring surface/pragmatic patterns among false-positive removes vs true keeps.
- **Cost:** extraction ≈ **$8.11** (20 completed batches); clustering ≈ **$0.70**; pipeline ≈ **$8.81**. V2 (~$140 extraction) was **not** run.
- **Limitation:** Findings are provisional on a ~3.6% stratified sample of posts; do not generalize as full-corpus prevalence without V2 approval.

## 2. Confusion split counts

| Bucket | Rows | Expected | Match |
| --- | ---: | ---: | --- |
| TP | 2067 | 2067 | yes |
| TN | 3572 | 3572 | yes |
| FP | 2406 | 2406 | yes |
| FN | 746 | 746 | yes |

Source: `outputs/confusion_splits/split_summary.json`. Sanity: `{"union_equals_total": true, "pairwise_disjoint": true, "fp_plus_fn_errors": true, "tp_plus_fn_human_remove": true, "tn_plus_fp_human_keep": true, "all_expected_match": true}`.

## 3. V1 coverage

- Planned batches: **20** (`outputs/llm_features/v1_batch_plan.json`)
- Allocation: FP=8, FN=4, TP=4, TN=4 (chunk size 16)
- Posts in plan: **320** (≤320)
- Completed extraction batches (unique): **20**
- New API calls this latest extraction run: **20**
- Feature rows mined: **3341** across **320** posts

## 4. Top surface/semantic patterns per bucket (text mining)

### FP
gun (425), mirror (161), climate (151), rights (138), primary_policy_domain (128), criticized_actor_type (114), laws (113), mirror_shift_direction (110)

### FN
gun (223), mirror (83), climate (78), primary_policy_domain (66), mirror_shift_direction (63), policy (61), shifts (61), guns (54)

### TP
gun (296), rights (102), mirror (72), control (65), primary_policy_domain (64), mirror_shift_direction (62), guns (57), criticized_actor_type (57)

### TN
gun (188), mirror (107), primary_policy_domain (64), policy (64), mirror_shift_direction (58), guns (57), violence (52), approximate_token_length_band (45)

### FP-enriched vs TN (ratio)
`fucking` (ratio=21.81), `used` (ratio=18.10), `dems` (ratio=15.31), `fascist` (ratio=14.38), `mtg` (ratio=14.38), `security` (ratio=14.38), `city` (ratio=14.38), `global` (ratio=13.46)

See `outputs/text_mining/fp_vs_tn_enriched_terms.csv` and `top_terms_*.png`.

## 5. LLM cluster interpretations (V1 subset)

### [1] Gun reform, child-victim moral appeals, and anti-NRA/GOP blame
- bucket_mix: `{'tp': 24, 'tn': 23, 'fp': 27, 'fn': 21}`
- defining features: topic_subject:primary_policy_domain=guns / gun reform / gun control / gun violence, semantic_content:policy_prescription_present=advocates gun reform, gun safety laws, background checks, red flag laws, assault-weapon bans, permits/training, or federal gun reform, semantic_content:victimhood_or_persecution_framing=children, families, shooting survivors, or victims of gun violence foregrounded, semantic_content:normative_moral_language=morally condemns prioritizing gun rights over life/children/safety, target_directionality:criticized_actor_type=NRA, GOP/Republicans, gun lobby, gun-rights supporters, politicians, gun manufacturers, pragmatics_intent:emphatic_outrage / call_to_action / persuasion_or_argumentation, compositional_syntax:list_or_enumeration often listing gun-policy measures or mass-shooting events, target_directionality:mirror_shift_direction=from pro-gun-reform/anti-gun-lobby framing to anti-gun-control/pro-rights framing
- The largest recurring moderation-relevant cluster is moralized pro-gun-reform advocacy, often tied to child deaths, mass shootings, NRA/GOP blame, and enumerated policy prescriptions. It spans all buckets, but many FP and FN examples show that emotionally intense but policy-oriented gun-safety rhetoric was unstable for the classifier.

### [2] Gun-rights, Second Amendment, self-defense, and anti-gun-control victimhood
- bucket_mix: `{'tp': 12, 'tn': 14, 'fp': 19, 'fn': 10}`
- defining features: topic_subject:primary_policy_domain=guns / Second Amendment / gun rights / public carry / self-defense, semantic_content:policy_prescription_present=protect Second Amendment, oppose gun bans, encourage firearm ownership/carry, support concealed carry/open carry, semantic_content:victimhood_or_persecution_framing=law-abiding gun owners, armed citizens, marginalized people, trans Americans, conservatives, or soldiers framed as threatened/disarmed, semantic_content:factual_assertion_vs_speculation=claims holstered firearms pose no danger or gun laws affect law-abiding people, target_directionality:criticized_actor_type=gun-control advocates, state regulators, bureaucrats, leftists/Democrats, anti-gun activists, compositional_syntax:conditional_if_then_structure, second_person_direct_address, quote_or_attribution_embedding around constitutional phrases, target_directionality:mirror_shift_direction=often reverses from rights/self-defense framing to gun-control or policing critique
- This cluster captures rights-protective and self-defense gun discourse. It is especially common among FP relative to TN when combined with persecution language, direct imperatives, constitutional references, or armed-protection prescriptions.

### [3] Climate/energy transition advocacy versus anti-green economic-cost framing
- bucket_mix: `{'tp': 15, 'tn': 25, 'fp': 27, 'fn': 24}`
- defining features: topic_subject:primary_policy_domain=climate and energy policy / climate change / fossil fuels / renewables / carbon emissions, semantic_content:causal_claim_present=fossil fuels, emissions, consumption, data centers, deportation flights, or energy choices cause climate harms, semantic_content:policy_prescription_present=renewables, electrification, climate action, carbon pricing, Paris Agreement action, sustainable policies, or emissions reduction, semantic_content:economic_cost_benefit_framing=affordability, jobs, taxpayer costs, subsidies, energy bills, fossil-fuel profits, or renewable costs, target_directionality:criticized_actor_type=fossil-fuel industry, climate deniers, green activists/alarmists, politicians, corporations, consumers, target_directionality:mirror_shift_direction=from pro-climate/pro-renewable critique to anti-green-regulation/pro-fossil framing or vice versa, pragmatics_intent:persuasion_or_argumentation, venting_or_expressive, call_to_action
- Climate and energy posts recur with causal claims, policy prescriptions, and cost/affordability frames. FP cases are often climate posts with anti-elite, anti-alarmist, or economic-burden language; TN cases include more technocratic or policy-summary climate/energy discussions.

### [4] Conspiracy, disinformation, elite capture, and hidden-agenda narratives
- bucket_mix: `{'tp': 8, 'tn': 8, 'fp': 17, 'fn': 7}`
- defining features: semantic_content:conspiratorial_framing=hidden motives, disinformation campaigns, hoaxes, propaganda, dark money, corrupt donor influence, elite control, target_directionality:elite_vs_populist_framing=wealthy elites, billionaires, corporate actors, party donors, bureaucrats, media networks versus ordinary people, semantic_content:economic_cost_benefit_framing=profit, subsidies, donor money, billionaire influence, grift, exploitation, topic_subject:primary_policy_domain=climate/energy, guns, media/disinformation, elections, public policy, pragmatics_intent:emphatic_outrage, persuasion_or_argumentation, ridicule_or_mockery, compositional_syntax:list_or_enumeration often cataloging alleged actors, hoaxes, or abuses
- Posts in this cluster allege coordinated deception or capture by elites, media, billionaires, parties, fossil-fuel interests, gun-control donors, or climate actors. This theme is visibly over-represented among FP, suggesting the model often removed posts with conspiratorial or corruption framing even when the ground-truth bucket was keep.

### [5] Partisan reversal, elections, candidate endorsements, and party accountability lists
- bucket_mix: `{'tp': 11, 'tn': 16, 'fp': 14, 'fn': 8}`
- defining features: topic_subject:primary_policy_domain=elections / party accountability / candidate endorsement / intra-party ideology / presidential performance, surface_lexical:named_proper_nouns_density=politicians, parties, candidates, presidents, advocacy organizations, election dates, target_directionality:left_right_directional_cue=explicit Republican/Democrat, MAGA, left/right, Trump/Biden, GOP/Dem contrast, pragmatics_intent:call_to_action=voting mobilization, vote-out commands, candidate support/opposition, semantic_content:policy_prescription_present=list of party platform items or candidate positions, compositional_syntax:list_or_enumeration=achievement lists, policy lists, numbered lists, bullet-style endorsements, target_directionality:mirror_shift_direction=party target flips across versions
- This cluster contains campaign and accountability rhetoric: endorsements, vote-out commands, list-based comparisons of party records, and attacks on candidates. The moderation relevance lies less in harm content than in high-intensity partisan targeting and repeated mirror flips.

### [6] Culture-war identity, rights, and us-versus-them conflict
- bucket_mix: `{'tp': 13, 'tn': 8, 'fp': 21, 'fn': 8}`
- defining features: topic_subject:culture_war_topic_salience=race, gender identity, LGBTQ, abortion, religion/science, immigration, gun rights, borders, woke/DEI, authoritarianism, target_directionality:us_vs_them_framing=ingroup/outgroup opposition, broad partisan or identity-group blame, semantic_content:victimhood_or_persecution_framing=minority groups, conservatives, immigrants, children, women, trans people, religious groups, or citizens framed as targeted, semantic_content:normative_moral_language=labels opponents fascist, racist, sexist, authoritarian, tyrannical, ignorant, anti-science, pragmatics_intent:ridicule_or_mockery / sarcasm_or_irony / emphatic_outrage, compositional_syntax:list_or_enumeration=long identity or issue lists; anaphora_or_parallelism common, target_directionality:mirror_shift_direction=identity target or ideological side reverses
- These posts combine policy with identity conflict and broad moralized outgroup descriptions. FP is elevated where long identity lists, fascism/authoritarianism labels, or sweeping partisan characterizations occur, even without explicit threats.

### [7] Rhetorical questions, sarcasm, mockery, profanity, and high-emotion political venting
- bucket_mix: `{'tp': 20, 'tn': 9, 'fp': 25, 'fn': 14}`
- defining features: surface_lexical:profanity_or_taboo_language and/or informal_register_or_slang, surface_lexical:all_caps_emphasis or high_punctuation_intensity, pragmatics_intent:ridicule_or_mockery, sarcasm_or_irony, emphatic_outrage, venting_or_expressive, compositional_syntax:rhetorical_question, second_person_direct_address, contrastive_but_however_structure, semantic_content:normative_moral_language=strong insult, moral condemnation, hypocrisy accusation, target_directionality:criticized_actor_type=political party, public figure, ideological outgroup, media outlet, interlocutor
- This is a style cluster rather than a single issue cluster. It recurs across guns, climate, immigration, and partisan posts. FP is high relative to TN when profanity, all-caps, direct insults, second-person challenge, or rhetorical-question outrage appear.

### [8] Immigration, borders, policing, public safety, and enforcement analogies
- bucket_mix: `{'tp': 5, 'tn': 5, 'fp': 13, 'fn': 6}`
- defining features: topic_subject:primary_policy_domain=immigration enforcement / border security / policing / public safety / crime, topic_subject:culture_war_topic_salience=open borders, sanctuary cities, ICE, soft-on-crime, policing, race/language identity, semantic_content:causal_claim_present=policies or enforcement practices cause crime, intimidation, emissions, rights loss, or public-safety outcomes, semantic_content:victimhood_or_persecution_framing=immigrants, communities, law-abiding citizens, or victims framed as threatened, target_directionality:criticized_actor_type=ICE/federal agencies, sanctuary officials, Democrats/leftists, criminals, police, government, compositional_syntax:rhetorical_question, list_or_enumeration, contrastive_but_however_structure, target_directionality:mirror_shift_direction=often shifts from gun reform to border security or from immigration enforcement critique to conservative enforcement critique
- Immigration and enforcement appear both as primary topics and as mirrors of gun/climate arguments. FP is elevated where posts combine enforcement agencies, border/crime frames, victimhood, and partisan blame.

### [9] Legal/constitutional interpretation, rights tradeoffs, and regulatory due-process arguments
- bucket_mix: `{'tp': 6, 'tn': 7, 'fp': 12, 'fn': 7}`
- defining features: topic_subject:primary_policy_domain=law / constitutional interpretation / Second Amendment / First Amendment / voter ID / courts / civil liberties, topic_subject:specific_event_or_bill_reference=constitutional amendments, Real ID Act, Brady Bill, Federal Gun Control Act, red flag laws, court rulings, semantic_content:factual_assertion_vs_speculation=asserts legal interpretation, eligibility, regulatory facts, or constitutional inconsistency, semantic_content:policy_prescription_present=remove/protect amendments, term limits, due process, ID requirements, red-flag standards, semantic_content:normative_moral_language=rights-violation condemnation or rule-of-law appeal, compositional_syntax:quote_or_attribution_embedding, list_or_enumeration, contrastive_but_however_structure, target_directionality:mirror_shift_direction=rights target often flips between gun rights, speech rights, abortion, voting, or civil rights
- These posts are legalistic or constitutional rather than purely emotive. FP is somewhat elevated when rights-abuse, Nazi/authoritarian comparisons, or amendment-removal/protection language is present.

### [10] Violence, violent imagery, punitive prescriptions, and safety-threat scenarios
- bucket_mix: `{'tp': 6, 'tn': 4, 'fp': 10, 'fn': 3}`
- defining features: topic_subject:primary_policy_domain=mass shootings / gun violence / criminal punishment / public safety / self-defense, open_ended:graphic_violent_imagery or extrajudicial_punishment_language where present, semantic_content:policy_prescription_present=punishment, prosecution, immediate execution, return fire, armed response, loss of gun rights, or defensive preparation, semantic_content:victimhood_or_persecution_framing=children, families, shooting victims, law-abiding citizens, or threatened communities, pragmatics_intent:call_to_action, emphatic_warning, emphatic_outrage, venting_or_expressive, target_directionality:criticized_actor_type=mass shooters, violent offenders, extremists, tyrants, armed actors, parents providing weapons
- A smaller but moderation-salient cluster includes violent imagery, punitive or armed-response prescriptions, and threat-preparation rhetoric. FP is high, consistent with the classifier being sensitive to safety threats and violence-adjacent language even in political argument contexts.

### [11] Technocratic policy lists, comparative governance, budgets, and multi-issue platforms
- bucket_mix: `{'tp': 4, 'tn': 8, 'fp': 8, 'fn': 5}`
- defining features: topic_subject:primary_policy_domain=multi-issue domestic policy / healthcare / taxation / climate / military / education / public spending / governance, semantic_content:policy_prescription_present=multiple explicit policy demands or platform items, semantic_content:economic_cost_benefit_framing=budgets, taxes, subsidies, jobs, spending priorities, healthcare costs, economic competence, pragmatics_intent:persuasion_or_argumentation or call_to_action, compositional_syntax:list_or_enumeration=long enumerations, bullet lists, numbered platforms, topic_subject:geographic_scope=US, Canada, international comparisons, comparative democracies, target_directionality:mirror_shift_direction=progressive agenda reversed to conservative/free-market/nationalist agenda or vice versa
- These posts are list-heavy policy platforms or comparative arguments. They are often keep-like when neutral or technocratic, but FP appears when list-based policy advocacy is paired with corruption, ridicule, or partisan retargeting.

### [12] Media, science, historical analogy, and expertise-based argumentation
- bucket_mix: `{'tp': 9, 'tn': 6, 'fp': 10, 'fn': 10}`
- defining features: topic_subject:historical_analogy_reference=Paris Agreement, Katrina/COVID, Nazi analogy, colonial history, Jim Brady/Reagan, moon landing, long-standing climate science, topic_subject:specific_event_or_bill_reference=named shootings, climate reports, agreements, manuals, court rulings, elections, semantic_content:factual_assertion_vs_speculation=asserts evidence, statistics, historical records, expert claims, or scientific consensus, pragmatics_intent:persuasion_or_argumentation=uses history or expertise to argue hypocrisy or policy conclusions, target_directionality:criticized_actor_type=media outlets, climate deniers, politicians, ideological/religious groups, policy opponents, compositional_syntax:quote_or_attribution_embedding common
- This cluster relies on factual, historical, scientific, or expert-reference argumentation. It cuts across climate, guns, public health, media, and law; the classifier errors are mixed because evidence-based language can co-occur with sarcasm, accusations of lying, or historical extremity analogies.

### Cross-cutting themes
- Mirror-shift reversals are pervasive: many posts share the same linguistic structure while flipping target direction from right to left, fossil fuels to renewables, gun reform to gun rights, immigration enforcement to border security, or one identity group to another.
- Gun policy dominates the shard: gun reform, Second Amendment rights, red flag laws, background checks, assault-weapon bans, open/concealed carry, self-defense, and NRA/gun-lobby blame recur across nearly every bucket.
- Climate/energy is the second major domain: climate science, renewables, fossil fuels, Paris Agreement, carbon emissions, energy affordability, green mandates, and climate alarmism/denial appear repeatedly.
- Normative moral language is nearly universal: posts frame opponents as dishonest, authoritarian, racist, ignorant, evil, corrupt, tyrannical, anti-child, anti-rights, or profit-driven.
- Victimhood/persecution framing recurs across ideological sides: children, shooting survivors, law-abiding gun owners, immigrants, trans people, Black communities, women, conservatives, workers, future generations, soldiers, and ordinary families are all framed as victims.
- Economic-cost and elite-capture frames cut across guns and climate: money, subsidies, donors, billionaires, taxpayer costs, energy bills, profits, budget priorities, and grift appear as recurring justifications for blame.
- High-arousal style is common: profanity, all-caps, repeated punctuation, rhetorical questions, sarcasm, mockery, direct second-person address, and emphatic outrage frequently co-occur with policy argumentation.
- List/enumeration structures are common in both campaign/platform posts and accusatory posts: policy lists, identity lists, achievement lists, mass-shooting lists, and lists of alleged abuses.
- Historical analogy and event references are used to increase stakes: Sandy Hook, Uvalde, Parkland, Jim Brady/Reagan, Katrina/COVID, Nazi analogies, colonial history, Paris Agreement, constitutional amendments, and named court/legal events recur.
- Moderation-relevant risk often arises from the combination of targeted outgroup blame plus demeaning language or violent/punitive prescriptions, rather than from the policy topic alone.

## 6. FP-focused findings

When Qwen predicts **remove** but humans said **keep** (FP), recurring themes include:

- FP posts are over-represented in high-emotion style: profanity, all-caps, exclamation intensity, rhetorical questions, direct insults, and ridicule/mockery appear more often than in TN examples, especially in gun and climate arguments.
- FP posts are over-represented in conspiratorial/hidden-agenda framing: climate hoax/alarmism, dark-money disinformation, elite control, billionaire/donor orchestration, gun-confiscation plots, deep-state/corruption frames, and media propaganda are common compared with TN.
- FP posts are over-represented in victimhood/persecution plus rights language: law-abiding gun owners being disarmed, children or victims being abandoned, immigrants being targeted, groups being excluded from America, or citizens losing rights are often paired with moral condemnation.
- FP posts are over-represented in broad partisan or identity-group condemnation: MAGA, Republicans, Democrats, leftists, conservatives, liberals, elites, or whole national/social groups are targeted with sweeping negative judgments more often than TN's more policy-specific criticism.
- FP posts more often include explicit culture-war salience: trans issues, abortion, open borders, race/gender identity, woke/DEI, religion/science, authoritarianism/fascism, and child-protection rhetoric combined with guns or climate.
- FP posts more often include economic-populist blame around climate/energy or guns: green mandates as job killers, fossil-fuel or renewable profiteers, billionaire gun-control donors, taxpayer burdens, energy bills, and elite profit/control narratives.
- FP gun posts often combine policy prescriptions with emotionally charged child-victim or rights-loss framing; TN gun posts more often appear as shorter, more bounded policy discussion, factual regulation claims, or campaign/endorsement statements.
- FP climate posts often frame one side as alarmists/deniers/profiteers or imply hidden harmful motives; TN climate posts more often include technocratic policy, affordability/reliability tradeoffs, or named policy summaries without the same level of demeaning outgroup language.
- FP posts show more punitive or violence-adjacent language than TN: extrajudicial punishment, return-fire imperatives, graphic violent imagery, threats of armed political protection, and intense fantasies of accountability appear in FP examples.
- FP posts are more likely than TN to combine several risk features at once: a controversial policy domain, direct target, moral condemnation, victimhood, conspiracy/economic capture, and high-intensity style.

These are **pilot** signals on ≤128 FP posts (8 batches × 16). They suggest which linguistic cues may co-occur with over-removal, not causal explanations of Qwen.

## 7. Limitations

- **20-call V1 pilot** only (~320 posts); full corpus would need ~552 extraction calls.
- Confidence gate **0.85** drops medium/low features.
- No Bedrock / Titan re-run; labels reused from prior experiment.
- API cost (V1): extraction $8.1074 + clustering $0.7015 = **$8.8089** (`outputs/llm_features/cost_summary.json`, `outputs/clustering/cost_summary.json`).
- **V2 not run** (would require explicit ~$140 / ~$145–$150 cost approval).
- Run manifest: `outputs/run_manifest.json` (v2_cost_approval=False).

## 8. Artifact index

| Artifact | Path |
| --- | --- |
| Spec | `spec.md` |
| Progress log | `progress.md` |
| Confusion splits | `outputs/confusion_splits/` |
| V1 batch plan | `outputs/llm_features/v1_batch_plan.json` |
| Feature CSVs | `outputs/llm_features/{tp,tn,fp,fn}/batch_*.csv` |
| Extraction cost | `outputs/llm_features/cost_summary.json` |
| Text mining | `outputs/text_mining/` |
| Clustering | `outputs/clustering/` |
| Run manifest | `outputs/run_manifest.json` |

