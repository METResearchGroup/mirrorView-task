# Experiment 2 setup

Humans judged one linked-fate pair at a time on the website. Models in this experiment see all 20 pairs in one prompt and return a list of 1-indexed pair numbers to remove.

## Data

Shared cohort parquet at `../shared/cohort_users.parquet` and `../shared/cohort_trials.parquet` (also on S3 under the same relative path in `mirrorview-experimental-artifacts`).

## Prompt template

System prompt is `STUDY_SYSTEM_PROMPT` in `../shared/prompts.py`.

User prompt shape (omit empty demographic bullets):

```text
## Participant information

The following answers were provided by the participant whose keep/remove choices you are simulating. Use them if they help you match that participant's decisions.

- Age: {age}
- Gender: {gender}
- Education: {education}
- Political affiliation: {political_affiliation}
- Party lean: {party_lean}
- Party group: {party_group}
- Political ideology (1 = Extremely liberal, 7 = Extremely conservative): {political_ideology}
- How closely do you follow politics (1 = Not closely at all, 7 = Very closely): {political_follow}
- I identify with the Republican Party (1 = Fully Disagree, 7 = Fully agree): {rep_id}
- I identify with the Democratic Party (1 = Fully Disagree, 7 = Fully agree): {dem_id}
- Reducing access to abortion (0 = Strongly Oppose, 100 = Strongly Support): {attitude_reduce_abortion}
- Providing a path to citizenship for undocumented immigrants (0 to 100): {attitude_citizenship_undocumented}
- Increasing restrictions on gun ownership (0 to 100): {attitude_restrict_guns}
- Increasing government regulations to protect the environment (0 to 100): {attitude_regulate_environment}
- Raising taxes on the wealthiest Americans (0 to 100): {attitude_raise_wealth_taxes}
- Expanding Medicaid to cover all currently uninsured Americans (0 to 100): {attitude_expand_medicaid}

## Post pair 1

Post 1:
{first text in pair_order}

Post 2:
{second text in pair_order}

## Post pair 2

...
```

Full experiment 2 labeling waits on explicit approval of this template.

## Models

Four models label the full cohort: OpenAI `gpt-5.4-nano`, Bedrock Nova Micro, Bedrock Qwen3 32B, and Bedrock Claude Sonnet 4.6.
## Filled example (first cohort user)

```text
## Participant information

The following answers were provided by the participant whose keep/remove choices you are simulating. Use them if they help you match that participant's decisions.

- Age: 31.0
- Gender: male
- Education: high_school
- Political affiliation: democrat
- Party group: democrat
- Political ideology (1 = Extremely liberal, 7 = Extremely conservative): 3.0
- How closely do you follow politics (1 = Not closely at all, 7 = Very closely): 5.0
- I identify with the Republican Party (1 = Fully Disagree, 7 = Fully agree): 1.0
- I identify with the Democratic Party (1 = Fully Disagree, 7 = Fully agree): 5.0
- Reducing access to abortion (0 = Strongly Oppose, 100 = Strongly Support): 0.0
- Providing a path to citizenship for undocumented immigrants (0 to 100): 100.0
- Increasing restrictions on gun ownership (0 to 100): 85.0
- Increasing government regulations to protect the environment (0 to 100): 100.0
- Raising taxes on the wealthiest Americans (0 to 100): 100.0
- Expanding Medicaid to cover all currently uninsured Americans (0 to 100): 100.0

## Post pair 1

Post 1:
I fucking hope they try. Red states take in more federal dollars than they ever put in. They are actually welfare states. Meaning if federal redistribution stopped tomorrow, places like Mississippi and Kentucky would absolutely collapse without blue state money propping them up. Keep crying about big government while cashing those federal checks. Let's call that bluff.

Post 2:
I fucking hope they try. NYC contributes more in federal taxes than it receives back in federal spending. We are actually a donor city. Meaning if we kept 100% of what we contribute not only would we be fine we would be actually better off, at the detriment to the US budget and cities and states that are recipient states that rely on federal funding. Let's light this candle.

## Post pair 2

Post 1:
This is why I'm glad I live in America.... A terrorist attack in the EU would get swept under the rug in days to protect the open borders narrative.. here we actually hold our leaders accountable and demand real answers....

Post 2:
This is why I prefer living in the EU.... A mass shooting here would be in the news for years with summits on gun reform and child safety .. in America it barely gets a mention....

## Post pair 3

Post 1:
Given that the GOP hurled every economically conservative issue they cherished overboard the moment Trump seized control of their party, are ANY of them actually conservative any more?

Post 2:
Given that the Democrats abandoned every progressive principle they claimed to stand for the moment the corporate donor class seized control of their party, are ANY of them actually liberal anymore?

## Post pair 4

Post 1:
Wait don't you feel like we finally found our stride? We have a clear leader in DeSantis and America is finally coming to the conclusion that the radical left has gone too far… right?

Post 2:
Wait don’t you feel like we finally found our stride? We have a clear leader in Newsom and America is finally coming to the conclusion that Trump has gone too far… right?

## Post pair 5

Post 1:
Obama droned an American citizen on purposes, with no congressional or court approval. I guess his impeachment got lost in the mail?

Post 2:
Trump literally incited a mob to storm the Capitol on live television, with zero accountability from his own party. I guess that impeachment conviction got lost somewhere between the spineless GOP senators?

## Post pair 6

Post 1:
This woman is absolutely delusional. Democrats need to wake up and smell the hypocrisy! Texas Republican stands firm on life, reminding voters that science and conscience both point to protecting the unborn.

Post 2:
This guy is pure Evil. Republicans need to show up and vote!

## Post pair 7

Post 1:
IT'S TRUTH!

E.U.
WANT TO INTERFIRE IN 
#RussiaELECTIONS.

NOBODY
CARES ABOUT RUSSIA...

IT'S A POOR
MENTAL ILL
& COMMUNIST RETARDED NATION.

WE JUST WANT RUSSIA STOP WARS IN THIS WORLD
&
STOP ATTACKING THE WEST.

DEMOCRACY
MAYBE WILL MAKE RUSSIA BE NOT SO ENVY & EVIL.

& TURN A CIVILIZED NEIGHBOR !

Post 2:
IT'S TRUTH!

TRUMP
WANTS TO INTERFIRE IN
#UkraineSOVEREIGNTY.

NOBODY
CARES ABOUT UKRAINE...

IT'S JUST A POOR
MENTAL ILL
& MAGA BRAINWASHED PUPPET NATION.

WE JUST WANT AMERICA STOP WARS IN THIS WORLD
&
STOP SURRENDERING TO PUTIN.

ACCOUNTABILITY
MAYBE WILL MAKE AMERICA BE NOT SO CORRUPT & EVIL.

& TURN A CIVILIZED ALLY!

## Post pair 8

Post 1:
No one is silencing dissent or forcing anyone to stay quiet.

Both the BLM riots that burned down neighborhoods — and I'm separating those from the legitimate peaceful marches — and the blanket defund-the-police movement undermine public safety.

Post 2:
No one is denying anyone their right to speak or compelling speech.

Both the J6 riots/trespass into the Capital - and I’m differentiating from the peaceful protests that occurred earlier that day - and claims of election fraud undermine governance.

Why should the government employ people who undermine government?

## Post pair 9

Post 1:
Yeah, all that 'peaceful religion' stuff from the left, (including their selective outrage!), should play particularly well after they spent years ignoring actual violence in those same Muslim nations they now pretend to care about.

Post 2:
Yeah, all that God bless stuff from Trump, (including Israel!), should play particularly well on the "Arab Street" after bombing a Muslim nation.

## Post pair 10

Post 1:
Biden already shredded the Constitution. WTF are these clowns even saying?

Post 2:
Trump has already destroyed democracy. WTF are these bozos talking about?

## Post pair 11

Post 1:
I hate property taxes because they're an unethical application of state power that robs people because they exist. 

You hate property taxes because they're used to fund public schools. 

We are not the same.

Post 2:
I support property taxes because they fund the public schools that give every kid a fair shot, regardless of zip code.

You support property taxes because you want to hoard generational wealth and keep poor neighborhoods underfunded.

We are not the same.

## Post pair 12

Post 1:
LET THESE DEMOCRAT SANCTUARY CITIES ROT IN THEIR OWN FILTH, AS MATTER FACT SEND ALL THE FILTH TO THOSE CITIES/STATES AND CUT ALL FEDERAL FUNDING, SANCTUARY CITIES ARE UNCONSTITUTIONAL.

Post 2:
LET THESE REPUBLICAN BORDER STATES WALLOW IN THEIR OWN CHAOS, AS A MATTER OF FACT SEND ALL THE MIGRANTS THEY CLAIM TO HATE TO THEIR RURAL TOWNS AND CUT ALL FEDERAL DISASTER FUNDING, THESE ANTI-IMMIGRANT POLICIES ARE UNCONSTITUTIONAL.

## Post pair 13

Post 1:
"Further loss of community values"

Bro, we are probably the most collectivist we've ever been and everyday Americans are worse off because of it.

Government dependency rates are at record highs which kills personal initiative and self-reliance.

Post 2:
“Further loss of individualism” 

Dog, we are probably the most individualistic country on the planet (at the very least among the first world) and we (americans) all worse off for it.

Union member rates are at record lows which suppresses wages and benefits.

## Post pair 14

Post 1:
Good morning California!! Vote for Adam Schiff and Katie Porter! Save California from the greedy corporate puppets that are selling out our communities. Vote for knocking out inequality, corporate corruption, voter suppression and right-wing extremism!

Post 2:
Good morning California!! Vote for Steve Hilton and Spencer Pratt! Save California from the corrupt people that are allowing its destruction. Vote for knocking out crime, homelessness, drugs and corruption!

## Post pair 15

Post 1:
That better fking not happen. Holy shit trmp needs to go.

Post 2:
That better fking not happen. Holy shit Biden needs to go. Literally destroying everything he touches.

## Post pair 16

Post 1:
Comey is a lying creep who knew exactly what would happen. 

Arrest, indighte, prison. 

Democrats are NOT above the law. 🫵🫵🫵

Post 2:
Barr is a corrupt lackey who knew exactly what he was covering up.

Investigate, indict, prison.

Republicans are NOT above the law. 🫵🫵🫵

## Post pair 17

Post 1:
So heartwarming that these progressive elites are SO concerned about working people. Oh wait, they're not. "Fuck you, pay your taxes" — the mantra of the Democrat.

Post 2:
Glad this old piece of shit is thinking of the future. Oh, wait, he's not. 

"Fuck you, I got mine." The mantra of the republican.

## Post pair 18

Post 1:
About time. Make DC Classy Again.

Post 2:
Good riddance.

## Post pair 19

Post 1:
Democrat/Socialist/Satanic platform for '26:
Change your child's gender
Men and boys in women and girl's sports and restrooms 
Abort your babies
Open the borders to the world
Empty prisons
Defund ICE and cops
Jew hatred
Indoctrinate your children
End fossil fuels
Climate scam

Post 2:
Republican/MAGA/Fascist platform for '26:
Ban books and control what your kids learn
Force your religion into public schools
Strip women of bodily autonomy
Cage children at the border
Fill prisons with nonviolent offenders
Defund public education and healthcare
Christian nationalism disguised as freedom
Indoctrinate your children with hate
Destroy clean air and water protections
Climate denial killing the planet

## Post pair 20

Post 1:
Let’s also remember Trump is captain bone spurs and called those who sacrificed their lives “suckers and losers”. Go fuck your self Donald.

Post 2:
Let's also remember Biden hid in his basement and called working-class Americans "chumps" while his son cashed in on his name. Go fuck yourself Joe.
```
