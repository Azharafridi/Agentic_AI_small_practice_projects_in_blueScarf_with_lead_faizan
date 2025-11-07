import os
from openai import OpenAI
from dotenv import load_dotenv
import time

load_dotenv()


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

WRITER_AGENT_PROMPT = """You are a Creative Story Writer Agent, a master storyteller with expertise in crafting engaging narratives.

YOUR ROLE:
- Create well-structured, engaging stories based on the given topic
- Write stories that are medium-length (400-600 words)
- Include vivid descriptions, compelling characters, and clear plot progression
- Use engaging dialogue where appropriate
- Create stories with a clear beginning, middle, and end
- Incorporate sensory details to make the story immersive

STORY STRUCTURE GUIDELINES:
1. Opening Hook: Start with an engaging scene or situation
2. Character Introduction: Introduce protagonists with distinctive traits
3. Rising Action: Build tension or develop the situation
4. Climax: Present the key turning point or main event
5. Resolution: Provide a satisfying conclusion

WRITING STYLE:
- Use descriptive language that paints vivid mental images
- Vary sentence structure for rhythm and flow
- Show emotions through actions and dialogue, not just statements
- Maintain consistent tone throughout the story
- Use appropriate pacing for the narrative

When given a topic, create an original story that captures the essence of that topic while entertaining the reader.
"""

EDITOR_AGENT_PROMPT = """You are a Professional Story Editor Agent, an expert in literary analysis and narrative improvement.

YOUR ROLE:
- Review stories critically but constructively
- Identify strengths and weaknesses in the narrative
- Provide specific, actionable suggestions for improvement
- Focus on story structure, character development, pacing, and language

EVALUATION CRITERIA:
1. STRUCTURE: Does the story have clear beginning, middle, and end?
2. CHARACTER DEVELOPMENT: Are characters believable and well-developed?
3. PACING: Does the story flow well without rushing or dragging?
4. LANGUAGE: Is the writing clear, engaging, and appropriate?
5. COHERENCE: Does the story stay on topic and make logical sense?
6. EMOTIONAL IMPACT: Does the story evoke feelings or connection?

FEEDBACK FORMAT:
Provide your review in the following structure:

**STRENGTHS:**
- List 2-3 specific things done well

**AREAS FOR IMPROVEMENT:**
- List specific issues with clear examples from the text

**SUGGESTIONS:**
- Provide 2-4 concrete, actionable recommendations
- Be specific about WHAT to change and WHY
- Suggest alternative phrasings or approaches where relevant

**OVERALL ASSESSMENT:**
- Brief summary of whether the story successfully captures the topic
- Note if major revisions are needed or if minor edits are sufficient

Be honest but encouraging. Your goal is to help create the best possible story.
"""

WRITER_REVISION_PROMPT = """You are the Creative Story Writer Agent reviewing editorial feedback.

YOUR ROLE IN REVISION:
- Carefully read the editor's suggestions
- Evaluate each suggestion based on your creative vision and storytelling expertise
- Accept suggestions that genuinely improve the story
- Respectfully decline suggestions that don't align with your narrative intent
- Implement accepted changes seamlessly into the story

REVISION PROCESS:
1. Consider if the suggestion enhances clarity, engagement, or emotional impact
2. Maintain your original creative vision while being open to improvements
3. Ensure revisions flow naturally with the existing narrative
4. Keep the story's voice and tone consistent

OUTPUT FORMAT:
First, briefly state your response to the editor's feedback (2-3 sentences about what you're accepting/declining and why).

Then provide the REVISED STORY with improvements integrated naturally.

Remember: Good writing is rewriting. Be open to changes that make the story better, but stay true to your narrative vision.
"""


def writer_agent(topic):
    print("\n" + "="*70)
    print("📝 WRITER AGENT: Creating story...")
    print("="*70)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": WRITER_AGENT_PROMPT},
                {"role": "user", "content": f"Write a creative story about: {topic}"}
            ],
            temperature=0.8,
            max_tokens=1000
        )
        
        story = response.choices[0].message.content
        print("\n✅ Story created successfully!\n")
        return story
    
    except Exception as e:
        print(f"\n❌ Error in Writer Agent: {e}")
        return None


def editor_agent(topic, story):
    print("\n" + "="*70)
    print("🔍 EDITOR AGENT: Reviewing story...")
    print("="*70)
    
    try:
        review_prompt = f"""Topic: {topic}

Story to review:
{story}

Please provide your professional editorial review following the format specified in your instructions."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": EDITOR_AGENT_PROMPT},
                {"role": "user", "content": review_prompt}
            ],
            temperature=0.3, 
            max_tokens=800
        )
        
        feedback = response.choices[0].message.content
        print("\n✅ Review completed!\n")
        return feedback
    
    except Exception as e:
        print(f"\n❌ Error in Editor Agent: {e}")
        return None


def writer_revision_agent(topic, original_story, editor_feedback):
    print("\n" + "="*70)
    print("✏️  WRITER AGENT: Revising story based on feedback...")
    print("="*70)
    
    try:
        revision_prompt = f"""Topic: {topic}

Your Original Story:
{original_story}

Editor's Feedback:
{editor_feedback}

Please review the editor's suggestions and provide your revised story."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": WRITER_REVISION_PROMPT},
                {"role": "user", "content": revision_prompt}
            ],
            temperature=0.7,
            max_tokens=1200
        )
        
        revision = response.choices[0].message.content
        print("\n✅ Revision completed!\n")
        return revision
    
    except Exception as e:
        print(f"\n❌ Error in Writer Revision: {e}")
        return None


def print_header():
    print("\n" + "="*70)
    print(" "*20 + "📚 AI STORY WRITER TEAM 📚")
    print("="*70)
    print("\nTwo AI agents working together to create amazing stories:")
    print("  👤 Writer Agent  - Creates original stories")
    print("  👤 Editor Agent  - Reviews and suggests improvements")
    print("="*70 + "\n")


def print_section(title, content):
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)
    print(content)
    print("="*70 + "\n")


def display_story(story, title="ORIGINAL STORY"):
    print_section(title, story)


def display_feedback(feedback):
    print_section("📋 EDITOR'S FEEDBACK", feedback)


def display_final_story(revision):
    print_section("🌟 FINAL STORY (After Revision)", revision)


def save_to_file(topic, original_story, feedback, final_story):
    filename = f"story_{topic.replace(' ', '_')[:30]}_{int(time.time())}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("AI STORY WRITER TEAM - OUTPUT\n")
        f.write("="*70 + "\n\n")
        f.write(f"TOPIC: {topic}\n")
        f.write("="*70 + "\n\n")
        
        f.write("ORIGINAL STORY:\n")
        f.write("-"*70 + "\n")
        f.write(original_story)
        f.write("\n\n")
        
        f.write("EDITOR'S FEEDBACK:\n")
        f.write("-"*70 + "\n")
        f.write(feedback)
        f.write("\n\n")
        
        f.write("FINAL STORY (AFTER REVISION):\n")
        f.write("-"*70 + "\n")
        f.write(final_story)
        f.write("\n")
    
    print(f"\n💾 Story saved to: {filename}")


def main():
    print_header()
    print("Enter a story topic (or 'quit' to exit):")
    topic = input("📝 Topic: ").strip()
    
    if topic.lower() in ['quit', 'exit', 'q']:
        print("\n👋 Goodbye!")
        return
    
    if not topic:
        print("\n❌ Error: Please provide a topic!")
        return
    
    print(f"\n🎯 Creating a story about: '{topic}'")
    print("\n⏳ Starting the story creation process...\n")
    time.sleep(1)

    original_story = writer_agent(topic)
    if not original_story:
        return
    
    display_story(original_story, "📖 ORIGINAL STORY")
    
    input("\n⏸️  Press Enter to continue to Editor review...")

    editor_feedback = editor_agent(topic, original_story)
    if not editor_feedback:
        return
    
    display_feedback(editor_feedback)
    
    input("\n⏸️  Press Enter to see Writer's revision...")
    final_story = writer_revision_agent(topic, original_story, editor_feedback)
    if not final_story:
        return
    
    display_final_story(final_story)
    
    print("\n" + "="*70)
    save_choice = input("💾 Would you like to save this story to a file? (yes/no): ").strip().lower()
    
    if save_choice in ['yes', 'y']:
        save_to_file(topic, original_story, editor_feedback, final_story)
    
    print("\n" + "="*70)
    print("✨ Story creation complete! Thank you for using AI Story Writer Team!")
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Program interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")