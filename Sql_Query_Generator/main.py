import requests
import json
import os
import sys
import time

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_colored(text, color):
    """Print colored text to terminal"""
    print(f"{color}{text}{Colors.END}")

def print_agent_header(agent_name, emoji):
    """Print agent header"""
    print("\n" + "="*70)
    print_colored(f"{emoji} {agent_name} is working...", Colors.BOLD)
    print("="*70)

def load_api_key_from_env():
    """Load OpenAI API key from .env file"""
    env_path = os.path.join(os.getcwd(), '.env')
    
    if not os.path.exists(env_path):
        print_colored("ERROR: .env file not found in current directory!", Colors.RED)
        print("Create .env file with: OPENAI_API_KEY=sk-your-key-here")
        sys.exit(1)
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key.strip() == 'OPENAI_API_KEY':
                    return value.strip().strip('"').strip("'")
    
    print_colored("ERROR: OPENAI_API_KEY not found in .env file!", Colors.RED)
    print("Add this line to .env: OPENAI_API_KEY=sk-your-key-here")
    sys.exit(1)

def call_openai_api(system_prompt, user_message, max_tokens=2000):

    api_key = load_api_key_from_env()
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'gpt-4o-mini',  
        'messages': [
            {
                'role': 'system',
                'content': system_prompt
            },
            {
                'role': 'user',
                'content': user_message
            }
        ],
        'max_tokens': max_tokens,
        'temperature': 0.7
    }
    
    try:
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code != 200:
            print_colored(f"API Error: {response.status_code}", Colors.RED)
            print(response.text)
            sys.exit(1)
        
        result = response.json()
        return result['choices'][0]['message']['content']
    
    except Exception as e:
        print_colored(f"Error calling API: {str(e)}", Colors.RED)
        sys.exit(1)

class SQLInterpreter:
    """Agent 1: Interprets natural language and converts to SQL logic"""
    
    def __init__(self):
        self.system_prompt = """You are an expert SQL query interpreter. Your job is to:
1. Understand the user's natural language request
2. Identify the tables, columns, and operations needed
3. Convert the request into SQL query logic
4. Output a SQL query

Focus on common SQL operations: SELECT, INSERT, UPDATE, DELETE, JOIN, WHERE, GROUP BY, ORDER BY.
Assume standard SQL syntax (PostgreSQL/MySQL compatible).
Output ONLY the SQL query, no explanations or markdown formatting."""

    def interpret(self, natural_language_query, schema_info=""):
        """Convert natural language to SQL"""
        print_agent_header("AGENT 1: SQL INTERPRETER", "🧠")
        
        user_message = f"""Convert this natural language request to a SQL query:

Request: {natural_language_query}

{schema_info if schema_info else ''}

Provide the SQL query directly without any markdown formatting or explanations."""
        
        sql_query = call_openai_api(self.system_prompt, user_message)
        
        
        sql_query = sql_query.strip()
        
        if sql_query.startswith('```'):
            lines = sql_query.split('\n')
            sql_query = '\n'.join(lines[1:-1]) if len(lines) > 2 else sql_query
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
        
        print_colored("\n📝 Generated SQL Query:", Colors.GREEN)
        print(sql_query)
        
        return sql_query

class SQLValidator:
    """Agent 2: Validates SQL syntax and suggests optimizations"""
    
    def __init__(self):
        self.system_prompt = """You are an expert SQL validator and optimizer. Your job is to:
1. Check the SQL query for syntax errors
2. Identify potential performance issues
3. Suggest optimizations (indexes, query restructuring, etc.)
4. Check for SQL injection vulnerabilities
5. Ensure the query follows best practices

Provide your analysis in this format:
STATUS: [VALID/INVALID/WARNING]
ISSUES: [List any problems found, or "None"]
OPTIMIZATIONS: [List suggested improvements, or "None"]
IMPROVED_QUERY: [Provide optimized version if applicable, or "No changes needed"]"""

    def validate(self, sql_query):
        """Validate and optimize SQL query"""
        print_agent_header("AGENT 2: SQL VALIDATOR", "🔍")
        
        user_message = f"""Analyze this SQL query for correctness and optimization opportunities:

{sql_query}

Provide detailed validation and optimization suggestions."""
        
        validation_result = call_openai_api(self.system_prompt, user_message)
        
        print_colored("\n🔎 Validation Results:", Colors.YELLOW)
        print(validation_result)
        
        return validation_result

class SQLExplainer:
    """Agent 3: Explains what the SQL query does in plain English"""
    
    def __init__(self):
        self.system_prompt = """You are an expert at explaining SQL queries in simple, clear English. Your job is to:
1. Break down the SQL query into logical steps
2. Explain what each part does
3. Describe the expected output
4. Mention any important considerations (performance, data types, etc.)

Write your explanation so that someone without SQL knowledge can understand what the query accomplishes."""

    def explain(self, sql_query, validation_notes=""):
        """Explain the SQL query in plain English"""
        print_agent_header("AGENT 3: SQL EXPLAINER", "📖")
        
        user_message = f"""Explain this SQL query in plain English:

{sql_query}

{f'Validator notes: {validation_notes}' if validation_notes else ''}

Provide a clear, simple explanation of what this query does."""
        
        explanation = call_openai_api(self.system_prompt, user_message)
        
        print_colored("\n📚 Query Explanation:", Colors.CYAN)
        print(explanation)
        
        return explanation

def get_multiline_input(prompt):
    """Get multi-line input from user"""
    print_colored(prompt, Colors.BOLD)
    print_colored("(Press Enter twice to finish, or type 'exit' to quit)", Colors.YELLOW)
    
    lines = []
    empty_line_count = 0
    
    while True:
        try:
            line = input()
            
            if line.lower() == 'exit':
                return None
            
            if line == '':
                empty_line_count += 1
                if empty_line_count >= 2:
                    break
            else:
                empty_line_count = 0
                lines.append(line)
        
        except EOFError:
            break
    
    return '\n'.join(lines).strip()

def save_results(query, validation, explanation, filename="sql_query_output.txt"):
    """Save the results to a file"""
    try:
        with open(filename, 'w') as f:
            f.write("="*70 + "\n")
            f.write("SQL QUERY BUILDER TEAM - RESULTS\n")
            f.write("="*70 + "\n\n")
            
            f.write("GENERATED SQL QUERY:\n")
            f.write("-"*70 + "\n")
            f.write(query + "\n\n")
            
            f.write("VALIDATION & OPTIMIZATION:\n")
            f.write("-"*70 + "\n")
            f.write(validation + "\n\n")
            
            f.write("EXPLANATION:\n")
            f.write("-"*70 + "\n")
            f.write(explanation + "\n")
        
        print_colored(f"\n💾 Results saved to: {filename}", Colors.GREEN)
        return True
    except Exception as e:
        print_colored(f"Error saving file: {str(e)}", Colors.RED)
        return False

def main():

    
    print_colored("""
╔══════════════════════════════════════════════════════════════════╗
║        SQL QUERY BUILDER TEAM - Multi-Agent System              ║
║                    (Powered by OpenAI GPT-4)                     ║
║                                                                  ║
║  🧠 Agent 1: Interprets natural language → SQL                  ║
║  🔍 Agent 2: Validates syntax & optimizes                        ║
║  📖 Agent 3: Explains query in plain English                     ║
╚══════════════════════════════════════════════════════════════════╝
    """, Colors.CYAN)
    

    interpreter = SQLInterpreter()
    validator = SQLValidator()
    explainer = SQLExplainer()
    
    while True:
        print("\n" + "="*70)
        print_colored("NEW QUERY REQUEST", Colors.BOLD)
        print("="*70)
        
        
        natural_language_query = get_multiline_input("\n🤔 Describe what you want to query (in plain English):")
        
        if natural_language_query is None or natural_language_query == '':
            print_colored("\nExiting SQL Query Builder Team. Goodbye! 👋", Colors.CYAN)
            break
        
        
        print_colored("\n📋 Do you want to provide table schema information? (y/n)", Colors.YELLOW)
        provide_schema = input().lower().strip()
        
        schema_info = ""
        if provide_schema == 'y':
            schema_info = get_multiline_input("\n📊 Paste your table schema (CREATE TABLE statements or description):")
            if schema_info:
                schema_info = f"Database Schema:\n{schema_info}"
        
        print_colored("\n🚀 Starting agent collaboration...\n", Colors.GREEN)
        time.sleep(1)
        
        # Agent 1: Interpret and generate SQL
        sql_query = interpreter.interpret(natural_language_query, schema_info)
        time.sleep(1)
        
        # Agent 2: Validate and optimize
        validation_result = validator.validate(sql_query)
        time.sleep(1)
        
        # Agent 3: Explain the query
        explanation = explainer.explain(sql_query, validation_result)
        
        # Final output
        print("\n" + "="*70)
        print_colored("✅ FINAL RESULTS", Colors.BOLD + Colors.GREEN)
        print("="*70)
        
        print_colored("\n📌 SQL QUERY:", Colors.BOLD)
        print_colored(sql_query, Colors.GREEN)
        
        # Save results
        print_colored("\n\n💾 Would you like to save these results to a file? (y/n)", Colors.YELLOW)
        save_choice = input().lower().strip()
        
        if save_choice == 'y':
            save_results(sql_query, validation_result, explanation)
        
        # Continue?
        print_colored("\n\n🔄 Would you like to create another query? (y/n)", Colors.YELLOW)
        continue_choice = input().lower().strip()
        
        if continue_choice != 'y':
            print_colored("\nThank you for using SQL Query Builder Team! 👋", Colors.CYAN)
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\n\nInterrupted by user. Goodbye! 👋", Colors.YELLOW)
        sys.exit(0)