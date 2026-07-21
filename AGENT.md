Build an AI-powered SaaS web application that allows users to generate fully illustrated ebooks on any topic.

The application should allow users to:

• Sign in using Google or normally.
• Create their own personal library of generated books.
• Browse, search, and favorite books within their library.
• Generate unlimited ebooks using AI.
• Generate books of different lengths (children's books, guides, tutorials, educational books, etc.).
• Export books as PDF or word.
• Export books as EPUB.
• Read books in an interactive HTML5 flipbook with realistic page-flipping animations.
• Save and reopen previously generated books.
• Continue editing previously generated books.

The AI should:

• Generate the complete book structure.
• Generate chapters and pages.
• Generate page-by-page illustrations.
• Keep a consistent writing style throughout the book.
• Keep a consistent illustration style throughout the book.
• Produce structured output that separates book content from presentation.
• The writing style will be based on the type of book we want (children's books, guides, tutorials, educational books, etc.)

Image generation requirements:

• Every page should contain an illustration whenever appropriate.
• The illustration style should remain visually consistent across the entire book.
• If a page requires an identifiable real person (celebrity, politician, athlete, influencer, or copyrighted photograph/reference), do not generate an image. Instead, display:
  "Real person image required. Please provide a licensed image or add it manually."

Research requirements:

• The AI should be able to perform live web research whenever factual information is required.
• The research should retrieve current information before writing the content.
• The generated book should incorporate the retrieved information naturally.

Reading experience:

• Support an interactive HTML5 book reader with realistic page-flipping animations (see c8b14100-b0cf-11ea-9d13-fc41ec605dfd.jpeg).
• Each page should display both text and illustration.
• Layout should remain clean, readable, and responsive.

User library:

• Every generated book should automatically be saved.
• Users should be able to organize books.
• Users should be able to mark books as favorites.
• Users should be able to delete books.
• Users should be able to download books at any time.

Payments:

• Users should be able to purchase generation credits.
• Credits should be consumed whenever a new book is generated.
• Users should be able to view remaining credits.
• Support one-time credit purchases.

AI Models:

• Use Ollama as the primary local LLM.
• Use Groq as the cloud inference provider when needed.
• Prefer free/open-source models whenever possible.
• The user will upload and save the api key.

Web Search:

• Use DuckDuckGo for web search and information retrieval (use it everytime).

General requirements:

• The application should feel modern, polished, and easy to use.
• The generated books should look professional.
• The application should be scalable for future features.
• Content generation should be separated from rendering so the same book can be exported into multiple formats without regenerating content.
• Keep the entire user experience simple and intuitive.

The goal is to build an AI Ebook Generator platform where users can generate high-quality illustrated ebooks, maintain a personal digital library, read books interactively, and export them into multiple formats.