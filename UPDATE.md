The current application is working and can already generate books using the integrated LLM.

Continue building on the existing web application.

Implement the following improvements:

1. Improve the AI book generation pipeline.
- Generate a complete book outline first.
- Generate chapters based on the outline.
- Generate page-by-page content.
- Keep the writing style and tone consistent throughout the book.
- Ensure the final book has the requested number of pages.

2. Add structured generation.
Create structured objects internally for:
- Book Blueprint
- Chapter
- Page
- Illustration Prompt

The book should be generated using these structured objects instead of generating one large block of text.

3. Add optional Internet Research.

Add a toggle called:

Internet Research

When OFF:
- Generate the book only using the LLM's knowledge.

When ON:
- Use DuckDuckGo search to retrieve relevant information before writing the book.
- Use the retrieved information as additional context.
- Keep citations internally for future use.
- Add more web search tools for more research like wikepedia, trivile. 

4. Improve prompt quality.

Generate a detailed illustration prompt for every page.

The illustration prompt should contain:
- Scene description
- Characters
- Environment
- Mood
- Lighting
- Composition
- Illustration style

5. Improve book consistency.

Maintain:
- Character consistency
- Writing style consistency
- Visual style consistency
- Timeline consistency

throughout the entire book.

6. Add generation progress.

Display progress such as:
- Creating outline
- Writing chapters
- Generating pages
- Creating illustration prompts
- Finalizing book

instead of a generic loading indicator.

7. Improve the database schema.

Each book should contain:
- Metadata
- Outline
- Chapters
- Pages
- Illustration prompts
- Generation status
- Generation progress
- Creation date
- Last modified date

The goal is to improve the intelligence, structure, and reliability of book generation while keeping the existing web application architecture intact.