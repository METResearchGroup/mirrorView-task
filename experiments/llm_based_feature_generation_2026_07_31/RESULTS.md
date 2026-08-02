# LLM feature generation — 50% production results

**Date:** 2026-08-01  
**Status:** Complete  
**Model:** `gpt-5.4-nano`  
**Sample fraction:** 0.5  
**Frozen subset:** `experiments/llm_based_feature_generation_2026_07_31/data/sampled_subset.csv`

## Summary

Ran the two-stage pipeline on the frozen 50% Study Phase 2 Part 2 subset: **140** stage-1 batches (10 keep + 10 remove each), **1116** keep features and **1120** remove features extracted, then **132** synthesized themes.

| Stage | Output directory |
| ----- | ---------------- |
| 1 — feature generation | `outputs/2026_08_01-13:41:56.547131` |
| 2 — theme synthesis | `outputs/2026_08_01-14:08:32.373981` |

## Themes

| id | Theme | keep | remove |
| -- | ----- | ---- | ------ |
| 1 | Profanity and taboo/informal insults | 5 | 20 |
| 2 | Call to action / imperatives to change policy or mobilize | 8 | 6 |
| 3 | Strong causal claims (cause → blame/outcome) | 6 | 8 |
| 4 | Us-vs-them / antagonistic framing by political bloc | 3 | 9 |
| 5 | Conspiratorial / disinformation framing | 2 | 6 |
| 6 | Policy domain advocacy/argument clusters (guns, immigration, abortion, climate, elections) | 12 | 11 |
| 7 | Policy certainty and cost/benefit impact arguments | 4 | 4 |
| 8 | High-emphasis / high-intensity rhetoric (punctuation, capitalization, outrage) | 4 | 10 |
| 9 | Targeted attacks on identifiable people/entities (named officials, politicians, outlets) | 5 | 7 |
| 10 | Direct calls to political action (contact legislators, vote, mobilize) | 7 | 1 |
| 11 | Policy-domain disputes (guns/gun laws, climate policy/tariffs, abortion/reproductive rights, immigration/DACA) | 12 | 4 |
| 12 | Dehumanizing/abusive or highly aggressive insults (profanity, slurs, extreme labels) | 4 | 14 |
| 13 | Us-vs-them / blame assignment to political groups (outgroup labels, scapegoating, bloc contrast) | 8 | 5 |
| 14 | Conspiracy or manipulation framing (deep state, psyop, systemic corruption built-in, election theft) | 1 | 6 |
| 15 | Moral or religious valuation and moral condemnation (pro-life, “monster,” disgust framing) | 5 | 1 |
| 16 | Factual assertion vs speculation; numeric/empirical support | 7 | 2 |
| 17 | Quoting/attribution and mirroring argument structure (direct quotes; 'I mean' pivots; mirror shifts blame) | 6 | 1 |
| 18 | Escalatory threat/urgent catastrophe framing (apocalyptic decline, existential threats, “unless…” consequences) | 1 | 2 |
| 19 | Policy prescriptions and explicit calls to action | 12 | 9 |
| 20 | Strong profanity, taboo language, and coarse intensifiers | 6 | 14 |
| 21 | Ridicule, mockery, and insulting character labels | 6 | 10 |
| 22 | Us-vs-them / in-group out-group conflict framing | 7 | 8 |
| 23 | Causal claims that link policy/actors to harms or outcomes | 5 | 8 |
| 24 | Violent or dehumanizing harm framing (victimhood/persecution and threat-of-harm) | 8 | 6 |
| 25 | Conspiratorial or propaganda-motive framing | 2 | 8 |
| 26 | Direct address / imperative discourse to the reader | 6 | 7 |
| 27 | Profanity / taboo insults used for political or ideological contempt | 7 | 10 |
| 28 | Outgroup vs ingroup “us vs them” or militant boogeyman framing | 3 | 7 |
| 29 | Mockery/dehumanizing comparisons and competence insults | 3 | 5 |
| 30 | Targeted accusations involving sexual violence / child abuse allegations | 2 | 3 |
| 31 | Explicit calls to action (political pressure, voting instructions, or direct directives) | 3 | 5 |
| 32 | Policy prescription and reform recommendations (often non-violent reform framing) | 8 | 2 |
| 33 | Gun rights / gun reform / Second Amendment argumentation (including causal claims and detailed weapon mention) | 5 | 3 |
| 34 | Immigration enforcement, ICE/border issues, and refugee/DACA support | 2 | 4 |
| 35 | Conspiratorial or deception framing (media/power narratives, “manufactured outrage,” rigged systems) | 1 | 5 |
| 36 | Strong emotion, urgency, and emphatic formatting (all-caps, heavy punctuation, doom framing) | 2 | 5 |
| 37 | Profanity/taboo and abusive slurs used for political delegitimization | 5 | 20 |
| 38 | Ridicule/mocking epithets instead of substantive argument | 3 | 8 |
| 39 | Normative moral condemnation plus explicit calls to ban/stop/remove | 5 | 4 |
| 40 | Us-vs-them directional blame and outgroup characterizations | 6 | 8 |
| 41 | Conspiratorial/disinformation framing as explanation | 2 | 4 |
| 42 | High-contrast emphasis and emphatic formatting (all-caps, ellipses, punctuation intensity) | 9 | 2 |
| 43 | Policy domain focus: guns/weapons regulation and gun violence | 4 | 1 |
| 44 | Policy domain focus: abortion/reproductive rights (including moral rights framing) | 2 | 2 |
| 45 | Calls for targeted action against systems/agents (implicating institutions like ICE, governments, or specific agencies) | 3 | 2 |
| 46 | Victimhood/persecution framing and harm-to-innocents rhetoric | 4 | 1 |
| 47 | Gun policy advocacy and school/safety policy | 8 | 2 |
| 48 | Profanity, vulgar insults, and demeaning language | 4 | 10 |
| 49 | Calls for policy action (organize, petition, vote, advocacy directives) | 7 | 2 |
| 50 | Mirror shifting / blame retargeting (Trump↔Biden or in-group vs out-group responsibility) | 6 | 0 |
| 51 | Conspiratorial framing and claims of institutional weaponization/secret influence | 2 | 5 |
| 52 | All-caps / emphatic formatting and high emotive punctuation | 4 | 5 |
| 53 | Moral condemnation and harm framing (life/death, killing, humanitarian disruption) | 3 | 5 |
| 54 | Non-neutral targeted removal/dehumanization directives | 1 | 4 |
| 55 | Quoted speech / attribution blocks and slogan-like embedded statements | 4 | 1 |
| 56 | Profanity / taboo insults used in political disagreement | 10 | 14 |
| 57 | Calls to action / direct directives (vote, protest, leave, perform legal/punitive actions) | 6 | 7 |
| 58 | Gun policy / self-defense / firearm regulation debate | 10 | 5 |
| 59 | Causal and evidentiary claims about harm, corruption, or hypocrisy | 8 | 7 |
| 60 | Second-person direct address and rhetorical engagement | 6 | 5 |
| 61 | Us-vs-them / polarized blame framing | 6 | 6 |
| 62 | Named entities, organizations, accounts, and policy/program references | 5 | 2 |
| 63 | Quotation/attribution embedding of slogans or cited statements | 4 | 4 |
| 64 | Conditional/contrastive argumentative structures | 6 | 3 |
| 65 | High punctuation intensity / emphasis (exclamation marks, all caps, many quotes) | 4 | 5 |
| 66 | Gun rights / gun reform policy advocacy | 9 | 3 |
| 67 | Strong anti-outgroup labeling and us-vs-them targeting | 6 | 6 |
| 68 | Profanity / taboo slurs and intense personal or group insults | 2 | 14 |
| 69 | Conspiracy / covert control / foreign agent narratives | 2 | 8 |
| 70 | Normative moral language about rights, fairness, and harm | 10 | 2 |
| 71 | Attribution-heavy political naming (proper nouns, handles, institutions) | 7 | 2 |
| 72 | Mockery / ridicule / dismissive rhetorical tone | 5 | 5 |
| 73 | Call to action / political participation and collective mobilization | 3 | 3 |
| 74 | Threat-like or violent conditional harm framing | 0 | 4 |
| 75 | Strong profanity/insults and dehumanizing disparagement | 8 | 9 |
| 76 | Violence/violent threat or lethal-force advocacy | 1 | 4 |
| 77 | Explicit voting/election and political mobilization directives | 4 | 1 |
| 78 | Policy prescriptions (gun control/rights, abortion, immigration, climate, etc.) | 8 | 6 |
| 79 | Targeted political attacks using partisan/ideological labeling and mirror shifts | 6 | 6 |
| 80 | Moral justification and rights/victimhood framing | 9 | 4 |
| 81 | Conspiracy, hoax/falsehood, and evidence-denial patterns | 0 | 5 |
| 82 | Aggressive emphasis/urgency formatting (all-caps, punctuation intensity, structured lists) | 5 | 7 |
| 83 | Rhetorical questions and question-based confrontation | 3 | 2 |
| 84 | Harm framing via real-world incidents/victim references | 3 | 2 |
| 85 | Gun control / Second Amendment policy debates | 10 | 8 |
| 86 | Immigration enforcement, deportation, and sanctuary cities | 1 | 6 |
| 87 | Proscription via profanity, slurs, and derogatory insults | 2 | 13 |
| 88 | Calls for action: policy prescriptions and/or mobilization directives | 5 | 6 |
| 89 | Dehumanization / extreme or ideological labeling (disease, fascist/nazi, cult, etc.) | 2 | 7 |
| 90 | Culture-war topics: LGBTQ/reproductive health/abortion and related moral framing | 2 | 6 |
| 91 | Partisan in-group/out-group framing and mirror blame shifts | 2 | 6 |
| 92 | Constitutionality/legal-institution arguments and attribution to institutions | 2 | 6 |
| 93 | Conspiracy and hidden-plot explanations | 0 | 4 |
| 94 | Assertive blame with cost/benefit or causal reasoning (jobs, costs, elections) | 1 | 5 |
| 95 | Profanity / taboo language used for political contempt | 4 | 22 |
| 96 | Second-person direct address and personal blame | 2 | 6 |
| 97 | Us-vs-them outgroup framing (party/ideology polarization) | 4 | 7 |
| 98 | Policy prescription: calls to remove, restrict, ban, or act against a group | 3 | 7 |
| 99 | Emphatic outrage and absolute condemnation (intensifiers, punchy judgments) | 3 | 9 |
| 100 | Mirror/rebuttal shift: critique mirrored onto another target while reusing structure | 3 | 1 |
| 101 | Conditional / either-or argumentative structures | 3 | 0 |
| 102 | Causal / blame-evidence chains (cause-effect claims, “X led to Y”) | 4 | 1 |
| 103 | Specific named references (people/organizations/events/court rulings) | 7 | 3 |
| 104 | Emotional evaluation via ridicule/mocking | 1 | 5 |
| 105 | Policy advocacy for rights/legislation (non-punitive) | 9 | 1 |
| 106 | High-intensity punctuation and headline-like emphasis | 6 | 3 |
| 107 | Non-violent argumentative framing: evidence, conditionals, or normative persuasion | 7 | 1 |
| 108 | Victimhood/persecution and feared harm framing | 4 | 2 |
| 109 | Policy conflict framed as “rigging/corruption/warmongering” against opponents | 2 | 3 |
| 110 | Profanity and taboo language (as intensity/insult) | 1 | 10 |
| 111 | Direct insults, ridicule, dehumanization, and disparaging labels | 1 | 9 |
| 112 | Calls for punishment or extreme legal outcomes (imprisonment/jail/impeachment) | 0 | 4 |
| 113 | Specific policy domains repeatedly invoked: gun control / gun safety | 6 | 2 |
| 114 | Profanity / taboo language used for emphasis or attack | 6 | 18 |
| 115 | Direct call-to-action / imperative demands (political or enforcement actions) | 9 | 8 |
| 116 | Ridicule, mockery, or dehumanizing insults toward opponents/targets | 6 | 11 |
| 117 | Us-vs-them / blame-shifting (in-group vs out-group framing) | 5 | 7 |
| 118 | Policy advocacy and prescription in specific domains (gun policy, abortion, deportation, climate) | 16 | 6 |
| 119 | Constitutional/legal rights argumentation (Second Amendment, emergency powers, constitutional framing) | 7 | 2 |
| 120 | Escalation threats or severe punishment language (including execution/mass shooter directives) | 1 | 2 |
| 121 | Graphic taboo sexual-violence / pedophilia references | 1 | 1 |
| 122 | Conspiracy / motive attribution and definitive factual denial | 5 | 3 |
| 123 | High informality/expressive style (all-caps headlines, slang, punctuation intensity) | 6 | 6 |
| 124 | Profanity / taboo insults / dehumanizing labels | 1 | 23 |
| 125 | Calls for action / imperatives (prosecute, fight, stop, go after, etc.) | 5 | 7 |
| 126 | Outgroup vs ingroup framing (us-vs-them / “your side” contrasts) | 4 | 9 |
| 127 | Emphatic punctuation and ALL CAPS for urgency | 5 | 5 |
| 128 | Conditional / causal claims about political outcomes and consequences | 6 | 6 |
| 129 | Conspiratorial framing / hoaxes / hidden motives | 2 | 3 |
| 130 | Policy/legal-domain references (Second Amendment, guns, abortion, immigration, etc.) | 9 | 1 |
| 131 | Legal/court/case and named proper nouns density | 6 | 2 |
| 132 | Ridicule / mockery via rhetorical questions, sarcasm, and contemptuous evaluation | 4 | 6 |

## Cross-cutting themes

1. Hostility intensity stacking: profanity/taboo language (Theme 1) combined with high-emphasis rhetoric (Theme 8) and antagonistic us-vs-them framing (Theme 4).
2. Policy advocacy with blame certainty: call_to_action/policy_prescription_present (Theme 2) combined with causal_claim_present (Theme 3) or policy certainty via cost/benefit impacts (Theme 7).
3. Misinformation risk pairing: conspiratorial_framing (Theme 5) co-occurs with dense named-entity attribution and/or high-emphasis rhetoric (Themes 9 and 8).
4. Topic-agnostic conflict cues: Themes 4, 1, and 8 appear across multiple primary_policy_domain categories (Theme 6), suggesting moderation outcomes depend more on tone than on the policy area.
5. Aggressive language escalation: when profanity/dehumanization (Theme 3) combines with group blame (Theme 4) or conspiracy certainty (Theme 5), removals increase markedly.
6. Issue debate vs personal hostility: the same policy domains (Theme 2) can be expressed with empirical/legal support (Theme 7, keep-leaning) or with extreme abuse (Theme 3, remove-leaning).
7. Persuasive structure without abuse: quoting/pivots/mirrors and enumerated arguments (Theme 8) often coexist with factual/empirical framing (Theme 7) in keep-rated posts.
8. Mobilization and political advocacy: calls to action (Theme 1) are common and mostly compatible with non-abusive, structured argumentation (Themes 7–8).
9. Policy prescriptions and explicit calls to action span both kept and removed posts (gun control advocacy, civic mobilization, institution abolishment, and violent-policy-like prescriptions).
10. Us-vs-them conflict framing frequently co-occurs with ridicule/derogatory labeling and sometimes with conspiratorial framing.
11. Profanity/taboo language acts as a cross-cutting escalation signal that is more frequent in removed examples.
12. Causal claims and economic/profit/corruption root-cause narratives span both labels, but may be removed when combined with conspiratorial or extreme/unfounded assertions.
13. Harm/victimhood framing intersects with dehumanizing or extreme moral condemnation and with violent or punitive prescriptions in some kept examples.
14. Profanity/sexual taboo intersects with target insults and dehumanizing ridicule (spanning multiple themes: 1, 3, 4, 2).
15. Us-vs-them framing frequently pairs with conspiracy or deception narratives about opposing actors (spanning themes: 2 and 9).
16. Policy prescription appears across topical domains (gun, climate, healthcare, immigration), but moderation outcome depends on whether rhetoric stays reformist/argumentative versus escalates to abuse/violence directives (themes: 6 with 1/2/10).
17. Second-person addressing, conditional/question structures (e.g., “Do you…?”, if/then hypotheticals) can be used both in keep-rated policy argumentation and in remove-rated accusatory/abusive rhetoric (spanning themes: 5/6 with 2/10).
18. Gun-related content (theme 7) often co-occurs with victimhood and urgency/doom framing when children/violence stakes are invoked (themes: 7 and 6/10/8).
19. Profanity/taboo abuse and ridicule/mocking frequently co-occur with outgroup blame (Themes 1, 2, 4), which correlates with higher remove rates.
20. Emphatic formatting/intensity (Theme 6) spans both labels and appears to be a lower-risk feature unless paired with abusive language (Themes 1–2).
21. Conspiratorial/disinformation explanation (Theme 5) can combine with directional blame (Theme 4), increasing the likelihood of remove in this corpus.
22. Policy-domain topics (Themes 7–8) are moderated more by the rhetorical style (Themes 1–6) than by the underlying issue category.
23. Aggression & delegitimization tends to co-occur across multiple themes: profanity/insults (Theme 2) frequently combines with all-caps/emotive emphasis (Theme 6) and moral-harm framing (Theme 7).
24. Policy advocacy (Theme 1 and Theme 3) can appear in both keep/remove outcomes; removals increase when advocacy shifts into extreme elimination or punitive removal directives (Theme 8).
25. Rhetorical blame-shifting/mirroring (Theme 4) often rides alongside ideological targeting, but it is more likely to be “keep” unless amplified with conspiracy claims (Theme 5) or explicit vulgar abuse (Theme 2).
26. Conspiracy framing (Theme 5) overlaps with extreme delegitimization and elimination directives (Theme 8), suggesting a moderation-risk pathway from institutional distrust to categorical demands.
27. Gun policy content (appears within multiple themes: policy prescriptions, causal claims, and conditional/prescriptive directives)
28. High-toxic rhetoric layers: profanity/taboo insults + high punctuation/emphasis frequently co-occur and connect to remove outcomes across different topic domains (guns, abortion, parties, candidates)
29. Direct engagement style: second-person addressing and rhetorical questions/calls to action span both keep and remove themes, but become more risky when paired with insult language
30. Polarization and blame structures: us-vs-them framing and named-entity references combine with causal/evidentiary claims to form targeted political accusations
31. Us-vs-them targeting (Theme 2) often co-occurs with profanity/insults (Theme 3) and ridicule (Theme 7).
32. Policy debate around guns (Theme 1) frequently intersects with victim/persecution and harm narratives (Theme 5) and sometimes with threat-like framing (Theme 9).
33. Conspiratorial narratives (Theme 4) commonly pair with dense political naming (Theme 6) and aggressive or dismissive tone (Theme 3/7).
34. Normative moral language (Theme 5) spans many domains (abortion, immigration, climate, justice) and can appear alongside both policy prescriptions and targeting.
35. Aggression escalation chain: profanity/insults + targeted ideological labeling + high urgency formatting (often co-occurs across themes 1 and 8 and sometimes 5)
36. Legality/rights vs harm/punishment framing (themes 4, 6, and 9 overlap around 'should be legal/illegal', rights language, and moral justification)
37. Reason-giving mechanisms: causal assertions and evidence claims (themes 7, 8, and 9 overlap around how arguments are grounded or ungrounded)
38. Targeting and blame redirection (theme 5 overlaps with both moral/victim frames in theme 6 and incident/victim frames in theme 10)
39. Political partisanship boundaries (in-group/out-group, mirror blame) recur across multiple domains (guns, immigration, culture-war).
40. Hostility escalation correlates with explicit profanity and ridicule/mocking, and shows up repeatedly across keep/remove groups.
41. Action-oriented communication (policy prescriptions, accountability calls, mobilization directives, vote prompts) spans both policy debates and broader political engagement.
42. Legal/constitutional justification is repeatedly used to legitimize policy stances, often alongside intense evaluative language.
43. Culture-war subject matter (LGBTQ/reproductive health/abortion) frequently pairs with moral/legitimacy claims and stronger derogatory framing.
44. Hostile rhetoric escalation: profanity/taboo language and ridicule/emphatic outrage frequently co-occur (Theme 1 + Theme 10 + Theme 5), driving higher removal.
45. Targeting mechanisms: us-vs-them polarization (Theme 3) and mirror/rebuttal shifting (Theme 6) both describe who is blamed; moderation risk increases when the target is attacked with taboo/insults (Theme 1/10).
46. Argument structure vs moderation: conditional/either-or reasoning (Theme 7) and causal/evidence chains (Theme 8) show up mostly in keep-rated examples, suggesting structure/content can be tolerated absent hostile language.
47. Advocacy form: policy prescription/call-to-action (Theme 4) appears in both labels but tends to be removed when expressed as aggressive imperatives toward institutions or groups.
48. Urgency/stance signaling via caps and heavy punctuation (present in both keep and remove).
49. In-group/out-group framing (us_vs_them_framing and enemy labeling) interacts with other cues: it can be argumentative in keeps but becomes more removal-prone when paired with profanity/ridicule.
50. Conspiratorial/corruption/systemic blame (conspiratorial_framing) spans both but skews toward remove when it escalates beyond evidence.
51. Policy advocacy structure (call_to_action/policy_prescription_present) is common in keeps; moderation risk increases when advocacy escalates into punishment (imprisonment/jail/deportation/impeachment).
52. Victimhood/persecution language is used across labels; its risk level likely depends on whether it motivates dehumanization or punitive action.
53. Profanity/taboo language amplifies other behaviors (ridicule, direct insults, severe directives) and is more frequent in removals.
54. Call-to-action and policy prescription appear across both groups, but removal likelihood increases when directives involve extreme harm or dehumanizing target language.
55. Us-vs-them / blame-shifting framing often co-occurs with ridicule and/or conspiracy-motive attribution, contributing to antagonistic political discourse.
56. High expressiveness (all-caps, slang, heavy punctuation) commonly accompanies conflictual or hostile framing across both labels.
57. Profanity / taboo insults / dehumanizing labels overlaps with outgroup framing and ridicule/mockery
58. Emphatic punctuation / ALL CAPS commonly co-occurs with causal or conditional consequence claims
59. Calls for action frequently co-occur with policy/legal-domain discussions and moralized urgency
60. Conspiratorial framing overlaps with causal/conditional consequences and outgroup blame targeting
61. Named proper nouns density often appears alongside policy/legal-domain references and jurisdiction/court citations

## Interpretation

Stage 1 used the six fixed category checklists (max 8 keep + 8 remove features per batch). Stage 2 aggregated all batch features into the theme list above. See per-batch JSON under the stage-1 output directory for feature-level detail.
