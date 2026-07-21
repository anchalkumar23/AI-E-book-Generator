The current project is functional and already includes:

- AI book generation using Ollama
- Chat interface
- WebSocket streaming
- Book generation pipeline
- SQLite database
- PDF/EPUB export
- Library system

Do NOT rebuild the project from scratch.

Migrate the existing application to the new architecture while preserving as much code as possible.

## New Architecture

Execution:
- Tauri

Frontend:
- React + TypeScript

Backend:
- Rust (Tauri Commands)

Local AI:
- Ollama/groq API (for me the test fast)

Database:
- SQLite

Knowledge Base:
- Local ZIM files

The application should become a cross-platform desktop application for Windows and macOS.

Do NOT use Electron.

Do NOT use a Python backend.

Do NOT use any cloud backend.

Everything should run locally.

--------------------------------------------------

## Main Application

The application should feel like ChatGPT or Gemini.

The home page should contain:

- Application logo
- Application title
- Centered prompt input
- Generate button

The conversation should continue as a live AI chat.

The user enters:

"Write a 15 page book about Ancient Rome."

The AI immediately starts responding inside the chat showing real time chat and image generated just like chatgpt does.

--------------------------------------------------

## Live Generation

Use WebSockets (or Tauri's event system if more appropriate) so generation appears in real time.

The user should see:

Creating outline...

Writing chapter 1...

Writing chapter 2...

Writing page 1...

Writing page 2...

Creating illustration prompts...

Finalizing book...

Everything should stream progressively.

Never wait until the entire generation has finished before showing content.

--------------------------------------------------

## Book Generation

The AI should internally generate:

- Outline
- Chapters
- Pages
- Illustration prompts

The generation pipeline should maintain:

- Character consistency
- Timeline consistency
- Writing style consistency
- Topic consistency

--------------------------------------------------

## Writing Styles

Allow the user to choose:

- Expository
- Narrative
- Descriptive
- Persuasive

The selected style should influence the complete generation.

--------------------------------------------------

## Knowledge

Integrate local knowledge support.

The application should be capable of reading locally stored ZIM knowledge files.

Use these files as an offline knowledge source whenever additional factual information is required.

Do not depend on cloud APIs.

--------------------------------------------------

## Local Storage

Everything should remain local.

Store:

- Books
- Chat history
- Generated content
- User preferences

inside SQLite.

--------------------------------------------------

## Export

After generation finishes,

allow exporting to:

- PDF
- EPUB

Leave placeholders for future video export.

--------------------------------------------------

## Images

For now,

continue generating detailed illustration prompts only.

Each illustration prompt should contain:

- Scene
- Characters
- Environment
- Lighting
- Mood
- Composition
- Style

Do NOT implement image generation yet.

Design the architecture so image generation can easily be added later.

--------------------------------------------------

## Performance

The application should:

- Launch quickly
- Feel responsive
- Stream generation in real time
- Avoid blocking the UI
- Support long book generation

--------------------------------------------------

## Code Quality

Refactor where necessary.

Remove obsolete code.

Reuse existing business logic whenever possible.

Keep the code modular.

Separate:

- UI
- AI generation
- Database
- Export
- Knowledge retrieval
- Streaming

--------------------------------------------------

## Goal

The final product should be a modern offline-first AI desktop application capable of generating complete books through a live chat interface while running entirely on the user's machine.