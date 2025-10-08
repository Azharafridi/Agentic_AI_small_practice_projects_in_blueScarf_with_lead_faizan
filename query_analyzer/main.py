import os
from dotenv import load_dotenv
from openai import OpenAI
from typing import List, Dict
import json

# Load environment variables
load_dotenv()


class Agent:
    """Base class for AI agents"""
    
    def __init__(self, name: str, role: str, instructions: str, model: str = "gpt-4o-mini"):
        self.name = name
        self.role = role
        self.instructions = instructions
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversation_history: List[Dict[str, str]] = []
    
    def add_message(self, role: str, content: str):
        """Add a message to conversation history"""
        self.conversation_history.append({"role": role, "content": content})
    
    def get_response(self, user_message: str = None) -> str:
        """Get response from the agent"""
        if user_message:
            self.add_message("user", user_message)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.instructions},
                    *self.conversation_history
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            assistant_message = response.choices[0].message.content
            self.add_message("assistant", assistant_message)
            return assistant_message
        
        except Exception as e:
            return f"Error: {str(e)}"
    
    def reset(self):
        """Reset conversation history"""
        self.conversation_history = []


class QueryAnalyzerAgent(Agent):
    """Agent 1: Analyzes user queries through interactive conversation"""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        instructions = """You are a Query Analyzer Agent. Your role is to understand user queries deeply through intelligent conversation.

Your responsibilities:
1. Ask clarifying questions ONE AT A TIME to understand the user's intent, context, and requirements
2. Focus on gathering: purpose/goal, scope, constraints, preferences, timeline, location (if relevant)
3. Keep questions natural and conversational
4. After gathering sufficient information (typically 3-5 exchanges), provide a STRUCTURED SUMMARY

When you have enough information, respond with:
ANALYSIS_COMPLETE
---
**Original Query:** [user's initial query]
**Refined Understanding:**
- Purpose: [what they want to achieve]
- Scope: [specific details and boundaries]
- Context: [relevant situational information]
- Constraints: [limitations, requirements, or preferences]
- Additional Details: [any other relevant information]
---

Be concise, friendly, and efficient. Don't ask unnecessary questions."""
        
        super().__init__(
            name="Query Analyzer",
            role="Interactive Query Analysis",
            instructions=instructions,
            model=model
        )
        self.is_analysis_complete = False
        self.refined_query = ""
    
    def analyze_query(self, user_input: str) -> tuple[str, bool]:
        """
        Analyze query and determine if more information is needed
        Returns: (response, is_complete)
        """
        response = self.get_response(user_input)
        
        # Check if analysis is complete
        if "ANALYSIS_COMPLETE" in response:
            self.is_analysis_complete = True
            self.refined_query = response.split("---")[1].strip() if "---" in response else response
            return response, True
        
        return response, False


class ResponseGeneratorAgent(Agent):
    """Agent 2: Generates comprehensive responses based on refined queries"""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        instructions = """You are a Response Generator Agent. You receive well-analyzed and refined user queries and provide comprehensive, helpful responses.

Your responsibilities:
1. Generate detailed, actionable responses based on the refined query analysis
2. Address all aspects mentioned in the analysis
3. Provide practical suggestions, recommendations, or solutions
4. Structure your response clearly with relevant sections
5. Be thorough but concise

Always aim to provide maximum value based on the information provided."""
        
        super().__init__(
            name="Response Generator",
            role="Comprehensive Response Generation",
            instructions=instructions,
            model=model
        )
    
    def generate_response(self, refined_query: str) -> str:
        """Generate final response based on refined query"""
        prompt = f"""Based on the following refined query analysis, provide a comprehensive and helpful response:

{refined_query}

Generate a detailed response that addresses all aspects of the query."""
        
        return self.get_response(prompt)


class QueryAnalyzerSystem:
    """Main orchestrator for the two-agent system"""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.agent1 = None
        self.agent2 = None
        self.original_query = ""
    
    def print_separator(self, char: str = "=", length: int = 60):
        """Print a separator line"""
        print(char * length)
    
    def print_agent_message(self, agent_name: str, message: str):
        """Print formatted agent message"""
        print(f"\n🤖 {agent_name}:")
        print(f"{message}")
    
    def run(self):
        """Main execution loop"""
        print("\n" + "="*60)
        print("   QUERY ANALYZER AGENTIC AI SYSTEM")
        print("="*60)
        print("\nThis system uses two specialized agents:")
        print("  Agent 1: Analyzes and refines your query")
        print("  Agent 2: Provides comprehensive responses")
        print("\nType 'quit' or 'exit' to end the session.\n")
        self.print_separator()
        
        while True:
            # Get initial query
            print("\n" + "🎯 NEW QUERY SESSION".center(60))
            self.print_separator("-")
            
            user_query = input("\n👤 You: ").strip()
            
            if user_query.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Thank you for using the Query Analyzer System. Goodbye!\n")
                break
            
            if not user_query:
                print("⚠️  Please enter a query.")
                continue
            
            self.original_query = user_query
            
            # Initialize Agent 1
            self.agent1 = QueryAnalyzerAgent(model=self.model)
            
            print("\n" + "─"*60)
            print("  PHASE 1: Query Analysis (Agent 1)")
            print("─"*60)
            
            # Agent 1: Query Analysis Phase
            analysis_complete = False
            question_count = 0
            
            while not analysis_complete and question_count < 10:
                if question_count == 0:
                    response, analysis_complete = self.agent1.analyze_query(user_query)
                else:
                    user_answer = input("\n👤 You: ").strip()
                    
                    if user_answer.lower() in ['quit', 'exit', 'skip']:
                        print("\n⚠️  Ending analysis phase...")
                        break
                    
                    response, analysis_complete = self.agent1.analyze_query(user_answer)
                
                question_count += 1
                
                if not analysis_complete:
                    self.print_agent_message("Query Analyzer", response)
                else:
                    # Display refined query
                    print("\n" + "─"*60)
                    print("  ✓ Analysis Complete!")
                    print("─"*60)
                    refined = self.agent1.refined_query
                    if refined:
                        print(f"\n{refined}")
            
            # Check if we have a refined query
            if not self.agent1.refined_query:
                print("\n⚠️  Analysis incomplete. Starting new session...\n")
                continue
            
            # Agent 2: Response Generation Phase
            print("\n" + "─"*60)
            print("  PHASE 2: Response Generation (Agent 2)")
            print("─"*60)
            
            self.agent2 = ResponseGeneratorAgent(model=self.model)
            final_response = self.agent2.generate_response(self.agent1.refined_query)
            
            self.print_agent_message("Response Generator", final_response)
            
            print("\n" + "="*60)
            print("  SESSION COMPLETE")
            print("="*60)
            
            # Ask if user wants to continue
            print("\n")
            continue_choice = input("Would you like to start a new query? (yes/no): ").strip().lower()
            if continue_choice not in ['yes', 'y']:
                print("\n👋 Thank you for using the Query Analyzer System. Goodbye!\n")
                break
            
            print("\n")


def main():
    """Main entry point"""
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in environment variables.")
        print("Please create a .env file with your OpenAI API key.")
        return
    
    # Get model from environment or use default
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # Initialize and run the system
    system = QueryAnalyzerSystem(model=model)
    
    try:
        system.run()
    except KeyboardInterrupt:
        print("\n\n👋 System interrupted. Goodbye!\n")
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}\n")


if __name__ == "__main__":
    main()