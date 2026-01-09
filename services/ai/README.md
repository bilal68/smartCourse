# AI Service

AI-powered features for course content generation, recommendations, and intelligent assistance.

## Features (Planned)

- 🤖 **AI Chat Assistant** - Help students with course questions
- 📝 **Content Generation** - Generate quizzes, summaries, and explanations
- 💡 **Course Recommendations** - Personalized course suggestions
- 🎯 **Difficulty Analysis** - Analyze course difficulty level
- 🔍 **Content Embeddings** - Vector embeddings for semantic search

## Architecture

```
app/
├── main.py              # FastAPI application
├── celery_app.py        # Celery configuration
├── modules/
│   ├── chat/           # AI chat functionality
│   ├── generation/     # Content generation
│   ├── recommendations/ # Course recommendations
│   └── embeddings/     # Vector embeddings
├── core/               # Core utilities
├── db/                 # Database layer
└── integrations/
    ├── openai/         # OpenAI integration
    ├── kafka/          # Kafka consumer
    └── vectordb/       # Vector database (Pinecone/Weaviate)
```

## Events Consumed

- `course.published` → Generate course embeddings
- `enrollment.created` → Generate recommendations
- `asset.completed` → Update user profile for recommendations

## Events Published

- `quiz.generated` - When quiz is generated
- `recommendation.created` - When recommendations are ready

## API Endpoints (Planned)

- `POST /api/v1/chat` - Chat with AI assistant
- `POST /api/v1/generate/quiz` - Generate quiz for course
- `POST /api/v1/generate/summary` - Generate course summary
- `GET /api/v1/recommendations/{user_id}` - Get course recommendations
- `POST /api/v1/embeddings/generate` - Generate course embeddings

## Database

- **ai_chat_history** - Chat conversation history
- **course_embeddings** - Course vector embeddings
- **user_preferences** - User learning preferences
- **recommendations** - Generated recommendations cache
