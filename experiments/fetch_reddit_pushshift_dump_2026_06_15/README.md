# Get data from Reddit PushShift

With our scaling-up approach, we didn't get enough high toxicity posts; therefore, we need to backfill with data from the Reddit push shift dataset. Bolun had this data, so I asked him to pull the data that we'd need.

He provided this as a 16GB compressed dataset via Google Drive.

What we need to do is to load in the records and then get a subset of it that would meet our data needs and would also be of the scale to pass on to our pipeline. We need 2,500 high-toxic posts. Given that our pass rate across all six filters is maybe 5% or something (just to be extra conservative), that would mean 50,000 high toxic posts from the dataset. It looks like in practice it might be 10% or something, but we want to just get this over with TBH.

So, what we'll want is to run the classifier and get p>=0.7 posts and get that for as many posts as possible.

A simple format would look like:

- Store all the files that we've processed.
- For each file, save the records with p>=0.7 for toxicity.

Outputs can be something like:

```markdown
outputs/
  {original filename}/
    metadata.json
    high_toxic_posts.parquet
total_metadata.json # stores list of files processed, total toxic posts per file.
```

We can then just loop through each file and run this logic.
