import os
import subprocess
import platform
from typing import Dict, Tuple
from dataclasses import dataclass
from enum import Enum
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class SafetyStatus(Enum):
    """Safety check result status"""
    SAFE = "safe"
    UNSAFE = "unsafe"
    UNKNOWN = "unknown"


@dataclass
class CommandAnalysis:
    """Result of command planning and safety analysis"""
    original_request: str
    planned_command: str
    safety_status: SafetyStatus
    safety_message: str
    execution_output: str = ""


class CommandPlanner:
    """Agent 1: Translates natural language to shell commands using OpenAI API"""
    
    def __init__(self):
        self.os_type = platform.system()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in your .env file.")
    
    def plan_command(self, user_input: str) -> str:
        """
        Convert natural language request to shell command using OpenAI API.
        """
        try:
            prompt = self._get_llm_prompt(user_input)
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=[
                    {
                        "role": "system",
                        "content": "You are a shell command expert. Your job is to convert natural language requests into safe, executable shell commands. Return ONLY the command itself, no explanations, no markdown, no code blocks."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3, 
                max_tokens=150
            )
            
            command = response.choices[0].message.content.strip()
            

            command = command.replace("```bash", "").replace("```sh", "").replace("```", "").strip()
            
            return command
            
        except Exception as e:
            print(f"❌ Error calling OpenAI API for command planning: {e}")
            return f"echo 'Error: Could not plan command - {str(e)}'"
    
    def _get_llm_prompt(self, user_input: str) -> str:
        """Generate prompt for LLM-based command planning"""
        return f"""Convert the following natural language request into a single, safe shell command.

Operating System: {self.os_type}
User Request: {user_input}

Rules:
1. Return ONLY the command, no explanations or markdown
2. Use common, widely-supported commands
3. Prefer read-only operations when possible
4. Never suggest destructive commands like rm -rf, format, or shutdown
5. If the request is unclear, return an echo command asking for clarification
6. Make sure the command is compatible with {self.os_type}

Respond with ONLY the shell command:"""


class SafetyChecker:
    """Agent 2: Verifies command safety before execution using OpenAI API"""
    

    DANGEROUS_PATTERNS = [

        "rm -rf", "rm -fr", "rm -r", "rmdir /s", "del /s", "format",
        "mkfs", "dd if=", "shred",
        "shutdown", "reboot", "init 0", "init 6", "poweroff", "halt",
        "systemctl stop", "systemctl disable",
        
        "iptables -F", "iptables -X", "firewall-cmd", "ufw disable",
        
        "apt-get remove", "yum remove", "dnf remove", "brew uninstall",
        "pip uninstall", "npm uninstall -g",
        
        "chmod 777", "chown", "passwd", "useradd", "userdel",
        "sudo su", "su -",
        
        "> /etc/", "> /sys/", "> /proc/", "> /dev/",
        
        "fdisk", "parted", "mkfs", "mount -o remount",
    ]
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in your .env file.")
    
    def check_safety(self, command: str) -> Tuple[SafetyStatus, str]:
        """
        Analyze command for safety using OpenAI API with pre-filtering.
        Returns: (SafetyStatus, explanation_message)
        """
        command_lower = command.lower().strip()
        
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in command_lower:
                return (
                    SafetyStatus.UNSAFE,
                    f"⛔ BLOCKED: Command contains dangerous pattern '{pattern}'. "
                    f"This could modify or delete system files."
                )
        
        try:
            prompt = self._get_llm_prompt(command)
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a cybersecurity expert. Analyze shell commands for safety. Respond with ONLY 'SAFE', 'UNSAFE', or 'UNKNOWN' followed by a brief explanation on the next line."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=200
            )
            
            analysis = response.choices[0].message.content.strip()
            
            lines = analysis.split('\n', 1)
            status_line = lines[0].upper()
            explanation = lines[1] if len(lines) > 1 else "No explanation provided."
            
            if "SAFE" in status_line and "UNSAFE" not in status_line:
                return (SafetyStatus.SAFE, f"✅ SAFE: {explanation}")
            elif "UNSAFE" in status_line:
                return (SafetyStatus.UNSAFE, f"⛔ BLOCKED: {explanation}")
            else:
                return (SafetyStatus.UNKNOWN, f"⚠️  CAUTION: {explanation}")
                
        except Exception as e:
            print(f"❌ Error calling OpenAI API for safety check: {e}")
            return (
                SafetyStatus.UNKNOWN,
                f"⚠️  CAUTION: Could not verify safety due to API error. Execution blocked by default."
            )
    
    def _get_llm_prompt(self, command: str) -> str:
        """Generate prompt for LLM-based safety checking"""
        return f"""Analyze this shell command for safety:

Command: {command}

Check for:
1. File deletion or system modification (rm, del, format, etc.)
2. Network or firewall changes
3. Privilege escalation attempts (sudo, su)
4. Data overwrites or corruption risks
5. System shutdown or restart commands
6. Package removal or system configuration changes

Respond in this exact format:
Line 1: SAFE, UNSAFE, or UNKNOWN
Line 2: Brief explanation (one sentence)

Analysis:"""


class SmartTerminalAssistant:
    """Main coordinator for the Smart Terminal Assistant"""
    
    def __init__(self):
        self.planner = CommandPlanner()
        self.safety_checker = SafetyChecker()
        self.execution_enabled = True
    
    def process_request(self, user_input: str, interactive: bool = True) -> CommandAnalysis:
        """
        Process user request through the two-agent pipeline.
        
        Args:
            user_input: The natural language request from the user
            interactive: If True, ask for user confirmation before execution
        """
        print(f"\n{'='*60}")
        print(f"📝 User Request: {user_input}")
        print(f"{'='*60}")
        
        print("\n🤖 Agent 1 (Command Planner): Analyzing request with OpenAI...")
        planned_command = self.planner.plan_command(user_input)
        print(f"   Planned Command: {planned_command}")
        
        print("\n🛡️  Agent 2 (Safety Checker): Verifying safety with OpenAI...")
        safety_status, safety_message = self.safety_checker.check_safety(planned_command)
        print(f"   {safety_message}")
        
        execution_output = ""
        if safety_status == SafetyStatus.UNSAFE:
            print("\n❌ Execution blocked for safety reasons.")
        elif safety_status == SafetyStatus.UNKNOWN:
            print("\n⚠️  Execution skipped due to safety uncertainty.")
        elif safety_status == SafetyStatus.SAFE and self.execution_enabled:

            if interactive:
                user_approval = self._get_user_confirmation(planned_command)
                if user_approval:
                    print("\n⚙️  Executing command...")
                    execution_output = self._execute_command(planned_command)
                    print(f"\n📤 Output:\n{execution_output}")
                else:
                    print("\n🚫 Execution cancelled by user.")
                    execution_output = "[Execution cancelled by user]"
            else:
                print("\n⚙️  Executing command...")
                execution_output = self._execute_command(planned_command)
                print(f"\n📤 Output:\n{execution_output}")
        
        return CommandAnalysis(
            original_request=user_input,
            planned_command=planned_command,
            safety_status=safety_status,
            safety_message=safety_message,
            execution_output=execution_output
        )
    
    def _get_user_confirmation(self, command: str) -> bool:
        """
        Ask user for confirmation before executing a command.
        
        Args:
            command: The command to be executed
            
        Returns:
            True if user confirms, False otherwise
        """
        print(f"\n{'─'*60}")
        print(f"🔍 Proposed Command: {command}")
        print(f"{'─'*60}")
        
        while True:
            try:
                response = input("Execute this command? (yes/no): ").strip().lower()
                
                if response in ['yes', 'y']:
                    return True
                elif response in ['no', 'n']:
                    return False
                else:
                    print("Please answer 'yes' or 'no'")
            except (EOFError, KeyboardInterrupt):
                print("\n")
                return False
    
    def _execute_command(self, command: str) -> str:
        """
        Safely execute a shell command and return output.
        """
        try:

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10  
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]: {result.stderr}"
            
            return output if output.strip() else "[Command executed successfully with no output]"
        
        except subprocess.TimeoutExpired:
            return "[Error]: Command timed out after 10 seconds"
        except Exception as e:
            return f"[Error]: {str(e)}"
    
    def interactive_mode(self):
        """Run the assistant in interactive terminal mode"""
        print("\n" + "="*60)
        print("🤖 Smart Terminal Assistant (OpenAI-Powered)")
        print("="*60)
        print("\nType your requests in natural language.")
        print("Commands are verified for safety before execution.")
        print("Type 'exit' or 'quit' to stop.\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ["exit", "quit", "q"]:
                    print("\n👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                self.process_request(user_input)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")


def main():
    """Entry point for the Smart Terminal Assistant"""
    try:
        assistant = SmartTerminalAssistant()
        
        print("\n🤖 Smart Terminal Assistant (AI-Powered)")
        print("="*60)
        
        show_demo = input("\nWould you like to see example demonstrations? (yes/no): ").strip().lower()
        
        if show_demo in ['yes', 'y']:
            print("\n🎯 Running Example Demonstrations:\n")
            print("Note: Demonstrations will ask for confirmation before execution.\n")
            
            examples = [
                "Show me how much space my disk is using.",
                "List all running Python processes.",
                "What is my current working directory?",
                "Show me my IP address",
            ]
            
            for example in examples:
                assistant.process_request(example, interactive=True)
                print("\n" + "-"*60 + "\n")
        
        # Start interactive mode
        print("\n🚀 Starting Interactive Mode...\n")
        assistant.interactive_mode()
        
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nPlease create a .env file with your OpenAI API key:")
        print("OPENAI_API_KEY=your-api-key-here")
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")


if __name__ == "__main__":
    main()