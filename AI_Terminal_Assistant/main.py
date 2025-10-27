
import os
import subprocess
import platform
from typing import Dict, Tuple
from dataclasses import dataclass
from enum import Enum


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
    """Agent 1: Translates natural language to shell commands"""
    
    def __init__(self):
        self.os_type = platform.system()
    
    def plan_command(self, user_input: str) -> str:
        """
        Convert natural language request to shell command.
        In a real implementation, this would call an LLM API.
        """
        # For demonstration, using pattern matching
        # In production: Replace with actual LLM API call
        
        user_input_lower = user_input.lower()
        
        # Common command patterns
        patterns = {
            "current directory": "pwd",
            "working directory": "pwd",
            "list files": "ls -la" if self.os_type != "Windows" else "dir",
            "list all files": "ls -la" if self.os_type != "Windows" else "dir",
            "disk space": "df -h" if self.os_type != "Windows" else "wmic logicaldisk get size,freespace,caption",
            "disk usage": "du -sh *" if self.os_type != "Windows" else "dir",
            "python processes": "ps aux | grep python" if self.os_type != "Windows" else "tasklist | findstr python",
            "running processes": "ps aux" if self.os_type != "Windows" else "tasklist",
            "network status": "netstat -tuln" if self.os_type != "Windows" else "netstat -an",
            "ip address": "ip addr" if self.os_type == "Linux" else "ifconfig" if self.os_type == "Darwin" else "ipconfig",
            "current user": "whoami",
            "who am i": "whoami",
            "my username": "whoami",
            "date and time": "date" if self.os_type != "Windows" else "date /t && time /t",
            "environment variables": "env" if self.os_type != "Windows" else "set",
            "system info": "uname -a" if self.os_type != "Windows" else "systeminfo",
        }
        
        for pattern, command in patterns.items():
            if pattern in user_input_lower:
                return command
        
        # Default: return a safe echo command
        return f"echo 'Command not recognized: {user_input}'"
    
    def get_llm_prompt(self, user_input: str) -> str:
        """Generate prompt for LLM-based command planning"""
        return f"""You are a shell command expert. Convert the following natural language request into a single, safe shell command.

Operating System: {self.os_type}
User Request: {user_input}

Rules:
1. Return ONLY the command, no explanations
2. Use common, widely-supported commands
3. Prefer read-only operations
4. Never suggest destructive commands
5. If unclear, return an echo command with clarification request

Shell Command:"""


class SafetyChecker:
    """Agent 2: Verifies command safety before execution"""
    
    # Dangerous command patterns
    DANGEROUS_PATTERNS = [
        # Deletion commands
        "rm -rf", "rm -fr", "rm -r", "rmdir /s", "del /s", "format",
        "mkfs", "dd if=", "shred",
        
        # System modification
        "shutdown", "reboot", "init 0", "init 6", "poweroff", "halt",
        "systemctl", "service", "chkconfig",
        
        # Network/Firewall
        "iptables", "firewall-cmd", "ufw", "netsh",
        
        # Package management (can modify system)
        "apt-get remove", "yum remove", "dnf remove", "brew uninstall",
        "pip uninstall", "npm uninstall -g",
        
        # User/Permission changes
        "chmod 777", "chown", "passwd", "useradd", "userdel",
        "sudo su", "su -",
        
        # File overwrites
        "> /etc/", "> /sys/", "> /proc/", "> /dev/",
        
        # Disk operations
        "fdisk", "parted", "mkfs", "mount -o remount",
        
        # Critical paths
        "/boot", "/sys", "/proc", "/dev/sd",
    ]
    
    # Safe command prefixes (read-only operations)
    SAFE_PREFIXES = [
        "ls", "dir", "pwd", "echo", "cat", "head", "tail", "grep",
        "find", "locate", "which", "whereis", "ps", "top", "htop",
        "df", "du", "free", "uptime", "date", "cal", "whoami",
        "uname", "hostname", "env", "printenv", "history",
        "ifconfig", "ip addr", "netstat", "ping", "traceroute",
        "wc", "sort", "uniq", "diff", "file", "stat",
    ]
    
    def check_safety(self, command: str) -> Tuple[SafetyStatus, str]:
        """
        Analyze command for safety.
        Returns: (SafetyStatus, explanation_message)
        """
        command_lower = command.lower().strip()
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in command_lower:
                return (
                    SafetyStatus.UNSAFE,
                    f"⛔ BLOCKED: Command contains dangerous pattern '{pattern}'. "
                    f"This could modify or delete system files."
                )
        
        # Check for pipe to dangerous commands
        if "|" in command:
            parts = command.split("|")
            for part in parts:
                part_stripped = part.strip().lower()
                if any(danger in part_stripped for danger in ["rm", "del", "shutdown"]):
                    return (
                        SafetyStatus.UNSAFE,
                        "⛔ BLOCKED: Piped command contains potentially dangerous operations."
                    )
        
        # Check for safe command prefixes
        command_first_word = command_lower.split()[0] if command_lower.split() else ""
        if any(command_first_word.startswith(safe) for safe in self.SAFE_PREFIXES):
            return (
                SafetyStatus.SAFE,
                "✅ SAFE: Command is read-only and safe to execute."
            )
        
        # Check for redirects to system locations
        if ">" in command and any(path in command_lower for path in ["/etc", "/sys", "/boot", "c:\\windows"]):
            return (
                SafetyStatus.UNSAFE,
                "⛔ BLOCKED: Attempting to write to system directory."
            )
        
        # Default to safe for simple echo commands
        if command_first_word == "echo":
            return (
                SafetyStatus.SAFE,
                "✅ SAFE: Echo command is harmless."
            )
        
        # Unknown command - be cautious
        return (
            SafetyStatus.UNKNOWN,
            "⚠️  CAUTION: Command safety could not be verified. Execution blocked by default."
        )
    
    def get_llm_prompt(self, command: str) -> str:
        """Generate prompt for LLM-based safety checking"""
        return f"""You are a cybersecurity expert specializing in command safety analysis.

Analyze this shell command for safety:
Command: {command}

Check for:
1. File deletion or system modification
2. Network or firewall changes
3. Privilege escalation attempts
4. Data overwrites or corruption risks
5. System shutdown or restart commands

Respond with:
- SAFE: if the command only reads information
- UNSAFE: if the command could harm the system
- Briefly explain why

Analysis:"""


class SmartTerminalAssistant:
    """Main coordinator for the Smart Terminal Assistant"""
    
    def __init__(self):
        self.planner = CommandPlanner()
        self.safety_checker = SafetyChecker()
        self.execution_enabled = True
    
    def process_request(self, user_input: str) -> CommandAnalysis:
        """
        Process user request through the two-agent pipeline.
        """
        print(f"\n{'='*60}")
        print(f"📝 User Request: {user_input}")
        print(f"{'='*60}")
        
        # Agent 1: Plan the command
        print("\n🕹️  Agent 1 (Command Planner): Analyzing request...")
        planned_command = self.planner.plan_command(user_input)
        print(f"   Planned Command: {planned_command}")
        
        # Agent 2: Check safety
        print("\n🛡️  Agent 2 (Safety Checker): Verifying safety...")
        safety_status, safety_message = self.safety_checker.check_safety(planned_command)
        print(f"   {safety_message}")
        
        # Execute if safe
        execution_output = ""
        if safety_status == SafetyStatus.SAFE and self.execution_enabled:
            print("\n⚙️  Executing command...")
            execution_output = self._execute_command(planned_command)
            print(f"\n📤 Output:\n{execution_output}")
        elif safety_status == SafetyStatus.UNSAFE:
            print("\n❌ Execution blocked for safety reasons.")
        else:
            print("\n⚠️  Execution skipped due to safety uncertainty.")
        
        return CommandAnalysis(
            original_request=user_input,
            planned_command=planned_command,
            safety_status=safety_status,
            safety_message=safety_message,
            execution_output=execution_output
        )
    
    def _execute_command(self, command: str) -> str:
        """
        Safely execute a shell command and return output.
        """
        try:
            # Use subprocess for safer execution
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10  # 10 second timeout
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
        print("🤖 Smart Terminal Assistant")
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
    assistant = SmartTerminalAssistant()
    
    # Demonstrate with some examples
    print("\n🎯 Running Example Demonstrations:\n")
    
    examples = [
        "Show me how much space my disk is using.",
        "List all running Python processes.",
        "What is my current working directory?",
        "Show me my IP address",
    ]
    
    for example in examples:
        assistant.process_request(example)
        print("\n" + "-"*60 + "\n")
    
    # Start interactive mode
    print("\n\n🚀 Starting Interactive Mode...\n")
    assistant.interactive_mode()


if __name__ == "__main__":
    main()