import os
from datetime import datetime, timedelta
import json
import re

# ============================================
# AGENT 1: Context Collector Agent
# ============================================
class ContextCollectorAgent:
    """
    Responsible for gathering and processing contextual data.
    Does pure data processing - no AI involved.
    """
    
    def collect_context(self, tasks):
        """Main method to collect all context about tasks"""
        current_time = datetime.now()
        current_hour = current_time.hour
        
        context = {
            'current_datetime': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'time_of_day': self._classify_time(current_hour),
            'available_hours_today': self._calculate_available_hours(current_hour),
            'tasks_with_urgency': []
        }
        
        for idx, task in enumerate(tasks):
            task_context = {
                'id': idx + 1,
                'name': task['name'],
                'deadline': task['deadline'],
                'estimate': task['estimate'],
                'urgency_score': self._calculate_urgency(task, current_time),
                'days_until_deadline': self._days_remaining(task, current_time),
                'can_finish_today': task['estimate'] <= context['available_hours_today']
            }
            context['tasks_with_urgency'].append(task_context)
        
        print(f"\n🔵 Agent 1 (Context Collector) - Processing complete!")
        print(f"   → Current time: {context['time_of_day']}")
        print(f"   → Available hours today: {context['available_hours_today']}")
        print(f"   → Analyzed {len(tasks)} tasks")
        
        return context
    
    def _classify_time(self, hour):
        """Classify time of day for energy levels"""
        if 6 <= hour < 12:
            return "morning (high energy)"
        elif 12 <= hour < 17:
            return "afternoon (moderate energy)"
        elif 17 <= hour < 23:
            return "evening (low energy)"
        else:
            return "night (rest time)"
    
    def _calculate_available_hours(self, current_hour):
        """Calculate remaining productive hours today"""
        end_of_workday = 22  # 10 PM
        if current_hour >= end_of_workday:
            return 0
        return end_of_workday - current_hour
    
    def _calculate_urgency(self, task, current_time):
        """Calculate urgency score (0-100)"""
        days = self._days_remaining(task, current_time)
        if days < 0:
            return 100  # Overdue
        elif days == 0:
            return 95   # Due today
        else:
            # Urgency decreases as days increase
            return max(10, 100 / (days + 1))
    
    def _days_remaining(self, task, current_time):
        """Calculate days until deadline"""
        deadline = datetime.strptime(task['deadline'], '%Y-%m-%d')
        delta = deadline - current_time
        return delta.days + (delta.seconds / 86400)  # Include partial days


# ============================================
# AGENT 2: Prioritization Agent
# ============================================
class PrioritizationAgent:
    """
    Uses AI to make intelligent prioritization decisions.
    Takes structured context and returns ranked tasks with reasoning.
    """
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            print("⚠️  Warning: No API key found. Using fallback mode.")
            self.use_fallback = True
        else:
            self.use_fallback = False
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except ImportError:
                print("⚠️  Warning: openai package not installed. Using fallback mode.")
                print("   Install with: pip install openai")
                self.use_fallback = True
    
    def prioritize_tasks(self, context_data):
        """Main method to prioritize tasks using AI"""
        print(f"\n🟠 Agent 2 (Prioritization Agent) - Analyzing...")
        
        if self.use_fallback:
            return self._fallback_prioritization(context_data)
        
        prompt = self._build_prompt(context_data)
        
        try:
            response = self._call_llm(prompt)
            prioritized_tasks = self._parse_response(response)
            print(f"   → AI prioritization complete!")
            return prioritized_tasks
        except Exception as e:
            print(f"   → API error: {e}")
            print(f"   → Using fallback prioritization")
            return self._fallback_prioritization(context_data)
    
    def _build_prompt(self, context):
        """Build intelligent prompt for LLM"""
        prompt = f"""You are a task prioritization expert. Analyze these tasks and prioritize them intelligently.

CURRENT CONTEXT:
- Time: {context['time_of_day']}
- Available hours today: {context['available_hours_today']}
- Current date/time: {context['current_datetime']}

TASKS TO PRIORITIZE:
"""
        
        for task in context['tasks_with_urgency']:
            prompt += f"""
Task #{task['id']}: {task['name']}
- Deadline: {task['deadline']} ({task['days_until_deadline']:.1f} days away)
- Time needed: {task['estimate']} hours
- Urgency score: {task['urgency_score']:.1f}/100
- Can finish today: {task['can_finish_today']}
"""
        
        prompt += """
Prioritize these tasks (1 = highest priority) considering:
1. Deadline urgency (closer deadlines = higher priority)
2. Available time vs. task duration (can you finish it today?)
3. Time of day and energy levels
4. Quick wins vs. long tasks

IMPORTANT: Return ONLY a JSON array in this exact format, nothing else:
[
  {"rank": 1, "task_id": 1, "task": "task name", "reason": "why this priority", "do_today": true},
  {"rank": 2, "task_id": 2, "task": "task name", "reason": "why this priority", "do_today": false}
]
"""
        return prompt
    
    def _call_llm(self, prompt):
        """Call OpenAI API"""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",  # or "gpt-4o" for better quality
            messages=[
                {"role": "system", "content": "You are a task prioritization expert. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    
    def _parse_response(self, response):
        """Extract JSON from LLM response"""
        # Try to find JSON array in response
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            tasks = json.loads(json_match.group())
            return tasks
        raise ValueError("Could not parse JSON from response")
    
    def _fallback_prioritization(self, context):
        """Fallback prioritization without AI (pure urgency-based)"""
        tasks = context['tasks_with_urgency']
        
        # Sort by urgency score
        sorted_tasks = sorted(tasks, key=lambda x: x['urgency_score'], reverse=True)
        
        prioritized = []
        for rank, task in enumerate(sorted_tasks, 1):
            prioritized.append({
                'rank': rank,
                'task_id': task['id'],
                'task': task['name'],
                'reason': f"Urgency score: {task['urgency_score']:.1f}/100",
                'do_today': task['can_finish_today'] and task['urgency_score'] > 50
            })
        
        return prioritized


# ============================================
# COORDINATOR: Manages the workflow
# ============================================
class TaskPrioritizerCoordinator:
    """
    Coordinates between agents and handles user interaction.
    """
    
    def __init__(self):
        self.tasks = []
        self.context_agent = ContextCollectorAgent()
        self.priority_agent = PrioritizationAgent()
    
    def run(self):
        """Main application loop"""
        print("=" * 60)
        print("   🎯 PERSONAL TASK PRIORITIZER - Two Agent System")
        print("=" * 60)
        
        while True:
            self._show_menu()
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == '1':
                self._add_task()
            elif choice == '2':
                self._prioritize_tasks()
            elif choice == '3':
                self._mark_complete()
            elif choice == '4':
                self._view_all_tasks()
            elif choice == '5':
                print("\n👋 Goodbye! Stay productive!")
                break
            else:
                print("❌ Invalid choice. Please try again.")
    
    def _show_menu(self):
        """Display main menu"""
        print("\n" + "=" * 60)
        print("MAIN MENU")
        print("=" * 60)
        print("1. ➕ Add Tasks")
        print("2. 🎯 Prioritize Tasks (Run Agents)")
        print("3. ✅ Mark Task Complete")
        print("4. 📋 View All Tasks")
        print("5. 🚪 Exit")
    
    def _add_task(self):
        """Add new task through terminal prompts"""
        print("\n" + "-" * 60)
        print("ADD NEW TASK")
        print("-" * 60)
        
        name = input("Task name: ").strip()
        if not name:
            print("❌ Task name cannot be empty!")
            return
        
        deadline = input("Deadline (YYYY-MM-DD): ").strip()
        try:
            datetime.strptime(deadline, '%Y-%m-%d')
        except ValueError:
            print("❌ Invalid date format! Use YYYY-MM-DD")
            return
        
        try:
            estimate = float(input("Estimated hours needed: ").strip())
            if estimate <= 0:
                raise ValueError
        except ValueError:
            print("❌ Please enter a valid positive number!")
            return
        
        task = {
            'name': name,
            'deadline': deadline,
            'estimate': estimate
        }
        
        self.tasks.append(task)
        print(f"\n✅ Task added successfully! Total tasks: {len(self.tasks)}")
    
    def _prioritize_tasks(self):
        """Run both agents to prioritize tasks"""
        if not self.tasks:
            print("\n❌ No tasks added yet! Add some tasks first.")
            return
        
        print("\n" + "=" * 60)
        print("RUNNING TWO-AGENT PRIORITIZATION SYSTEM")
        print("=" * 60)
        
        # Step 1: Agent 1 collects context
        context = self.context_agent.collect_context(self.tasks)
        
        # Step 2: Agent 2 prioritizes with AI
        prioritized = self.priority_agent.prioritize_tasks(context)
        
        # Step 3: Display results
        self._display_prioritized_tasks(prioritized, context)
    
    def _display_prioritized_tasks(self, prioritized, context):
        """Display prioritized tasks with color coding"""
        print("\n" + "=" * 60)
        print("📊 PRIORITIZED TASK LIST")
        print("=" * 60)
        print(f"Context: {context['time_of_day']}, {context['available_hours_today']}h available\n")
        
        for item in prioritized:
            rank = item['rank']
            task = item['task']
            reason = item['reason']
            do_today = item['do_today']
            
            # Color coding
            if rank == 1:
                priority_label = "🔴 URGENT"
            elif rank == 2:
                priority_label = "🟡 HIGH"
            elif do_today:
                priority_label = "🟢 MEDIUM"
            else:
                priority_label = "⚪ LOW"
            
            today_marker = "⏰ DO TODAY" if do_today else "📅 Can defer"
            
            print(f"{priority_label} | Rank #{rank}")
            print(f"   Task: {task}")
            print(f"   Reason: {reason}")
            print(f"   {today_marker}")
            print()
    
    def _mark_complete(self):
        """Mark a task as complete"""
        if not self.tasks:
            print("\n❌ No tasks to complete!")
            return
        
        print("\n" + "-" * 60)
        print("MARK TASK COMPLETE")
        print("-" * 60)
        
        for idx, task in enumerate(self.tasks, 1):
            print(f"{idx}. {task['name']} (Due: {task['deadline']})")
        
        try:
            choice = int(input("\nEnter task number to complete: ").strip())
            if 1 <= choice <= len(self.tasks):
                completed_task = self.tasks.pop(choice - 1)
                print(f"\n✅ Completed: {completed_task['name']}")
                print(f"   Remaining tasks: {len(self.tasks)}")
            else:
                print("❌ Invalid task number!")
        except ValueError:
            print("❌ Please enter a valid number!")
    
    def _view_all_tasks(self):
        """View all tasks in memory"""
        if not self.tasks:
            print("\n❌ No tasks added yet!")
            return
        
        print("\n" + "=" * 60)
        print(f"📋 ALL TASKS ({len(self.tasks)} total)")
        print("=" * 60)
        
        for idx, task in enumerate(self.tasks, 1):
            print(f"{idx}. {task['name']}")
            print(f"   Deadline: {task['deadline']}")
            print(f"   Estimate: {task['estimate']} hours")
            print()


# ============================================
# MAIN ENTRY POINT
# ============================================
if __name__ == "__main__":
    # Set your API key as environment variable or pass it directly
    # export OPENAI_API_KEY="your-key-here"
    
    coordinator = TaskPrioritizerCoordinator()
    coordinator.run()