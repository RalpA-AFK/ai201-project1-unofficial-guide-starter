"""The 10 document sources for the skateboarding corpus.

Single source of truth for ingestion. Each entry's ``slug`` becomes the
saved filename in ``documents/`` and the key used for source attribution
later in the pipeline (Milestone 5).
"""

SOURCES = [
    {
        "id": 1,
        "slug": "01-skateboardgeek-tricks",
        "name": "SkateboardGeek — Skateboarding Tricks Guide",
        "url": "https://skateboardgeek.com/skateboarding-tricks/",
    },
    {
        "id": 2,
        "slug": "02-skateboardgb-learn-to-skate",
        "name": "Skateboard GB — Learn to Skate Guide",
        "url": "https://skateboardgb.org/beginners/learn-to-skate-guide/",
    },
    {
        "id": 3,
        "slug": "03-skateboardsession-griptape",
        "name": "Skateboard Session — Grip Tape Maintenance & Cleaning",
        "url": "https://skateboardsession.com/maintenance-repairs/skateboard-grip-tape-maintenance/",
    },
    {
        "id": 4,
        "slug": "04-surfertoday-beginners-guide",
        "name": "Surfertoday — Beginner's Guide to Skateboarding",
        "url": "https://www.surfertoday.com/skateboarding/the-beginners-guide-to-skateboarding",
    },
    {
        "id": 5,
        "slug": "05-surfertoday-thrasher",
        "name": "Surfertoday — The Story of Thrasher",
        "url": "https://www.surfertoday.com/skateboarding/thrasher-the-story-of-the-ultimate-skateboard-magazine",
    },
    {
        "id": 6,
        "slug": "06-skateboardsession-etiquette",
        "name": "Skateboard Session — Skatepark Etiquette",
        "url": "https://skateboardsession.com/culture-and-community/skate-park-etiquette/",
    },
    {
        "id": 7,
        "slug": "07-skateavenue-size-guide",
        "name": "Skate Avenue — Skateboard Size Guide",
        "url": "https://skate-avenue.com/blogs/articles/skateboard-size-guide",
    },
    {
        "id": 8,
        "slug": "08-tactics-safety",
        "name": "Tactics — Skateboarding Safety & Gear Guide",
        "url": "https://www.tactics.com/info/skateboarding-safety-gear-guide",
    },
    {
        "id": 9,
        "slug": "09-tactics-kickflip",
        "name": "Tactics — How to Kickflip",
        "url": "https://www.tactics.com/info/how-to-kickflip",
    },
    {
        "id": 10,
        "slug": "10-retrospec-beginner-steps",
        "name": "Retrospec — How to Skateboard: 5 Steps for Beginners",
        "url": "https://retrospec.com/blogs/gear-guides/how-to-skateboard-5-steps-for-beginners",
    },
]