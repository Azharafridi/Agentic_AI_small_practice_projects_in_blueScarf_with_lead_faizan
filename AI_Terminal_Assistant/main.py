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
            
            # Clean up markdown if present
            command = command.replace("```bash", "").replace("```sh", "").replace("```powershell", "").replace("```cmd", "").replace("```", "").strip()
            
            return command
            
        except Exception as e:
            print(f"❌ Error calling OpenAI API for command planning: {e}")
            return f"echo 'Error: Could not plan command - {str(e)}'"
    
    def _get_llm_prompt(self, user_input: str) -> str:
        """Generate prompt for LLM-based command planning"""
        shell_info = self._get_shell_info()
        
        return f"""Convert the following natural language request into a single, safe shell command.

Operating System: {self.os_type}
Shell: {shell_info}
User Request: {user_input}

Rules:
1. Return ONLY the command, no explanations or markdown
2. Use common, widely-supported commands for {self.os_type}
3. Prefer read-only operations when possible
4. Never suggest destructive commands like rm -rf, format, or shutdown
5. If the request is unclear, return an echo command asking for clarification
6. For Windows: Use PowerShell-compatible commands or cmd commands
7. For Linux/Mac: Use bash-compatible commands
8. Ensure the command works natively on {self.os_type}

Respond with ONLY the shell command:"""
    
    def _get_shell_info(self) -> str:
        """Get appropriate shell information based on OS"""
        if self.os_type == "Windows":
            return "PowerShell/CMD"
        elif self.os_type == "Darwin":
            return "bash/zsh (macOS)"
        else:
            return "bash"


class SafetyChecker:
    """Agent 2: Verifies command safety before execution using OpenAI API"""
    
    # Pre-defined dangerous patterns for fast filtering (cross-platform)
    DANGEROUS_PATTERNS = [
        # File deletion (Unix/Linux/Mac)
        "rm -rf", "rm -fr", "rm -r", "shred",
        # File deletion (Windows)
        "rmdir /s", "del /s", "del /f", "rd /s", "remove-item -recurse", "format",
        # Disk operations
        "mkfs", "dd if=", "fdisk", "parted", "diskpart",
        # System control (Unix/Linux/Mac)
        "shutdown", "reboot", "init 0", "init 6", "poweroff", "halt",
        "systemctl stop", "systemctl disable",
        # System control (Windows)
        "shutdown /s", "shutdown /r", "restart-computer", "stop-computer",
        # Network/firewall (Unix/Linux/Mac)
        "iptables -F", "iptables -X", "firewall-cmd", "ufw disable",
        # Network/firewall (Windows)
        "netsh advfirewall", "disable-netfirewallrule",
        # Package management (Unix/Linux/Mac)
        "apt-get remove", "yum remove", "dnf remove", "brew uninstall",
        "pip uninstall", "npm uninstall -g",
        # Permission changes (Unix/Linux/Mac)
        "chmod 777", "chown", "passwd", "useradd", "userdel",
        "sudo su", "su -",
        # System file modification (Unix/Linux/Mac)
        "> /etc/", "> /sys/", "> /proc/", "> /dev/",
        # System file modification (Windows)
        "> c:\\windows", "> c:\\system",
        # Registry modification (Windows)
        "reg delete", "remove-item hklm:", "remove-item hkcu:",
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
        
        # Pre-filter dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in command_lower:
                return (
                    SafetyStatus.UNSAFE,
                    f"⛔ BLOCKED: Command contains dangerous pattern '{pattern}'. "
                    f"This could modify or delete system files."
                )
        
        # Use LLM for deeper analysis
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
            
            # Parse response
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
3. Privilege escalation attempts (sudo, su, runas)
4. Data overwrites or corruption risks
5. System shutdown or restart commands
6. Package removal or system configuration changes
7. Registry modifications (Windows)
8. Disk operations

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
        self.os_type = platform.system()
    
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
            # Get user confirmation if in interactive mode
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
    
    def _get_current_directory(self) -> str:
        """Get the current working directory safely (cross-platform)"""
        try:
            # Use Python's os.getcwd() which is cross-platform
            return os.getcwd()
        except Exception as e:
            # Fallback to subprocess if needed
            try:
                if self.os_type == 'Windows':
                    result = subprocess.run(
                        'cd',
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                else:
                    result = subprocess.run(
                        'pwd',
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                return result.stdout.strip()
            except:
                return "[Unknown directory]"
    
    def _enhance_command_output(self, command: str, output: str) -> str:
        """Enhance output for file/directory creation commands (cross-platform)"""
        
        # Keywords that indicate file or directory creation
        # Unix/Linux/Mac commands
        unix_keywords = ['touch', 'mkdir', 'echo >', 'cat >', '> ']
        # Windows commands
        windows_keywords = ['new-item', 'ni ', 'echo.>', 'type nul >', 'md ', 'mkdir']
        
        command_lower = command.lower()
        
        # Check if this is a file creation command
        is_file_creation = (
            any(keyword in command_lower for keyword in unix_keywords) or
            any(keyword in command_lower for keyword in windows_keywords)
        )
        
        if is_file_creation:
            try:
                cwd = self._get_current_directory()
                
                # Extract filename from command
                filename = self._extract_filename(command)
                
                if output == "[Command executed successfully with no output]":
                    if filename:
                        full_path = os.path.join(cwd, filename)
                        # Normalize path for current OS
                        full_path = os.path.normpath(full_path)
                        return f"✅ File/directory created successfully!\n📍 Location: {full_path}"
                    else:
                        return f"✅ File/directory created successfully!\n📍 Location: {cwd}"
                else:
                    return f"{output}\n\n📍 Working Directory: {cwd}"
            except Exception as e:
                # If we can't get location info, just return original output
                pass
        
        return output
    
    def _extract_filename(self, command: str) -> str:
        """Extract filename from common file creation commands (cross-platform)"""
        try:
            command = command.strip()
            command_lower = command.lower()
            
            # Unix/Linux/Mac commands
            # Handle touch command
            if command_lower.startswith('touch '):
                parts = command.split()
                if len(parts) >= 2:
                    return parts[1].strip('"\'')
            
            # Handle mkdir command (Unix)
            elif command_lower.startswith('mkdir '):
                parts = command.split()
                if len(parts) >= 2:
                    # Skip flags like -p
                    for part in parts[1:]:
                        if not part.startswith('-'):
                            return part.strip('"\'')
            
            # Windows commands
            # Handle New-Item (PowerShell)
            elif 'new-item' in command_lower:
                # Look for -Path parameter
                if '-path' in command_lower:
                    parts = command.split()
                    for i, part in enumerate(parts):
                        if part.lower() == '-path' and i + 1 < len(parts):
                            return parts[i + 1].strip('"\'')
                # Look for -Name parameter
                elif '-name' in command_lower:
                    parts = command.split()
                    for i, part in enumerate(parts):
                        if part.lower() == '-name' and i + 1 < len(parts):
                            return parts[i + 1].strip('"\'')
                else:
                    # First argument after New-Item
                    parts = command.split()
                    if len(parts) >= 2:
                        return parts[1].strip('"\'')
            
            # Handle echo > file (both Unix and Windows)
            elif '>' in command and 'echo' in command_lower:
                parts = command.split('>')
                if len(parts) >= 2:
                    filename = parts[-1].strip()
                    # Remove any trailing commands (like in && chains)
                    if '&&' in filename:
                        filename = filename.split('&&')[0].strip()
                    return filename.strip('"\'')
            
            # Handle type nul > file (Windows)
            elif 'type nul' in command_lower and '>' in command:
                parts = command.split('>')
                if len(parts) >= 2:
                    return parts[-1].strip().strip('"\'')
            
            # Handle md/mkdir (Windows CMD)
            elif command_lower.startswith('md ') or command_lower.startswith('mkdir '):
                parts = command.split(maxsplit=1)
                if len(parts) >= 2:
                    return parts[1].strip('"\'')
            
        except Exception as e:
            print(f"Debug: Error extracting filename: {e}")
        
        return ""
    
    def _execute_command(self, command: str) -> str:
        """
        Safely execute a shell command and return output (cross-platform).
        """
        try:
            # Determine the appropriate shell based on OS
            if self.os_type == 'Windows':
                # Use PowerShell for Windows (better compatibility)
                # Check if it's a PowerShell command
                if command.lower().startswith(('new-item', 'get-', 'set-', 'remove-item', 'copy-item', 'move-item')):
                    # PowerShell command
                    shell_command = ['powershell', '-Command', command]
                    result = subprocess.run(
                        shell_command,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                else:
                    # CMD command or generic command
                    result = subprocess.run(
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
            else:
                # Unix/Linux/Mac - use default shell
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    executable='/bin/bash'  # Explicitly use bash
                )
            
            output = result.stdout
            if result.stderr:
                # Only include stderr if it looks like an error (not just warnings)
                stderr = result.stderr.strip()
                if stderr and result.returncode != 0:
                    output += f"\n[stderr]: {stderr}"
            
            final_output = output if output.strip() else "[Command executed successfully with no output]"
            
            # Enhance output with location info for file operations
            return self._enhance_command_output(command, final_output)
        
        except subprocess.TimeoutExpired:
            return "[Error]: Command timed out after 10 seconds"
        except Exception as e:
            return f"[Error]: {str(e)}"
    
    def interactive_mode(self):
        """Run the assistant in interactive terminal mode"""
        print("\n" + "="*60)
        print("🤖 Smart Terminal Assistant (OpenAI-Powered)")
        print(f"💻 Running on: {self.os_type}")
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
        print(f"💻 Detected OS: {platform.system()}")
        print("="*60)
        
        show_demo = input("\nWould you like to see example demonstrations? (yes/no): ").strip().lower()
        
        if show_demo in ['yes', 'y']:
            print("\n🎯 Running Example Demonstrations:\n")
            print("Note: Demonstrations will ask for confirmation before execution.\n")
            
            # OS-specific examples
            if platform.system() == 'Windows':
                examples = [
                    "Show me the current directory",
                    "List all files in the current folder",
                    "Create a test.txt file",
                ]
            else:
                examples = [
                    "Show me how much space my disk is using",
                    "List all running Python processes",
                    "What is my current working directory?",
                    "Create a test.txt file",
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