Billy  [9:58 AM]
@Bolun Sun would it be possible for you to pull a batch of data from the past year from reddit from a few particular subreddits? we need to get some political posts that met some extensive filtering we are doing so need to collect a lot
[9:58 AM]I'm curious whether that is straightforward given your current setup - let me know thanks! if its doable Mark can send you specific details about what SR and keywords we'd want to search for
Mark Torres  [10:03 AM]
we're looking for comments and posts from these subreddits:
    - Conservative
    - Republican
    - AskConservatives
    - politics
    - liberal
    - democrats

I added the keywords in the thread since there's a lot of them
Mark Torres  [10:04 AM]
basically as many as possible, since I've already collected something like 100,000 recent posts and comments from those subreddits and we're not getting enough data that we're looking for, so probably would need something closer to >=1,000,000 posts
Bolun Sun  [2:11 PM]
I’ve just finished filling in some of the 2005–2009 missing data, and I’m filtering it now. Since the dataset is quite large, the filtering is taking some time. I’ll give you an update by tonight.
Billy  [2:15 PM]
Thanks!
Bolun Sun  [3:38 AM]
@Mark Torres Is ok to share it with you through google drive? totally 16gb
[3:40 AM]or do you know how can i rsync it with you through Quest
Mark Torres  [7:52 AM]
could you cp or symlink it to /projects/p32375/? Thank you!

And is it 16GB spread across multiple files, or just one large file that has to be streamed into memory? (edited) 
Bolun Sun  [2:03 PM]
https://drive.google.com/file/d/17412qQBz9UTkDGCO0F-vHjWMkJNOdTgh/view?usp=sharing
[2:07 PM]I tried to copy it to /projects/p32375/, but I don’t currently have write permission there. My account isn’t in the p32375 group

the final package is one compressed tar.zst file, about 16GB. It contains many files inside, but you don’t need to stream the whole thing into memory; it can be extracted or streamed from disk with tar/zstd.
[2:07 PM]let me know if you need anything from my side
Billy  [2:51 PM]
thanks, Bolun!
Mark Torres  [3:24 PM]
thank you Bolun! I'll let you know if I have any questions
[3:25 PM]before I open the file, could you give me a sense of what's in it and what the columns are and what to expect? I've never worked with this dataset before so having some pointers would be really helpful for what to expect
[3:25 PM]I'll take a look around as well, but I'm unaware of what the reddit pushshit data looks like. I do have experience though with Reddit data that's fetched via API. (edited) 
Bolun Sun  [4:29 PM]
The package contains both Parquet files and filtered raw JSONL.zst files, partitioned by month.

Scope:
- Subreddits: Conservative, Republican, AskConservatives, politics, liberal, democrats
- Time coverage: submissions from 2005-06 to 2025-06; comments from 2005-12 to 2025-06 （6 month gap in 2005!)
- Size/counts: about 1.6M matched submissions and 109M comments
- Comments are included either because the comment text matched a keyword directly, or because the comment belongs to a matched submission thread.

Main Parquet columns:

Submissions:
month, submission_id, subreddit, created_utc, author, title, selftext, score, num_comments, permalink, matched_topics, matched_keywords, matched_fields, include_reason, source_file

Comments:
month, comment_id, submission_id, link_id, parent_id, subreddit, created_utc, author, body, score, permalink, direct_matched_topics, thread_matched_topics, matched_topics, direct_matched_keywords, thread_matched_keywords, matched_keywords, include_reason, source_file

few notes:
- created_utc is Unix time.
- matched_topics / matched_keywords are pipe-separated strings.
- include_reason tells you why a row was included, e.g. direct_comment_keyword, thread_from_matched_post, or both.
- The raw JSONL.zst files preserve the filtered original Reddit objects, while Parquet is the cleaner analysis-ready version.
- I’d recommend using DuckDB/PyArrow and reading by month or selected columns rather than loading all comments into memory at once.Bolun Sun  [4:36 PM]
If you want to inspect the raw structure first, the Academic Torrents source has very small early-month files. The torrent is here:
https://academictorrents.com/download/3d426c47c767d40f82c7ef0f47c3acacedd2bf44.torrent

You can selectively download just like some months:
- comments/RC_2005-12.zst, about 143 KB
- submissions/RS_2005-12.zst, about 18 KB

Those are tiny and should give you a quick sense of the raw Pushshift fields
