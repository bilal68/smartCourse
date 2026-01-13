"""Generate dummy course content for testing and development."""

import uuid
from pathlib import Path
from typing import List
from sqlalchemy.orm import Session

from app.modules.courses.models import Course, Module, LearningAsset, AssetType
from app.integrations.s3 import get_s3_client
from app.core.logging import get_logger

logger = get_logger(__name__)


class DummyContentGenerator:
    """
    Generates fake course content for development and testing.
    Creates realistic-looking transcripts, slides, and materials.
    """

    def __init__(self, db: Session):
        self.db = db
        self.s3_client = get_s3_client()

    def generate_for_course(self, course: Course) -> dict:
        """
        Generate dummy content for all modules and assets in a course.
        
        Args:
            course: Course object with loaded modules and assets
            
        Returns:
            dict with generation summary
        """
        logger.info("Generating dummy content for course", course_id=str(course.id))
        
        stats = {
            "course_id": str(course.id),
            "modules_processed": 0,
            "assets_processed": 0,
            "files_created": 0,
            "total_content_size": 0
        }

        # Generate content for each module
        for module in course.modules:
            stats["modules_processed"] += 1
            
            # Generate content for each asset in the module
            for asset in module.assets:
                try:
                    content_size = self._generate_asset_content(course.id, module, asset)
                    stats["assets_processed"] += 1
                    stats["files_created"] += 1
                    stats["total_content_size"] += content_size
                except Exception as e:
                    logger.error(
                        "Failed to generate content for asset",
                        asset_id=str(asset.id),
                        error=str(e)
                    )

        logger.info("Dummy content generation complete", **stats)
        return stats

    def _generate_asset_content(
        self, 
        course_id: uuid.UUID, 
        module: Module, 
        asset: LearningAsset
    ) -> int:
        """
        Generate content for a single asset based on its type.
        
        Returns:
            Size of generated content in bytes
        """
        # Create S3 key path
        key = f"courses/{course_id}/module-{module.id}/asset-{asset.id}"
        
        if asset.asset_type == AssetType.video:
            return self._generate_video_content(key, asset)
        elif asset.asset_type == AssetType.pdf:
            return self._generate_pdf_content(key, asset)
        elif asset.asset_type == AssetType.article:
            return self._generate_article_content(key, asset)
        else:
            return self._generate_generic_content(key, asset)

    def _generate_video_content(self, key: str, asset: LearningAsset) -> int:
        """Generate video transcript (we'll use text instead of actual video)."""
        
        transcript = f"""Video Transcript: {asset.title}

Introduction
{'=' * 50}

Welcome to this lesson on {asset.title}. In this video, we'll cover several important concepts
that are fundamental to understanding this topic.

Main Content
{'=' * 50}

Let's start with the basics. {asset.title} is an essential concept that every learner should
understand thoroughly. Here are the key points:

1. First Key Concept
   - This is an important fundamental principle
   - It relates to the broader context of the module
   - Pay special attention to how this connects with other topics

2. Second Key Concept  
   - Building on what we learned before
   - Here's a practical example to illustrate the point
   - Consider how you might apply this in real situations

3. Third Key Concept
   - Advanced considerations for this topic
   - Common mistakes to avoid
   - Best practices and recommendations

Practical Examples
{'=' * 50}

Now let's look at some practical examples that demonstrate these concepts in action.

Example 1: Basic Application
Here we can see how the concept applies in a straightforward scenario. Notice how
each component interacts with the others to produce the desired result.

Example 2: Advanced Usage
This example shows more sophisticated usage patterns. Pay attention to the nuances
and edge cases that might arise in production environments.

Summary
{'=' * 50}

To recap what we've covered:
- We introduced the fundamental concepts of {asset.title}
- We explored practical applications and examples
- We discussed best practices and common pitfalls

In the next lesson, we'll build on these concepts to explore more advanced topics.

Key Takeaways:
✓ Understand the core principles
✓ Practice with real examples
✓ Apply best practices in your work

Duration: {asset.duration_seconds or 600} seconds
"""
        
        # Store transcript
        transcript_key = f"{key}/transcript.txt"
        content_bytes = transcript.encode('utf-8')
        self.s3_client.put_object(transcript_key, content_bytes, 'text/plain')
        
        # Update asset with source URL
        asset.source_url = transcript_key
        self.db.commit()
        
        logger.debug("Generated video transcript", asset_id=str(asset.id), size=len(content_bytes))
        return len(content_bytes)

    def _generate_pdf_content(self, key: str, asset: LearningAsset) -> int:
        """Generate PDF content (as text for simplicity)."""
        
        pdf_content = f"""
{asset.title}
{'=' * 70}

Course Material - Educational Content

Table of Contents
{'=' * 70}
1. Introduction
2. Core Concepts
3. Detailed Explanations
4. Practical Applications
5. Summary and Conclusions

{'=' * 70}

Chapter 1: Introduction
{'=' * 70}

This document covers {asset.title} in comprehensive detail. The material is designed
to provide both theoretical understanding and practical knowledge that you can apply
immediately in real-world scenarios.

Learning Objectives:
• Understand the fundamental principles
• Master key concepts and terminology
• Apply knowledge to practical situations
• Develop problem-solving skills

Chapter 2: Core Concepts
{'=' * 70}

Let's explore the essential concepts that form the foundation of {asset.title}.

Concept 1: Fundamentals
The first concept we need to understand is the basic framework. This provides the
foundation for everything else we'll learn. Key aspects include:

- Primary principles that govern the topic
- Essential terminology and definitions
- Historical context and development
- Current best practices and standards

Concept 2: Advanced Principles
Building on the fundamentals, we can now explore more sophisticated aspects:

- Complex interactions and relationships
- Edge cases and special considerations
- Performance optimization techniques
- Security and reliability concerns

Chapter 3: Detailed Explanations
{'=' * 70}

In this section, we dive deep into the technical details. Each topic is explained
with examples and illustrations to ensure clear understanding.

Topic 3.1: Technical Details
Here we examine the internal workings and mechanisms. Understanding these details
helps you make informed decisions and troubleshoot effectively.

Topic 3.2: Implementation Strategies
Various approaches and their trade-offs. Learn when to use each strategy and why.

Topic 3.3: Common Patterns
Proven patterns that solve recurring problems. These patterns have been tested and
refined through practical use.

Chapter 4: Practical Applications
{'=' * 70}

Now let's see how to apply what we've learned in real situations.

Example Application 1
This example demonstrates a common use case. Notice how the principles we learned
are applied in practice.

Example Application 2
A more complex scenario that requires combining multiple concepts. Study how
different elements work together.

Best Practices:
✓ Always follow established guidelines
✓ Test thoroughly before deployment
✓ Document your work clearly
✓ Consider edge cases and error handling

Chapter 5: Summary and Conclusions
{'=' * 70}

We've covered a lot of ground in this material. Let's review the key points:

Key Points to Remember:
1. Fundamental principles provide the foundation
2. Advanced concepts build on the basics
3. Practical application requires practice
4. Continuous learning is essential

Further Reading:
• Additional resources for deeper study
• Related topics to explore
• Community forums and discussions
• Official documentation and references

Conclusion:
Understanding {asset.title} is crucial for success in this field. Continue practicing
and applying what you've learned, and don't hesitate to revisit this material as needed.

{'=' * 70}
End of Document
"""
        
        # Store PDF content as text
        pdf_key = f"{key}/document.txt"
        content_bytes = pdf_content.encode('utf-8')
        self.s3_client.put_object(pdf_key, content_bytes, 'text/plain')
        
        # Update asset with source URL
        asset.source_url = pdf_key
        self.db.commit()
        
        logger.debug("Generated PDF content", asset_id=str(asset.id), size=len(content_bytes))
        return len(content_bytes)

    def _generate_article_content(self, key: str, asset: LearningAsset) -> int:
        """Generate article/text content."""
        
        article = f"""# {asset.title}

{asset.description or 'A comprehensive guide to this topic.'}

## Introduction

In this article, we'll explore {asset.title} from multiple perspectives. Whether you're
a beginner or have some experience, you'll find valuable insights and practical information.

## Understanding the Basics

Before diving into advanced topics, let's establish a solid foundation. The basics of
{asset.title} include several key components:

### Component 1: Foundation
This is where everything begins. Understanding this component is crucial for grasping
more advanced concepts later on.

### Component 2: Building Blocks
These are the essential elements that you'll work with regularly. Familiarity with
these building blocks makes everything else easier.

### Component 3: Core Principles
These principles guide how we approach problems and solutions. They're not strict rules,
but rather guidelines that help us make better decisions.

## Advanced Topics

Now that we have the basics covered, let's explore more sophisticated aspects.

### Advanced Topic 1
This builds directly on what we learned in the basics. You'll see how the foundational
concepts apply in more complex situations.

### Advanced Topic 2
Here we tackle scenarios that require deeper understanding and careful consideration.

## Real-World Applications

Theory is important, but practical application is where real learning happens.

### Case Study 1: Industry Example
In this real-world scenario, we see how professionals apply {asset.title} to solve
actual business problems.

### Case Study 2: Common Use Cases
These are situations you're likely to encounter. Study how the principles are applied
and adapted to different contexts.

## Best Practices and Tips

Learn from the experience of others who have mastered this topic.

**Do's:**
- Follow established conventions
- Test your work thoroughly
- Document your decisions
- Seek feedback from peers

**Don'ts:**
- Don't skip the fundamentals
- Avoid over-complicating solutions
- Don't ignore error handling
- Never stop learning

## Troubleshooting Common Issues

Even experts encounter problems. Here's how to handle common issues:

**Issue 1: Common Problem**
- Symptoms: What you'll notice
- Cause: Why it happens
- Solution: How to fix it

**Issue 2: Frequent Mistake**
- What goes wrong and why
- How to prevent it
- How to recover if it happens

## Conclusion

We've covered a lot of ground in this article. Remember that mastering {asset.title}
takes time and practice. Keep experimenting, learning, and applying what you've learned.

### Key Takeaways
- Start with solid foundations
- Practice regularly
- Learn from mistakes
- Stay curious and keep learning

### Next Steps
Continue your learning journey by exploring related topics and practicing what you've
learned in this article.

---

*Article length: Comprehensive guide suitable for all skill levels*
*Last updated: 2026*
"""
        
        # Store article
        article_key = f"{key}/article.txt"
        content_bytes = article.encode('utf-8')
        self.s3_client.put_object(article_key, content_bytes, 'text/plain')
        
        # Update asset with source URL
        asset.source_url = article_key
        self.db.commit()
        
        logger.debug("Generated article content", asset_id=str(asset.id), size=len(content_bytes))
        return len(content_bytes)

    def _generate_generic_content(self, key: str, asset: LearningAsset) -> int:
        """Generate generic content for other asset types."""
        
        content = f"""Content for {asset.title}

This is learning material about {asset.title}.

Description:
{asset.description or 'Educational content designed to help you learn.'}

Type: {asset.asset_type.value}

This resource provides valuable information and insights that will enhance
your understanding of the subject matter. Take your time to review and
absorb the material.

Remember to:
- Review the content carefully
- Take notes on key points
- Practice what you learn
- Ask questions if anything is unclear

Good luck with your learning!
"""
        
        # Store content
        content_key = f"{key}/content.txt"
        content_bytes = content.encode('utf-8')
        self.s3_client.put_object(content_key, content_bytes, 'text/plain')
        
        # Update asset with source URL
        asset.source_url = content_key
        self.db.commit()
        
        logger.debug("Generated generic content", asset_id=str(asset.id), size=len(content_bytes))
        return len(content_bytes)

    @staticmethod
    def get_sample_topics() -> List[str]:
        """Get list of sample topics for creating demo courses."""
        return [
            "Introduction to Programming",
            "Data Structures and Algorithms",
            "Web Development Fundamentals",
            "Database Design Principles",
            "API Development Best Practices",
            "Software Testing Strategies",
            "Version Control with Git",
            "Cloud Computing Basics",
            "Security and Authentication",
            "Performance Optimization"
        ]
