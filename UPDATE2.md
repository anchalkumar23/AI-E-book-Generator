The current application can already generate books using the integrated LLM.

Do NOT rewrite the project.

Do NOT change the existing architecture.

Continue building on the existing web application.

Implement the following improvements:

1. Real-time Book Generation

Replace the current "wait until finished" generation flow with real-time streaming.

The user should be able to watch the book being generated live.

The generation process should stream:

- Creating outline
- Writing chapters
- Writing pages
- Creating illustration prompts
- Finalizing the book

Each completed section should immediately appear in the UI instead of waiting for the full book to finish.

2. WebSocket Support

Implement WebSockets for real-time communication between the frontend and backend.

The frontend should receive live updates while the book is being generated.

Display:

- Current stage
- Current chapter
- Current page
- Overall progress percentage
- Current status message

The UI should update instantly without refreshing.

3. Streaming Reader

As pages are generated they should automatically appear inside the book reader.

The user should be able to begin reading before the entire book has finished generating.

The book should continue growing in real time until generation is complete.

4. Writing Style Selection

Allow users to choose a writing style before generating a book.

Include:

- Expository
- Descriptive
- Narrative
- Persuasive

The selected writing style should influence the entire generated book consistently.

5. Improved Prompt Experience

Redesign the home screen.

Place the application logo at the top center.

Place the application name directly below the logo.

Place the main prompt input in the center of the page.

Place the Generate Book button directly below the prompt.

The experience should feel similar to modern AI chat applications.

6. Generation Progress

Replace generic loading indicators with detailed progress.

Examples:

Creating outline...

Writing Chapter 1...

Writing Page 4...

Generating illustration prompts...

Finalizing book...

Completed.

7. Better Book Generation Pipeline

Generate books using structured steps:

- Generate outline
- Generate chapters
- Generate pages
- Generate illustration prompts
- Assemble final book

Ensure:

- Consistent writing style
- Consistent characters
- Consistent timeline
- Consistent tone

8. Illustration Prompt Preparation

Continue generating detailed illustration prompts for every page.

Each illustration prompt should include:

- Scene
- Characters
- Environment
- Mood
- Lighting
- Composition
- Illustration style

Store these prompts for future image generation.

The goal is to make book generation feel live, interactive, and responsive while keeping the current web application architecture intact.