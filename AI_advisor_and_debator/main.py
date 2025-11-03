
import os
import sys
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

try:
    from openai import OpenAI
except ImportError:
    print("Error: OpenAI library not installed.")
    print("Please install it with: pip install openai --break-system-packages")
    sys.exit(1)


class DualAgentChatbot:
    def __init__(self, api_key=None):
        """Initialize the dual agent chatbot system"""
        if api_key is None:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-3.5-turbo"
        
        # Define agent personalities
        self.optimist_system = """You are an Optimist Agent. Your role is to:
- Always look on the bright side of things
- Find positive aspects and opportunities in every situation
- Encourage hope and possibility
- Be enthusiastic and uplifting
- Keep responses concise (2-4 sentences)"""

        self.realist_system = """You are a Realist Agent. Your role is to:
- Provide pragmatic and critical analysis
- Point out potential challenges and risks
- Be grounded in practical considerations
- Offer balanced, realistic perspectives
- Keep responses concise (2-4 sentences)"""

        self.debate_prompt = """Read the Optimist's response and provide a thoughtful counterpoint or critique from a realistic perspective. Keep it brief (2-3 sentences)."""
        
        self.optimist_debate_prompt = """Read the Realist's critique and provide a hopeful counter-argument or find the silver lining. Keep it brief (2-3 sentences)."""

    def get_optimist_response(self, user_question):
        """Get response from the Optimist agent"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.optimist_system},
                    {"role": "user", "content": user_question}
                ],
                temperature=0.8,
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error: {str(e)}"

    def get_realist_response(self, user_question):
        """Get response from the Realist agent"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.realist_system},
                    {"role": "user", "content": user_question}
                ],
                temperature=0.7,
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error: {str(e)}"

    def get_debate_response(self, agent_type, original_question, other_agent_response):
        """Get a debate response from an agent about the other agent's answer"""
        if agent_type == "realist":
            system_prompt = self.realist_system
            debate_instruction = self.debate_prompt
        else:
            system_prompt = self.optimist_system
            debate_instruction = self.optimist_debate_prompt
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Question: {original_question}\n\nOther agent said: {other_agent_response}\n\n{debate_instruction}"}
                ],
                temperature=0.7,
                max_tokens=100
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error: {str(e)}"

    def process_question(self, question):
        """Process a question through both agents and have them debate"""
        print("\n" + "="*70)
        print("PROCESSING YOUR QUESTION...")
        print("="*70)
        
        # Get initial responses
        print("\n🌟 Optimist Agent is thinking...")
        optimist_response = self.get_optimist_response(question)
        
        print("🎯 Realist Agent is thinking...")
        realist_response = self.get_realist_response(question)
        
        # Display initial responses
        print("\n" + "-"*70)
        print("INITIAL RESPONSES")
        print("-"*70)
        
        print("\n🌟 OPTIMIST AGENT:")
        print(f"   {optimist_response}")
        
        print("\n🎯 REALIST AGENT:")
        print(f"   {realist_response}")
        
        # Have them debate each other
        print("\n" + "-"*70)
        print("DEBATE")
        print("-"*70)
        
        print("\n🎯 Realist responds to Optimist...")
        realist_debate = self.get_debate_response("realist", question, optimist_response)
        print(f"🎯 REALIST: {realist_debate}")
        
        print("\n🌟 Optimist responds to Realist...")
        optimist_debate = self.get_debate_response("optimist", question, realist_response)
        print(f"🌟 OPTIMIST: {optimist_debate}")
        
        print("\n" + "="*70)


def print_welcome():
    """Print welcome message"""
    print("\n" + "="*70)
    print(" "*15 + "DUAL-PERSONALITY CHATBOT")
    print("="*70)
    print("\nWelcome! Ask any question and see two different perspectives:")
    print("  🌟 The OPTIMIST - Always sees the bright side")
    print("  🎯 The REALIST - Keeps it practical and grounded")
    print("\nThey'll also debate each other's responses!")
    print("\nCommands:")
    print("  • Type your question and press Enter")
    print("  • Type 'quit' or 'exit' to leave")
    print("="*70)


def main():
    """Main function to run the chatbot"""
    print_welcome()
    
    # Initialize chatbot
    try:
        chatbot = DualAgentChatbot()
    except ValueError as e:
        print(f"\n❌ {str(e)}")
        print("\nTo set your API key, run:")
        print("  export OPENAI_API_KEY='your-api-key-here'")
        return
    except Exception as e:
        print(f"\n❌ Error initializing chatbot: {str(e)}")
        return
    
    # Main conversation loop
    while True:
        try:
            # Get user input
            print("\n" + "-"*70)
            user_input = input("\n💭 Your question: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Thanks for chatting! Goodbye!\n")
                break
            
            # Skip empty input
            if not user_input:
                print("⚠️  Please enter a question.")
                continue
            
            # Process the question
            chatbot.process_question(user_input)
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ An error occurred: {str(e)}")
            print("Please try again.")


if __name__ == "__main__":
    main()