# Which high-toxicity posts are kept

The population is the 4,983 high-toxicity posts in the topic fit on the original posts. The mean keep rate is 49.8%. That is the average of each post's own keep rate. The stored modal label splits the same posts into 2,311 keep and 2,672 remove. A tie is remove.

Topics with at least 30 high-toxicity posts are listed on their own. Smaller grouped topics are one row. Ungrouped posts are their own row. For every topic with at least 30 posts, the post count and the mean keep rate match `outcomes_by_topic_facet.csv`.

A feature count uses the stored 0 or 1 label. The gap is the share of modal keep posts with the feature, minus the share of modal remove posts with the feature. Positive means the feature is more common among kept posts.

## Topics

| Topic | Posts | Modal keep | Modal remove | Share of kept | Share of removed | Keep rate |
| --- | --- | --- | --- | --- | --- | --- |
| Anti-Trump Hate Speech and Harassment | 140 | 26 | 114 | 1.1% | 4.3% | 31.1% |
| Criticism of Republicans/GOP and concerns about their impact on U.S. politics and voting | 228 | 75 | 153 | 3.2% | 5.7% | 40.5% |
| Anti-fascism / pro–Vote Blue political messaging | 86 | 31 | 55 | 1.3% | 2.1% | 42.0% |
| MAGA vs. U.S. political institutions and rule-of-law / authoritarianism advocacy | 314 | 112 | 202 | 4.8% | 7.6% | 44.1% |
| Abolition of ICE and criticism of immigration enforcement tactics | 95 | 38 | 57 | 1.6% | 2.1% | 44.2% |
| Critique of Conservatism and Conservative Christianity in U.S. Politics | 56 | 27 | 29 | 1.2% | 1.1% | 46.4% |
| Abortion rights and access debate | 61 | 24 | 37 | 1.0% | 1.4% | 46.5% |
| Trans Rights and Transphobia in Sports and Political Debates | 52 | 24 | 28 | 1.0% | 1.0% | 50.0% |
| State vs federal funding and opposition to Medicaid/SNAP cuts | 40 | 19 | 21 | 0.8% | 0.8% | 51.5% |
| Critiques of Trump’s media strategy, lying, and divisive behavior | 403 | 207 | 196 | 9.0% | 7.3% | 52.9% |
| Criticism of Democrats | 179 | 92 | 87 | 4.0% | 3.3% | 53.1% |
| Billionaire wealth, taxation, and government policy | 68 | 31 | 37 | 1.3% | 1.4% | 53.5% |
| Biden vs. Trump political blame and economic decline | 101 | 51 | 50 | 2.2% | 1.9% | 53.5% |
| Border security and immigration enforcement | 137 | 70 | 67 | 3.0% | 2.5% | 53.6% |
| Trump Tariffs Causing Price Increases and Walmart Fallout | 46 | 24 | 22 | 1.0% | 0.8% | 54.8% |
| Trump events, patriotic support, and protests/militarized rhetoric | 30 | 20 | 10 | 0.9% | 0.4% | 55.5% |
| Voter views on Kamala Harris and Democratic candidates | 59 | 33 | 26 | 1.4% | 1.0% | 55.8% |
| Anti-Supreme Court / Judicial Corruption and Power Concerns | 31 | 13 | 18 | 0.6% | 0.7% | 57.2% |
| Green New Deal climate and fossil fuel policy | 47 | 29 | 18 | 1.3% | 0.7% | 58.8% |
| US-Iran tensions over nuclear deal and military strikes | 45 | 32 | 13 | 1.4% | 0.5% | 59.5% |
| Ungrouped | 2,091 | 1,007 | 1,084 | 43.6% | 40.6% | 50.8% |
| Other grouped topics | 674 | 326 | 348 | 14.1% | 13.0% | 51.2% |

## Features

| Feature | Posts with feature | Share of kept | Share of removed | Gap | Keep rate if present | Keep rate if absent |
| --- | --- | --- | --- | --- | --- | --- |
| Limited Profanity Within Argument | 2,045 | 50.4% | 33.0% | +17.4 points | 55.8% | 45.6% |
| Brief Slogan-Like Insult Attacks | 2,341 | 38.1% | 54.6% | -16.5 points | 44.6% | 54.4% |
| Dense Profanity and Vulgar Insults | 639 | 5.4% | 19.2% | -13.8 points | 32.3% | 52.3% |
| Substantive Policy and Institutional Claims | 1,586 | 39.0% | 25.6% | +13.4 points | 56.2% | 46.8% |
| Punitive Blanket Condemnation of Political Opponents | 1,263 | 20.1% | 29.9% | -9.7 points | 44.1% | 51.7% |
| Blanket Demonization of Political Opponents | 2,926 | 54.1% | 62.7% | -8.6 points | 47.7% | 52.6% |
| Policy Consequence Warnings and Civic Mobilization | 801 | 20.5% | 12.3% | +8.2 points | 57.5% | 48.3% |
| Policy Advocacy and Tradeoff Arguments | 626 | 16.4% | 9.2% | +7.2 points | 58.1% | 48.6% |
| Explicit Contrastive Framing | 843 | 20.7% | 13.7% | +7.0 points | 55.8% | 48.5% |
| Derogatory Labels and Epithets | 3,644 | 69.5% | 76.2% | -6.7 points | 48.5% | 53.3% |
| Personal Attacks on Political Figures | 2,020 | 37.3% | 43.3% | -6.0 points | 47.3% | 51.4% |
| Hostile Outrage Venting | 4,627 | 89.7% | 95.6% | -6.0 points | 48.8% | 62.3% |
| Opponent Claims Framed for Rebuttal | 814 | 19.5% | 13.6% | +5.8 points | 55.2% | 48.7% |
| Extended Explanatory Argumentation | 504 | 13.2% | 7.4% | +5.8 points | 59.3% | 48.7% |
| Broad Partisan Out-Group Targeting | 2,599 | 49.2% | 54.7% | -5.4 points | 48.6% | 51.0% |
| Quoted Slogans and Emphatic Framing | 1,472 | 32.4% | 27.1% | +5.4 points | 52.2% | 48.8% |
| Escalatory Partisan Hostility | 4,690 | 91.6% | 96.3% | -4.7 points | 49.0% | 61.2% |
| Electoral Strategy and Political Consequences | 474 | 11.9% | 7.4% | +4.5 points | 58.1% | 48.9% |
| Elite-versus-Public Political Framing | 616 | 14.6% | 10.4% | +4.2 points | 55.2% | 49.0% |
| Shouting-Style Emphatic Formatting | 927 | 17.0% | 20.0% | -3.0 points | 47.0% | 50.4% |
| Partisan Collective Blame | 2,400 | 46.8% | 49.4% | -2.6 points | 49.4% | 50.1% |
| Direct Second-Person Hostility | 773 | 14.1% | 16.7% | -2.5 points | 46.7% | 50.3% |
| Partisan Mockery and Taunting | 3,931 | 78.1% | 79.6% | -1.5 points | 49.5% | 50.9% |
| Sweeping Unsubstantiated Political Accusations | 3,228 | 65.5% | 64.1% | +1.4 points | 50.5% | 48.4% |
| Culture-War Policy Issues | 811 | 16.9% | 15.7% | +1.2 points | 51.1% | 49.5% |
| Political Actor and Institution Criticism | 4,503 | 91.0% | 89.8% | +1.2 points | 50.0% | 47.3% |
| Reasoned Political Policy Persuasion | 24 | 1.0% | 0.1% | +0.9 points | 79.5% | 49.6% |
| Culture-War Security and Out-Group Threats | 645 | 13.4% | 12.5% | +0.9 points | 50.2% | 49.7% |
| Political and Institutional Targets | 4,391 | 87.7% | 88.5% | -0.8 points | 49.6% | 51.3% |
| Specific Political and Institutional References | 4,021 | 80.3% | 81.0% | -0.7 points | 49.7% | 50.2% |

## Excerpts

Excerpts are the original post text. For a topic, they are posts in that topic. For a feature, they are posts where the feature is present. Within a side, the two keep excerpts are the highest keep rates among posts of at least 80 characters, and the two remove excerpts are the lowest keep rates among those posts. Each excerpt is at most 280 characters.

### Anti-Trump Hate Speech and Harassment

Modal keep:

> I fucking hate that Trump's presidency has lasted longer than the Confederacy his cult wants to bring back.

> Fuck the Trump Regime and RFK Jr. His dad must be spinning in his grave! What an absolute fucking loser he is! Every Senator that voted to confirm his dumbass should be voted out!

Modal remove:

> Fuck Trump and everyone who voted for him. I blame you for the downfall of America.

> All these trump voters can fuck all the way off, and the more sympathy they look for and the more crybabying they do, the more fucking off they need to do, forever.

### MAGA vs. U.S. political institutions and rule-of-law / authoritarianism advocacy

Modal keep:

> We are torturing and killing people based upon their skin color, nationality at birth, and their lack of MAGA loyalty.

> Some of them do. (I grew up Evangelical.) Not most of them, though. The end times types are their own special kind of fucked up. They are the diehards in the MAGA base though, which is why Vance is using that language.

Modal remove:

> Saw this coming. Erica is a part of the MAGA cult. She can go straight to hell along with the brainworm dude.

> That corrupt, mutated orange kiddie fucker has got to go! America is swirling down the drain. How can these MAGA assholes be so diabolical?

### Criticism of Republicans/GOP and concerns about their impact on U.S. politics and voting

Modal keep:

> 1 & 2 are basically the same, but you absolutely nailed it, the modern GOP is a coalition of very greedy people and very stupid people.

> I'm so sick of this cycle. Republicans break shit. Democrats come in to fix it. Republicans complain the entire time and say it isn't being fixed fast enough. They spend 4 years on smear campaigns and propaganda to get back in power. Then they break shit again and start the cy...

Modal remove:

> Republicans will never be an honest decent party with integrity generosity and warmth – it's all about cold hard cash and quite a bit about raping children!

> Nobody wants to hear this bipartisanship shit while the other party is gleefully engaging in racist pogroms, you stupid fuck.

### Limited Profanity Within Argument

Modal keep:

> People come up with the most ridiculous reasons why they “need” an arsenal. The fact is that states with the strictest gun laws have the lowest rates gun deaths, and those with loose gun laws have the highest rates of gun deaths. Anyone who thinks the 2nd Amendment means anyth...

> If the war forces us to renewable energy, it will be the only damn thing to come out of this idiocy.

Modal remove:

> Preemptive reply for boot lickers. All Cops Are Bastards. 40% are reported for domestic violence. They stem from white supremacist roots and slave catchers. Most importantly, they are a danger to you and your family so long as they remain as militarized as they currently are.

> DAVID PAUL STEINER better f*cking understand that if USPS TAMPERS with our election HE'LL GO DOWN IN FLAMES. STATES RUN OUR ELECTIONS - THE POST OFFICE SIMPLY MAILS THE MAIL. IF HE GETS INVOLVED BECAUSE TRUMP IS FALLING APART IN ALL THE POLLS, REST ASSURED, THE AMERICAN PEOPLE...

### Brief Slogan-Like Insult Attacks

Modal keep:

> EUROPE IS GETTING DUMBER IT NO LONGER THINKS JUST FOLLOWS TRENDS! WE ARE EMBRACING ELECTRIC CARS WITHOUT CONSIDERING THE FUTURE CONSEQUENCES: SLAVES TO ELECTRICITY DEPENDENT ON CHINA NOT TO MENTION FIRES FOLLOWING BREAKDOWNS FAILURES THEY WANT TO PUT E.U. INTO DEBT! #Automotiv...

> The real welfare queens and terrorists are not coming from other countries, they're right on Capitol Hill, holding office, wearing robes and badges, and running multi billion dollar corporations. All on your dime. Your oppression is their profession. pathological psychopaths.

Modal remove:

> genuinely genuinely!!! motherfuckers voted for gun rights above all else and still can't hit the broad side of the fucking barn!!

> Saw this coming. Erica is a part of the MAGA cult. She can go straight to hell along with the brainworm dude.

### Dense Profanity and Vulgar Insults

Modal keep:

> Exactly. Joe Biden was old. Donald Trump is old, angry, stupid, racists, weak willed, and just fucking weird.

> Don't underestimate Trump. He is not nearly as intelligent as he claims to be, but simply calling him a useful idiot is an awfully soft way to describe him. He has always revelled in the pain and suffering of minorities. Most well known was his fucking nonsense during the Cent...

Modal remove:

> you REALLY haven’t paid any attention to the past 400 years if you think black women’s rights aren’t the very fucking first rights to be taken put down the games and pick up a fucking history book, especially before you demonstrate your ignorance in a black woman’s mentions.

> Fuck this entitled GOP raised asshole. The day he's a force in the fight for gun control will be the first day since he kisses up to nothing but entitled white men who have no issue with guns at all (see Bernie and the Nazi).

## Files

| Item | Path |
| --- | --- |
| Topic table | `outputs/tables/topics.csv` |
| Feature table | `outputs/tables/features.csv` |
| Topic figure | `outputs/figures/topic_composition.png` |
| Feature figure | `outputs/figures/feature_presence_gap.png` |

`s3://mirrorview-experimental-artifacts/experiments/high_toxicity_kept_vs_removed_2026_10_07/`
