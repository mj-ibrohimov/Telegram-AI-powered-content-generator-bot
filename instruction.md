Yes. I would build this as a **human-in-the-loop Telegram content system**, rather than allowing AI to publish automatically. The bot generates, you review, and only your approval can publish.

Below is a prompt you can paste directly into your cloud coding agent (Cursor, Claude Code, Codex, etc.). I’ve made it detailed enough that the coding agent should be able to implement the project rather than just give you a high-level explanation.

# Build a Production-Ready AI Telegram Content Bot for a German-Learning Channel

## 1. ROLE

You are a senior Python backend engineer and Telegram Bot API developer.

Build a production-ready Telegram bot that manages content generation and publishing for a German-language learning Telegram channel.

The system must be designed for a channel owner who wants to:

1. Automatically generate educational German-learning content several times per day.
2. Receive every generated post privately in Telegram.
3. Review the generated post.
4. Approve it and publish it immediately to the channel.
5. Discard it and generate another post.
6. Ask the AI to improve/rewrite it using natural-language instructions.
7. Keep a history of generated and published content.
8. Avoid repetitive content.
9. Eventually use the channel to attract students to paid online German classes.

The owner must remain in complete control of publication. **The AI must NEVER publish a post without explicit owner approval.**

---

# 2. CORE TECHNOLOGY

Use this stack unless there is a strong technical reason to change it:

- Python 3.12+
- aiogram 3.x for Telegram Bot API
- PostgreSQL for production
- SQLite as an optional local-development database
- SQLAlchemy 2.x
- APScheduler for scheduled generation
- Pydantic / pydantic-settings for configuration
- An LLM provider abstraction, initially supporting OpenAI-compatible APIs
- httpx for HTTP requests
- Docker + Docker Compose
- pytest for testing
- python-dotenv for local development
- structured logging

Design the application so the LLM provider can later be changed without rewriting the bot.

For example:

```text
LLMProvider
    ├── OpenAIProvider
    ├── AnthropicProvider (future)
    └── OtherProvider (future)
```

---

# 3. TIMEZONE AND SCHEDULE

The owner is located in Uzbekistan.

Use:

```text
Asia/Tashkent
```

as the default timezone.

Generate posts every day at:

```text
08:00
12:00
16:00
20:00
22:00
```

The times must be configurable through environment variables or application configuration.

Default:

```env
TIMEZONE=Asia/Tashkent
POST_TIMES=08:00,12:00,16:00,20:00,22:00
```

The scheduler must correctly handle timezone-aware datetimes.

Do not rely on server local time.

---

# 4. TELEGRAM ARCHITECTURE

There will be:

### A. Telegram channel

The bot is added as an administrator of the channel.

The bot requires permission to:

- Post messages
- Edit messages if necessary
- Delete messages if necessary

The exact minimum permissions should be documented.

### B. Channel owner/admin

The owner communicates with the bot in a private Telegram chat.

Only authorized Telegram user IDs may control the bot.

Example:

```env
ADMIN_TELEGRAM_IDS=123456789
```

Support multiple administrators if possible.

Unauthorized users must not be able to:

- Generate posts
- Approve posts
- Publish posts
- Change settings
- Access administrative commands

---

# 5. MAIN WORKFLOW

The central workflow is:

```text
Scheduler
   ↓
Generate content
   ↓
Validate content
   ↓
Send draft to owner
   ↓
Owner reviews
   ↓
 ┌───────────────┬────────────────┬──────────────────┐
 │               │                │
Approve        Discard          Improve
 │               │                │
 ↓               ↓                ↓
Publish      Generate new     Ask for instructions
to channel       draft              ↓
 │               │             AI improves draft
 ↓               │                  ↓
Done             └────────────→ Owner reviews again
```

---

# 6. DRAFT APPROVAL MESSAGE

When a draft is generated, send it privately to the owner.

The message should clearly indicate that it is a draft.

Example:

```text
📝 NEW GERMAN LEARNING POST

Scheduled slot:
20:00

Category:
Workplace German

━━━━━━━━━━━━━━━━━━

🇩🇪 Useful German phrases for the workplace

...

━━━━━━━━━━━━━━━━━━

Status:
Waiting for approval
```

Below the message use Telegram inline buttons:

```text
[ ✅ Approve & Publish ]

[ ✏️ Improve ]

[ ❌ Discard & Regenerate ]
```

Use callback queries rather than text commands whenever possible.

---

# 7. APPROVE WORKFLOW

When owner presses:

```text
✅ Approve & Publish
```

the bot must:

1. Verify that the user is authorized.
2. Verify that the draft still exists.
3. Verify that the draft has not already been published.
4. Publish the content to the configured Telegram channel.
5. Store the Telegram message ID.
6. Change draft status to `PUBLISHED`.
7. Record publication timestamp.
8. Update the owner message to indicate successful publication.

Example:

```text
✅ PUBLISHED

The post has been published to the channel.

Published at:
20:03
```

Prevent double publication if the owner presses the button multiple times.

---

# 8. DISCARD WORKFLOW

When owner presses:

```text
❌ Discard & Regenerate
```

do NOT simply delete the draft from the database.

Instead:

1. Mark the current draft as `DISCARDED`.
2. Record the reason as `owner_discarded`.
3. Generate a new post.
4. Use the discarded content as negative context so the AI does not simply reproduce it.
5. Send the new draft to the owner.
6. Create a new draft ID.

Example:

```text
❌ Previous draft discarded.

🔄 Generating a new idea...
```

Then send the new draft.

---

# 9. IMPROVE WORKFLOW

When owner presses:

```text
✏️ Improve
```

the bot should enter an improvement state.

Reply:

```text
✏️ What would you like me to improve?

For example:

• Make it shorter
• Make it more interesting
• Add a quiz
• Make the German easier
• Add Uzbek explanations
• Make it suitable for A2 learners
• Add emojis
• Make it more professional
• Change the topic
• Make the CTA less promotional
```

The owner then sends natural-language instructions.

Example:

```text
Make it more suitable for A2 learners and add a small exercise.
```

The AI should then rewrite the post while preserving the useful parts.

Send the improved version as a new review message with the same approval controls:

```text
[ ✅ Approve & Publish ]

[ ✏️ Improve ]

[ ❌ Discard & Regenerate ]
```

Maintain the revision history.

---

# 10. CONTENT STRATEGY

The channel is for people who want to learn German.

The content should be genuinely useful and interesting rather than consisting primarily of advertising.

The long-term business goal is:

```text
Useful content
     ↓
Audience trust
     ↓
Channel growth
     ↓
Interest in German learning
     ↓
Potential students
     ↓
Online German classes
```

Do NOT make every post promotional.

The content engine should prioritize value.

---

# 11. CONTENT CATEGORIES

Implement a configurable content category system.

Suggested categories:

### 1. Daily German

Useful everyday phrases.

Example:

```text
🇩🇪 5 German phrases you can use today

1. Wie geht's?
2. Das klingt gut.
3. Kein Problem.
4. Ich bin gleich da.
5. Bis später!
```

Include Uzbek explanations when useful.

---

### 2. German Vocabulary

Vocabulary grouped by topic.

Examples:

- Travel
- Food
- Work
- University
- Shopping
- Healthcare
- Housing
- Relationships
- Daily life
- Bureaucracy

---

### 3. Workplace German

Examples:

- Office vocabulary
- Job interviews
- Emails
- Meetings
- Presentations
- Talking to colleagues
- Talking to managers
- Professional phrases

Example:

```text
💼 Deutsch im Büro

"Ich wollte kurz nachfragen..."

Meaning:
I just wanted to ask/follow up...

Useful when writing a polite professional message.
```

---

### 4. Grammar

Short explanations.

Examples:

- Akkusativ vs Dativ
- der/die/das
- Perfekt
- Präteritum
- Konjunktiv II
- weil/dass
- word order
- separable verbs
- modal verbs

Avoid overly academic explanations.

---

### 5. German Mistakes

Common mistakes made by German learners.

Format:

```text
❌ Ich habe gegangen.

✅ Ich bin gegangen.

Warum?

"gehen" uses "sein" in Perfekt.
```

---

### 6. German vs Uzbek / Russian / English

Where appropriate, explain differences between German and languages commonly spoken by the target audience.

The main explanatory language should be Uzbek when appropriate.

Do not invent linguistic similarities.

---

### 7. Quiz

Create interactive-style posts.

Example:

```text
🧠 Mini German Quiz

Which sentence is correct?

A) Ich bin 25 Jahre alt.
B) Ich habe 25 Jahre.
C) Ich bin habe 25 Jahre.

Write your answer below 👇

Answer:
A
```

---

### 8. Interesting Germany Facts

Interesting cultural and practical information about Germany.

Examples:

- German traditions
- Public transport
- Education
- Work culture
- Food
- Geography
- Cities
- German expressions
- Everyday German culture

Avoid stereotypes.

Facts should be verified when factual accuracy matters.

---

### 9. German News

Potentially include current German news.

When generating news:

- Use a web/news retrieval component.
- Prefer reputable sources.
- Include the date.
- Clearly distinguish fact from commentary.
- Include the original source.
- Summarize rather than copying articles.
- Provide a short German section.
- Provide Uzbek explanation/translation when useful.
- Do not fabricate news.

Example:

```text
🇩🇪 HEUTE AUF DEUTSCH

[German headline]

🇺🇿 Qisqacha:
[Uzbek explanation]

📚 Useful vocabulary:

die Entscheidung — qaror
die Regierung — hukumat
...
```

The system should be able to disable news generation if no reliable source is available.

---

### 10. German Media Recommendations

Recommend:

- Books
- YouTube channels
- Podcasts
- Movies
- Series
- Websites
- Audio resources

Whenever recommending external resources, prefer legitimate/free/legal sources.

Do not distribute copyrighted books, movies, or audio illegally.

For copyrighted materials, link to legitimate sources instead.

---

### 11. Learning Challenges

Examples:

```text
🔥 7-Day German Challenge

Day 1:

Learn these 5 verbs:

...
```

---

### 12. German for Migration / Life in Germany

Useful practical German for:

- Anmeldung
- renting apartments
- doctors
- banks
- work
- bureaucracy
- transportation
- interviews

Make clear that informational posts are not legal advice when relevant.

---

### 13. Soft Marketing

Occasionally mention the owner's German classes.

For example:

```text
📚 Want to practice German with a teacher?

If you're looking for structured lessons and personal feedback, our online German classes are available.

Write to us: @...
```

Marketing frequency must be configurable.

For example:

```env
PROMOTIONAL_POST_RATIO=0.10
```

Meaning approximately 10% of posts may contain promotional content.

Never make the channel feel like a constant advertisement.

---

# 12. LANGUAGE STRATEGY

The primary educational language is German.

Use Uzbek for explanations when useful.

A post can contain:

```text
German
+
Uzbek explanation
+
Example
+
Exercise
```

Do not translate everything automatically.

The purpose is to help users learn German.

Adjust language difficulty according to the target CEFR level.

Support:

```text
A1
A2
B1
B2
C1
C2
Mixed
```

Default:

```text
Mixed
```

The bot should avoid creating C1/C2 vocabulary-heavy posts repeatedly.

---

# 13. CONTENT QUALITY RULES

Every generated post should pass an internal quality checklist.

The AI should verify:

### Accuracy

- German grammar must be correct.
- Vocabulary meanings must be correct.
- Uzbek translations must be natural.
- Facts must not be invented.

### Educational value

The reader should learn something.

### Readability

Use:

- short paragraphs
- bullets
- emojis where appropriate
- examples
- clear formatting

### Engagement

Where appropriate include:

- questions
- quizzes
- challenges
- examples
- practical scenarios

### Non-repetition

Do not repeatedly publish the same:

- vocabulary
- phrases
- examples
- topics
- jokes
- facts
- exercises

### Marketing balance

Avoid excessive promotion.

---

# 14. AI CONTENT GENERATION PROMPT

Create a system prompt similar to:

```text
You are an expert German teacher and educational content creator.

Your job is to create useful, accurate, engaging Telegram posts for Uzbek-speaking people learning German.

The content should help learners improve their German while making the Telegram channel worth following.

Prioritize educational value over marketing.

Use natural German.

When Uzbek explanations are useful, provide clear and natural Uzbek.

Adapt content to the requested CEFR level.

Avoid repetitive content.

Do not invent facts, news, books, resources, statistics, quotations, or sources.

If current information is requested, rely on retrieved sources rather than memory.

Create content that is easy to read on Telegram.

Use emojis moderately.

Do not make every post promotional.

Do not publish anything yourself.

You are generating a draft that must be reviewed and approved by the channel owner.
```

---

# 15. CONTEXT GIVEN TO AI

Every generation request should provide the AI with structured context.

For example:

```json
{
  "scheduled_time": "20:00",
  "timezone": "Asia/Tashkent",
  "category": "workplace_german",
  "cefr_level": "A2-B1",
  "language": "German + Uzbek",
  "recent_posts": [],
  "discarded_posts": [],
  "recent_categories": [],
  "marketing_ratio": 0.10
}
```

Use recent content to prevent repetition.

Do not send the entire database history to the LLM.

Retrieve only relevant recent content and summaries.

---

# 16. CONTENT ROTATION

Implement category rotation.

For example, avoid:

```text
08:00 vocabulary
12:00 vocabulary
16:00 vocabulary
20:00 vocabulary
22:00 vocabulary
```

Instead rotate:

```text
08:00 Daily German
12:00 Grammar
16:00 Workplace German
20:00 Quiz
22:00 Germany/Culture
```

But the exact category should be dynamically selected.

Store category usage history.

Use configurable weights.

Example:

```text
daily_phrases: 20
vocabulary: 15
grammar: 15
workplace: 10
quiz: 10
culture: 10
news: 5
media: 5
mistakes: 10
challenge: 5
marketing: 5
```

These weights should be configurable.

---

# 17. DATABASE

Use SQLAlchemy.

Create at least these tables.

## admins

```text
id
telegram_user_id
username
is_active
created_at
updated_at
```

## drafts

```text
id
scheduled_for
category
cefr_level
title
content
status
generation_attempt
created_at
updated_at
published_at
telegram_message_id
```

Statuses:

```text
GENERATED
WAITING_APPROVAL
IMPROVING
DISCARDED
PUBLISHED
FAILED
```

## revisions

```text
id
draft_id
version
content
instruction
created_at
```

## publications

```text
id
draft_id
channel_id
telegram_message_id
published_at
```

## content\_history

Track published and discarded content for duplicate prevention.

Fields may include:

```text
id
draft_id
category
topic
summary
keywords
created_at
```

## scheduler\_runs

Track scheduler execution:

```text
id
scheduled_for
started_at
completed_at
status
error_message
draft_id
```

---

# 18. DUPLICATE DETECTION

Implement multiple levels of duplicate detection.

### Exact duplicate

Compare normalized text.

### Similar duplicate

Use a lightweight similarity mechanism.

For MVP, TF-IDF/cosine similarity or another simple local similarity approach is acceptable.

Later this can be replaced with embeddings.

Reject or regenerate if similarity exceeds a configurable threshold.

Example:

```env
DUPLICATE_SIMILARITY_THRESHOLD=0.80
```

---

# 19. BOT COMMANDS

Implement at least:

```text
/start
/help
/status
/generate
/schedule
/history
/settings
```

### /start

Explain that the bot is an AI content assistant.

### /status

Show:

```text
Bot: Online
Scheduler: Running
Next generation: 20:00
Channel: Connected
Database: Connected
```

### /generate

Manually generate a draft.

### /schedule

Show today's scheduled times.

### /history

Show recent published posts.

### /settings

Allow owner to inspect configuration.

---

# 20. INLINE BUTTONS

Implement callback buttons such as:

```text
approve:{draft_id}
improve:{draft_id}
discard:{draft_id}
```

Use secure callback handling.

Never trust callback data alone.

Always verify:

1. user authorization
2. draft ownership/state
3. current draft status

---

# 21. IMPROVEMENT CONVERSATION STATE

Use FSM/state management from aiogram.

Example:

```text
WAITING_FOR_IMPROVEMENT_INSTRUCTION
```

Store:

```text
admin_id
draft_id
```

When the owner sends the instruction:

```text
Improve this by making the explanation simpler and adding 3 examples.
```

Call the LLM.

Create a new revision.

Send the revised draft.

Reset the FSM.

---

# 22. TELEGRAM FORMATTING

Use Telegram-compatible formatting.

Prefer HTML or MarkdownV2, but implement formatting carefully so special characters do not break messages.

Create a formatting utility.

For example:

```python
format_telegram_post(...)
```

Do not allow malformed markup to reach Telegram.

If Telegram rejects formatting, retry with plain text or sanitized formatting.

---

# 23. LONG POSTS

Telegram has message length limitations.

Implement automatic length validation.

If content is too long:

1. Ask AI to shorten it, or
2. Split it into multiple messages if appropriate.

For normal educational posts, prefer keeping them concise.

Target approximately:

```text
500–1500 characters
```

unless the content type requires more.

---

# 24. ERROR HANDLING

Implement robust error handling.

Handle:

- Telegram API errors
- network failures
- LLM API failures
- rate limits
- database failures
- scheduler failures
- malformed AI output
- invalid Telegram formatting
- duplicate publication
- missing channel permissions

Use retries with exponential backoff where appropriate.

Do not endlessly retry.

---

# 25. IDEMPOTENCY

This is important.

If the application restarts after generation but before recording the result, it must not accidentally generate five duplicate posts.

Every scheduled task should have an idempotency key based on:

```text
date + scheduled_time
```

Example:

```text
2026-09-27_20:00
```

Before executing a scheduled generation, check whether that slot has already been successfully processed.

---

# 26. SECURITY

Never hard-code:

- Telegram bot token
- OpenAI/API keys
- database passwords
- Telegram admin IDs

Use environment variables.

Example:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHANNEL_ID=
ADMIN_TELEGRAM_IDS=
DATABASE_URL=
LLM_API_KEY=
LLM_MODEL=
TIMEZONE=Asia/Tashkent
```

Add:

```text
.env
```

to `.gitignore`.

Provide:

```text
.env.example
```

without real credentials.

---

# 27. OPTIONAL WEB/NEWS PROVIDER

Create an abstraction:

```python
class NewsProvider:
    async def search(self, query: str) -> list[NewsItem]:
        ...
```

Possible implementation:

```text
WebNewsProvider
```

Use it only for content types requiring current information.

News content should include:

```text
source
source_url
publication_date
```

Do not fabricate URLs.

Do not copy entire articles.

Summarize them.

---

# 28. AI PROVIDER ABSTRACTION

Create:

```python
class LLMProvider(ABC):

    async def generate_post(...):
        pass

    async def improve_post(...):
        pass
```

Implement the initial provider.

Keep all provider-specific code isolated.

---

# 29. PROJECT STRUCTURE

Use a clean architecture similar to:

```text
german-telegram-bot/
│
├── app/
│   ├── __init__.py
│   │
│   ├── bot/
│   │   ├── handlers/
│   │   │   ├── start.py
│   │   │   ├── admin.py
│   │   │   ├── drafts.py
│   │   │   └── callbacks.py
│   │   │
│   │   ├── keyboards/
│   │   │   └── approval.py
│   │   │
│   │   ├── states/
│   │   │   └── improvement.py
│   │   │
│   │   └── middleware/
│   │       └── auth.py
│   │
│   ├── ai/
│   │   ├── base.py
│   │   ├── provider.py
│   │   └── prompts.py
│   │
│   ├── content/
│   │   ├── generator.py
│   │   ├── validator.py
│   │   ├── duplicate_detector.py
│   │   └── strategy.py
│   │
│   ├── database/
│   │   ├── models.py
│   │   ├── database.py
│   │   └── repositories/
│   │
│   ├── scheduler/
│   │   └── scheduler.py
│   │
│   ├── news/
│   │   ├── base.py
│   │   └── provider.py
│   │
│   ├── services/
│   │   ├── draft_service.py
│   │   ├── publication_service.py
│   │   └── improvement_service.py
│   │
│   ├── config.py
│   └── main.py
│
├── tests/
│   ├── test_content.py
│   ├── test_duplicates.py
│   ├── test_scheduler.py
│   ├── test_callbacks.py
│   └── test_publication.py
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── alembic.ini
```

Use Alembic migrations.

---

# 30. DEPLOYMENT

The bot must run continuously on a cloud server.

Provide Docker support.

Docker Compose should include:

```text
bot
postgres
```

Example architecture:

```text
                    ┌───────────────┐
                    │   PostgreSQL  │
                    └───────▲───────┘
                            │
                            │
┌─────────────┐      ┌──────┴───────┐
│ Telegram    │◄────►│ Python Bot   │
│             │      │              │
└─────────────┘      │ Scheduler    │
                     │ AI Service   │
                     │ Content      │
                     └──────┬───────┘
                            │
                            ▼
                       LLM Provider
```

The README must explain deployment step-by-step.

---

# 31. LOGGING

Use structured logging.

Every important operation should log:

```text
generation started
generation completed
draft created
draft improved
draft discarded
publication attempted
publication successful
publication failed
scheduler started
scheduler failed
```

Never log secrets or API tokens.

---

# 32. OBSERVABILITY

Implement a simple `/status` endpoint or health-check mechanism.

For example:

```text
GET /health
```

Return:

```json
{
  "status": "ok",
  "database": "ok",
  "scheduler": "running"
}
```

This is useful for cloud hosting and monitoring.

---

# 33. CONTENT GENERATION ALGORITHM

At each scheduled time:

```python
async def generate_scheduled_post():
    slot = get_current_schedule_slot()

    if already_processed(slot):
        return

    category = content_strategy.select_category()

    context = content_history.get_recent_context(
        category=category
    )

    draft = await llm.generate_post(
        category=category,
        context=context
    )

    validation_result = validate(draft)

    if not validation_result.valid:
        regenerate()

    if is_duplicate(draft):
        regenerate()

    save_draft(draft)

    send_to_admin(draft)

    mark_scheduler_run_success()
```

---

# 34. REGENERATION LIMIT

Never enter an infinite generation loop.

Example:

```env
MAX_GENERATION_ATTEMPTS=3
```

If all attempts fail:

```text
⚠️ I couldn't generate a valid post for the 20:00 slot.

You can use /generate to try manually.
```

Log the error.

---

# 35. MANUAL GENERATION

When owner sends:

```text
/generate
```

the bot should allow optional parameters.

For example:

```text
/generate
```

or:

```text
/generate workplace
```

or:

```text
/generate A2 grammar
```

or:

```text
/generate quiz
```

Parse the request and pass it to the content strategy system.

---

# 36. OWNER EXPERIENCE

The owner should not need to interact with the command line after deployment.

Normal workflow should happen entirely inside Telegram.

Example:

### 20:00

Bot:

```text
📝 New draft

🇩🇪 5 useful German phrases for work...

[✅ Approve & Publish]
[✏️ Improve]
[❌ Discard & Regenerate]
```

Owner:

```text
✏️ Improve
```

Bot:

```text
What should I change?
```

Owner:

```text
Make it more useful for people preparing for a job interview.
```

Bot:

```text
✨ Revised draft

💼 Deutsch für Vorstellungsgespräche

...

[✅ Approve & Publish]
[✏️ Improve]
[❌ Discard & Regenerate]
```

Owner:

```text
✅ Approve & Publish
```

Bot:

```text
✅ Published successfully.
```

---

# 37. CONTENT PERSONALITY

The channel should feel:

- friendly
- useful
- motivating
- practical
- modern
- educational
- trustworthy

Avoid:

- excessive emojis
- clickbait
- fake urgency
- repetitive motivational quotes
- low-quality AI filler
- overly formal textbook language
- excessive advertising
- fabricated facts

---

# 38. FUTURE EXTENSIONS

Design the code so these can be added later:

### Subscriber analytics

Track:

- views
- reactions
- forwards
- comments

### Best-performing content

Identify which categories perform best.

### Automatic content optimization

Use historical performance to adjust category weights.

### Image generation

Generate illustrations for selected posts.

### Vocabulary cards

Automatically create:

```text
German word
Uzbek meaning
Example sentence
Plural
Article
```

### Audio

Generate German pronunciation/audio.

### Courses

Eventually promote structured courses.

### Lead generation

Allow users to contact the teacher.

### CRM

Potential future integration with:

- Google Sheets
- Airtable
- CRM
- Telegram forms

Do not implement these unless explicitly requested, but keep the architecture extensible.

---

# 39. TESTING REQUIREMENTS

Write unit and integration tests.

At minimum test:

### Authentication

Unauthorized users cannot control the bot.

### Approval

Approved draft publishes exactly once.

### Discard

Discard changes status and creates a new draft.

### Improvement

Improvement instruction reaches the AI provider and creates a new revision.

### Duplicate protection

Similar posts are detected.

### Scheduler

Correct timezone and scheduled times are used.

### Restart

Restarting the application does not duplicate a scheduled job.

### Telegram failures

Telegram API failures are handled safely.

### LLM failures

LLM failures are retried and handled.

### Database

Transactions do not leave drafts in inconsistent states.

---

# 40. README REQUIREMENTS

The README must explain:

1. What the bot does.
2. How to create a Telegram bot using BotFather.
3. How to add the bot to the channel.
4. Which admin permissions are required.
5. How to find the channel ID.
6. How to find the owner's Telegram user ID.
7. How to configure `.env`.
8. How to run locally.
9. How to run with Docker.
10. How to run PostgreSQL.
11. How scheduling works.
12. How to test generation.
13. How to deploy to a cloud server.
14. How to troubleshoot common errors.

---

# 41. BOTFATHER SETUP DOCUMENTATION

Include instructions such as:

```text
1. Open Telegram.
2. Open @BotFather.
3. Create a new bot.
4. Copy the bot token.
5. Add the bot to the Telegram channel.
6. Promote it to administrator.
7. Give it permission to post messages.
8. Configure TELEGRAM_CHANNEL_ID.
9. Configure ADMIN_TELEGRAM_IDS.
```

Never ask the user to put their bot token directly into source code.

---

# 42. ACCEPTANCE CRITERIA

The project is considered complete only when all of the following work:

### Scheduling

At:

```text
08:00
12:00
16:00
20:00
22:00
```

a generation job is triggered.

### Generation

A useful German-learning draft is generated.

### Review

The owner receives the draft privately.

### Approval

Pressing:

```text
Approve & Publish
```

publishes the draft to the configured channel.

### Discard

Pressing:

```text
Discard & Regenerate
```

generates another draft.

### Improve

Pressing:

```text
Improve
```

allows the owner to give instructions.

The AI then produces an improved draft.

### Security

Only configured administrators can perform these actions.

### Persistence

Drafts and publication history survive application restarts.

### Duplicate prevention

The system does not repeatedly generate nearly identical content.

### Reliability

Temporary Telegram/API failures do not crash the entire application.

---

# 43. IMPLEMENTATION PROCESS

Do not simply generate a theoretical architecture.

Actually implement the project.

Work in this order:

1. Initialize project.
2. Configure Python environment.
3. Implement configuration.
4. Implement database models.
5. Implement migrations.
6. Implement Telegram bot.
7. Implement authentication middleware.
8. Implement inline keyboards.
9. Implement draft lifecycle.
10. Implement AI provider.
11. Implement content strategy.
12. Implement duplicate detection.
13. Implement scheduler.
14. Implement publication.
15. Implement improvement FSM.
16. Implement error handling.
17. Implement logging.
18. Implement health checks.
19. Write tests.
20. Write Docker configuration.
21. Write README.
22. Run tests.
23. Fix errors.
24. Verify the complete workflow.

Do not stop after creating the architecture.

---

# 44. IMPORTANT IMPLEMENTATION PRINCIPLE

The system should be designed around this state machine:

```text
                ┌─────────────┐
                │  GENERATED  │
                └──────┬──────┘
                       │
                       ▼
              ┌─────────────────┐
              │ WAITING_APPROVAL│
              └───┬─────┬────┬──┘
                  │     │    │
             approve  improve discard
                  │     │    │
                  ▼     ▼    ▼
             PUBLISHED  │  DISCARDED
                        │
                        ▼
                  IMPROVED DRAFT
                        │
                        ▼
                WAITING_APPROVAL
```

Every state transition must be explicit and persisted.

Never rely only on in-memory state.

---

# 45. FINAL DELIVERABLE

At the end, provide:

1. Complete source code.
2. Database models.
3. Alembic migrations.
4. AI prompts.
5. Telegram handlers.
6. Scheduler.
7. Content strategy.
8. Duplicate detection.
9. Tests.
10. Docker configuration.
11. `.env.example`.
12. README.
13. Example generated posts.
14. Instructions for connecting the bot to the Telegram channel.
15. Instructions for deploying it to the cloud.

Before declaring the project complete, run the test suite and fix all errors.

The final application should be maintainable by a Python developer and should not depend on manual intervention outside Telegram for normal daily operation.

### One important improvement I'd make

I would **not** initially make the AI responsible for generating completely random content five times a day. The content engine should have a **content calendar + history + category rotation**.

For example:

| Time | Typical content |
|---|---|
| 08:00 | 🇩🇪 Daily phrase / vocabulary |
| 12:00 | 📚 Grammar / common mistakes |
| 16:00 | 💼 Workplace German |
| 20:00 | 🧠 Quiz / interactive exercise |
| 22:00 | 🇩🇪 Germany / culture / news / media |

The AI can still choose the exact topic dynamically. This gives the channel a recognizable rhythm while preventing it from becoming repetitive.

Also, I would keep **news as a separate AI workflow** from evergreen educational content. Current news needs source retrieval and fact checking; phrases, vocabulary, grammar, quizzes, etc. don't need live web access.