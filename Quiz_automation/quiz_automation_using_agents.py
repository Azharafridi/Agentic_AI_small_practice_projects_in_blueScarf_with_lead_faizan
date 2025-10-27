#!/usr/bin/env python3
"""
Study Assistant - AI-Powered Learning System
Two-agent architecture: Question Generator + Evaluator
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# Load environment variables
load_dotenv()


class QuestionType(Enum):
    MCQ = "multiple_choice"
    SHORT = "short_answer"
    TRUE_FALSE = "true_false"
    ESSAY = "essay"


class Difficulty(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass
class Question:
    id: int
    text: str
    type: QuestionType
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    points: int = 10


@dataclass
class Answer:
    question_id: int
    student_answer: str


@dataclass
class Evaluation:
    question_id: int
    score: float
    max_score: int
    feedback: str
    correct_answer: str
    is_correct: bool


class QuestionGenerator:
    """Agent 1: Generates quiz questions from study material"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"
    
    def generate_questions(
        self,
        content: str,
        num_questions: int = 5,
        difficulty: Difficulty = Difficulty.INTERMEDIATE,
        question_type: QuestionType = QuestionType.SHORT
    ) -> List[Question]:
        """Generate questions from study material"""
        
        prompt = self._build_generation_prompt(content, num_questions, difficulty, question_type)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        return self._parse_questions(response.choices[0].message.content, question_type)
    
    def _build_generation_prompt(
        self,
        content: str,
        num_questions: int,
        difficulty: Difficulty,
        question_type: QuestionType
    ) -> str:
        """Build prompt for question generation"""
        
        type_instructions = {
            QuestionType.MCQ: "Create multiple choice questions with 4 options (A, B, C, D). Mark the correct answer.",
            QuestionType.SHORT: "Create short answer questions requiring 2-3 sentence responses.",
            QuestionType.TRUE_FALSE: "Create true/false statements based on the content.",
            QuestionType.ESSAY: "Create essay questions requiring detailed explanations."
        }
        
        return f"""Analyze this study material and create {num_questions} high-quality quiz questions.

STUDY MATERIAL:
{content}

REQUIREMENTS:
- Difficulty Level: {difficulty.value}
- Question Type: {question_type.value}
- {type_instructions[question_type]}
- Cover different concepts from the material
- Ensure questions test understanding, not just memorization
- Include the correct answer for each question

FORMAT YOUR RESPONSE AS JSON:
{{
  "questions": [
    {{
      "id": 1,
      "text": "Question text here?",
      "type": "{question_type.value}",
      "options": ["A) option1", "B) option2", "C) option3", "D) option4"],  // only for MCQ
      "correct_answer": "Full correct answer here",
      "points": 10
    }}
  ]
}}

Generate exactly {num_questions} questions now."""
    
    def _parse_questions(self, response: str, question_type: QuestionType) -> List[Question]:
        """Parse JSON response into Question objects"""
        try:
            # Extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            json_str = response[start:end]
            data = json.loads(json_str)
            
            questions = []
            for q in data['questions']:
                questions.append(Question(
                    id=q['id'],
                    text=q['text'],
                    type=question_type,
                    options=q.get('options'),
                    correct_answer=q['correct_answer'],
                    points=q.get('points', 10)
                ))
            return questions
        except Exception as e:
            print(f"⚠️  Error parsing questions: {e}")
            return []


class Evaluator:
    """Agent 2: Evaluates student answers and provides feedback"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"
    
    def evaluate_answer(
        self,
        question: Question,
        student_answer: str,
        source_material: str
    ) -> Evaluation:
        """Evaluate a single answer with detailed feedback"""
        
        prompt = self._build_evaluation_prompt(question, student_answer, source_material)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        return self._parse_evaluation(response.choices[0].message.content, question)
    
    def _build_evaluation_prompt(
        self,
        question: Question,
        student_answer: str,
        source_material: str
    ) -> str:
        """Build prompt for answer evaluation"""
        
        return f"""Evaluate this student's answer with detailed feedback.

ORIGINAL QUESTION:
{question.text}

CORRECT ANSWER:
{question.correct_answer}

STUDENT'S ANSWER:
{student_answer}

SOURCE MATERIAL (for context):
{source_material[:1000]}...

EVALUATION CRITERIA:
1. Accuracy: Is the answer factually correct?
2. Completeness: Does it cover all key points?
3. Understanding: Does it demonstrate true comprehension?
4. Clarity: Is the explanation clear and well-structured?

PROVIDE EVALUATION IN JSON FORMAT:
{{
  "score": 8.5,  // out of {question.points}
  "is_correct": true,
  "feedback": "Detailed feedback explaining what's good and what could be improved...",
  "key_points_covered": ["point1", "point2"],
  "key_points_missed": ["point3"],
  "suggestions": "How to improve the answer..."
}}

Be encouraging but honest. Focus on learning, not just grading."""
    
    def _parse_evaluation(self, response: str, question: Question) -> Evaluation:
        """Parse evaluation response"""
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            json_str = response[start:end]
            data = json.loads(json_str)
            
            return Evaluation(
                question_id=question.id,
                score=data['score'],
                max_score=question.points,
                feedback=data['feedback'],
                correct_answer=question.correct_answer,
                is_correct=data['is_correct']
            )
        except Exception as e:
            print(f"⚠️  Error parsing evaluation: {e}")
            return Evaluation(
                question_id=question.id,
                score=0,
                max_score=question.points,
                feedback="Error during evaluation",
                correct_answer=question.correct_answer,
                is_correct=False
            )


class StudyAssistant:
    """Main orchestrator for the study assistant system"""
    
    def __init__(self, api_key: str):
        self.generator = QuestionGenerator(api_key)
        self.evaluator = Evaluator(api_key)
        self.questions: List[Question] = []
        self.evaluations: List[Evaluation] = []
        self.study_material: str = ""
    
    def start_session(self):
        """Main session flow"""
        self._print_header()
        
        # Get study material
        self.study_material = self._get_study_material()
        
        # Get preferences
        num_questions, difficulty, q_type = self._get_preferences()
        
        # Generate questions
        print("\n🔄 Generating questions from your study material...")
        self.questions = self.generator.generate_questions(
            self.study_material,
            num_questions,
            difficulty,
            q_type
        )
        
        if not self.questions:
            print("❌ Failed to generate questions. Please try again.")
            return
        
        print(f"✅ Generated {len(self.questions)} questions!\n")
        
        # Quiz loop
        self._conduct_quiz()
        
        # Show results
        self._show_results()
    
    def _print_header(self):
        """Print welcome header"""
        print("\n" + "="*60)
        print("📚 STUDY ASSISTANT - AI-Powered Learning System")
        print("="*60)
        print("Two specialized AI agents working together:")
        print("  🤖 Agent 1: Question Generator")
        print("  🤖 Agent 2: Answer Evaluator")
        print("="*60 + "\n")
    
    def _get_study_material(self) -> str:
        """Get study material from user"""
        print("📖 Input Study Material")
        print("-" * 40)
        print("Options:")
        print("  1. Paste text directly")
        print("  2. Load from file")
        
        choice = input("\nChoose option (1/2): ").strip()
        
        if choice == "2":
            filepath = input("Enter file path: ").strip()
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print(f"❌ Error reading file: {e}")
                print("Falling back to text input...")
        
        print("\nPaste your study material (press Ctrl+D or Ctrl+Z when done):")
        print("-" * 40)
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        
        return "\n".join(lines)
    
    def _get_preferences(self) -> tuple:
        """Get quiz preferences from user"""
        print("\n⚙️  Quiz Configuration")
        print("-" * 40)
        
        # Number of questions
        while True:
            try:
                num = int(input("Number of questions (1-20) [5]: ").strip() or "5")
                if 1 <= num <= 20:
                    break
                print("Please enter a number between 1 and 20")
            except ValueError:
                print("Please enter a valid number")
        
        # Difficulty
        print("\nDifficulty levels:")
        print("  1. Beginner")
        print("  2. Intermediate")
        print("  3. Advanced")
        diff_choice = input("Choose difficulty (1/2/3) [2]: ").strip() or "2"
        difficulty_map = {
            "1": Difficulty.BEGINNER,
            "2": Difficulty.INTERMEDIATE,
            "3": Difficulty.ADVANCED
        }
        difficulty = difficulty_map.get(diff_choice, Difficulty.INTERMEDIATE)
        
        # Question type
        print("\nQuestion types:")
        print("  1. Short Answer")
        print("  2. Multiple Choice")
        print("  3. True/False")
        print("  4. Essay")
        type_choice = input("Choose type (1/2/3/4) [1]: ").strip() or "1"
        type_map = {
            "1": QuestionType.SHORT,
            "2": QuestionType.MCQ,
            "3": QuestionType.TRUE_FALSE,
            "4": QuestionType.ESSAY
        }
        q_type = type_map.get(type_choice, QuestionType.SHORT)
        
        return num, difficulty, q_type
    
    def _conduct_quiz(self):
        """Run the quiz session"""
        print("\n" + "="*60)
        print("📝 QUIZ TIME!")
        print("="*60)
        
        for i, question in enumerate(self.questions, 1):
            print(f"\n\n{'='*60}")
            print(f"Question {i}/{len(self.questions)}")
            print("="*60)
            print(f"\n{question.text}\n")
            
            if question.options:
                for option in question.options:
                    print(f"  {option}")
                print()
            
            # Get student answer
            if question.type == QuestionType.ESSAY:
                print("Enter your answer (press Ctrl+D or Ctrl+Z when done):")
                lines = []
                try:
                    while True:
                        line = input()
                        lines.append(line)
                except EOFError:
                    pass
                student_answer = "\n".join(lines)
            else:
                student_answer = input("Your answer: ").strip()
            
            if not student_answer:
                print("⚠️  No answer provided. Skipping...")
                continue
            
            # Evaluate answer
            print("\n⏳ Evaluating your answer...")
            evaluation = self.evaluator.evaluate_answer(
                question,
                student_answer,
                self.study_material
            )
            self.evaluations.append(evaluation)
            
            # Show immediate feedback
            self._show_evaluation(evaluation)
    
    def _show_evaluation(self, eval: Evaluation):
        """Display evaluation feedback"""
        print("\n" + "-"*60)
        print("📊 EVALUATION")
        print("-"*60)
        
        # Score
        percentage = (eval.score / eval.max_score) * 100
        status = "✅ Correct" if eval.is_correct else "❌ Incorrect" if eval.score == 0 else "⚠️  Partially Correct"
        
        print(f"\n{status}")
        print(f"Score: {eval.score}/{eval.max_score} ({percentage:.1f}%)")
        
        # Feedback
        print(f"\n💬 Feedback:")
        print(f"{eval.feedback}")
        
        if not eval.is_correct:
            print(f"\n✓ Correct Answer:")
            print(f"{eval.correct_answer}")
        
        print("\n" + "-"*60)
        input("\nPress Enter to continue...")
    
    def _show_results(self):
        """Display final results summary"""
        if not self.evaluations:
            print("\n❌ No answers to evaluate.")
            return
        
        print("\n\n" + "="*60)
        print("📈 FINAL RESULTS")
        print("="*60)
        
        total_score = sum(e.score for e in self.evaluations)
        max_score = sum(e.max_score for e in self.evaluations)
        percentage = (total_score / max_score) * 100 if max_score > 0 else 0
        
        print(f"\nOverall Score: {total_score:.1f}/{max_score} ({percentage:.1f}%)")
        print(f"Questions Answered: {len(self.evaluations)}/{len(self.questions)}")
        
        correct = sum(1 for e in self.evaluations if e.is_correct)
        print(f"Correct Answers: {correct}/{len(self.evaluations)}")
        
        # Performance feedback
        print("\n" + "-"*60)
        if percentage >= 90:
            print("🌟 EXCELLENT! You have mastered this material!")
        elif percentage >= 75:
            print("👍 GOOD JOB! You have a solid understanding.")
        elif percentage >= 60:
            print("📚 KEEP STUDYING! You're making progress.")
        else:
            print("💪 DON'T GIVE UP! Review the material and try again.")
        
        # Weak areas
        weak_questions = [e for e in self.evaluations if not e.is_correct]
        if weak_questions:
            print("\n💡 Areas for improvement:")
            for e in weak_questions:
                q = next(q for q in self.questions if q.id == e.question_id)
                print(f"  • Review: {q.text[:60]}...")
        
        print("\n" + "="*60)
        print("Thank you for using Study Assistant! 📚")
        print("="*60 + "\n")


def main():
    """Main entry point"""
    # Load API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("Please create a .env file with: OPENAI_API_KEY=your_key_here")
        return
    
    try:
        assistant = StudyAssistant(api_key)
        assistant.start_session()
    except KeyboardInterrupt:
        print("\n\n👋 Session interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")


if __name__ == "__main__":
    main()