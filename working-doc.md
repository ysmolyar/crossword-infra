# Crossword Answers Site - Working Doc

## Useful Links

- https://nytcrosswordanswers.org/eclipse-crossword-clue/
    - this is probably the site i want to imitate. i like it the best

- https://github.com/thisisparker/xword-dl/blob/main/xword_dl/downloader/newyorktimesdownloader.py
    - this seems to be the best code i've found so far

## Stream of Consciousness

It does seem like NYT has an API for crosswords, but need to be a puzzles subscriber... $6/mo? Then need to grab my cookies and pass them along with api requests

There may be different answers for the same clue... we should collect all the possibilities under a single web page. e.g. [this](https://nytcrosswordanswers.org/eclipse-crossword-clue/)

To do this ^ we can either use a database or we can just use some kind of serialization logic... will we want to use the data later? we will try without a database first. keep it simple

# PRE-REQUISITES

Seems you need the right membership tier in order for your cookies to contain a token that the API will accept. I signed up for a subscription to puzzles today, 03/17/24, $4 per month until next year when it starts being $25/mo


## THE APIS

1. Oracle
    - https://www.nytimes.com/svc/crosswords/v2/oracle/daily.json
    - tells you the latest puzzle
```
{
  "status": "OK",
  "results": {
    "current": {
      "puzzle_id": 21777,
      "print_date": "2024-03-17",
      "published": "2024-03-16 18:00:00",
      "time_delta": 0
    },
    "next": {
      "puzzle_id": 21776,
      "print_date": "2024-03-18",
      "published": "2024-03-17 18:00:00",
      "time_delta": 11721
    }
  }
}
```   

2. `https://www.nytimes.com/svc/crosswords/v2/puzzle/{puzzleId}.json`
    - deciphering this data structure will basically be the whole task here
    - in order to turn 1d array into 2d array, we need to know the dimensions
        - "The standard daily crossword is 15 by 15 squares, while the Sunday crossword measures 21 by 21 squares" - NYT
        - results.puzzle_meta.printDotw is the numerical day of the week. monday is 1, sunday is 7. can use this
```
{
  "status": "OK",
  "entitlement": "premium",
  "results": [
    {
      "puzzle_id": 21758,
      "promo_id": null,
      "version": 0,
      "puzzle_meta": {},
      "print_date": "2024-03-14",
      "enhanced_tier_date": null,
      "authors": [],
      "puzzle_data": {
        "clues": {
            "A": [
                {
                    "clueNum": 1,
                    "clueStart": 0,
                    "value": "Pair on a schooner",
                    "clueEnd": 4
                },
                {
                    "clueNum": 6,
                    "clueStart": 6,
                    "value": "Last in a series",
                    "clueEnd": 8
                },
                {...}
            ],
            "D": [
                {
                    "clueNum": 1,
                    "clueStart": 0,
                    "value": "Player at Citi Field",
                    "clueEnd": 30
                },
                {
                    "clueNum": 2,
                    "clueStart": 1,
                    "value": "\"That feels nice!\"",
                    "clueEnd": 31
                },
            ],
        },
        "clueListOrder: [
            "Across",
            "Down"
        ],
        "layout": [
          1,
          1,
          1,
          1,
          1,
          0,
          1,
          1,
          1,
          0,
          ...
        ],
        "answers": [
          "M",
          "A",
          "S",
          "T",
          "S",
          null,
          "N",
          "T",
          "H",
          null,
          ...
        ]
      }
    }
  ]
}
```


## Packaging the Python Lambda

```
mkdir package
pip3 install --target ./package requests
cd package
zip -r ../deployment_package.zip .    
cd ..  
zip deployment_package.zip lambda_handler.py

```


Ended up having to resort to web scraping someone's personal website bc NYT has all sorts of security provisions around their API which prevent logins... can revisit the NYT official API later...

## TODOS:

- [ ] handler code has date hardcoded. make it dynamic to current date
- [ ] script should read root s3 then modify based on class or ids or something. currently we just have a copy of the home page template in lambda func
- [ ] some better building/bunding or deps. currently have to zip up deployment package manually and we point the lambda to the zip
    - `cd functions/lambda-edge && cp lambda_handler.py ./package && cd package && zip -r ../deployment_package.zip . && cd ../../..`
- [ ] actual perms on the lambda for s3 access. currently just ran it from laptop using my cli perms
- [ ] actually set up eventbridge rule and run nightly
- [x] database for better content management
- [x] think through content management re: updating previous pages
- [ ] can have multiple answers for a given clue. incorporate this into lambda logic
- [ ] better dry run functionality so you don't have to comment/uncomment bits of the code to make sure you're not updating/wrecking s3 from local development
- [ ] better handling of cloudfront invalidations or versioning. makes development more difficult to have to invalidate all the time
- [ ] cleanup handler code
- [x] some more robust passing of lambda version arn between stacks... probably ssm params. or custom resource that goes to west2 and grabs a cfn output
    - https://github.com/aws/aws-cdk/issues/1575
- prefix paths with /clue/ or something so that other routes can do non dynamo related things


# v3 design

- cron Lambda function will:
    - query and retrieve latest crossword clues and answers
    - add them to dynamodb
    - create new s3 files from template
        - check if file already exists, if yes, update and invalidate cache using boto3

- if need to redesign website, can update all files using dynamo, save them to new file name (index2.html), and update the cloudfront function on viewer event to redirect to the appropriate file name.
    - can save the new file name of version as an ssm parameter and reference it if needed


TODO:
- don't need to read from dynamo when creating clue page. can just read the s3 object to see if answers are already in the green box
- can add some kind of table or s3 object when a given day has already been processed. so the code doesn't have to recreate all the objects
- need to make invalidations programmatic
- CLEAN UP CODE :D 