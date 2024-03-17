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