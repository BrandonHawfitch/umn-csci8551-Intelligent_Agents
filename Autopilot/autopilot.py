
import requests
from analyzer import GameResult, SimulationAnalyzer
from gamelogger import GameLogger
from strategies import StrategyFactory, BeliefTracker
import sys
import importlib

# Force reload of strategies module
if 'strategies' in sys.modules:
    importlib.reload(sys.modules['strategies'])
else:
    import strategies


# --- CORE COMPONENTS ---
class SkyTeamClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()

    def reset(self):
        try:
            resp = self.session.post(f"{self.base_url}/reset")
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError:
            print(f"CRITICAL ERROR: Could not connect to Simulator at {self.base_url}")
            print("Make sure the C# application is running (dotnet run)!")
            exit(1)

    def step(self, action_index):
        resp = self.session.post(f"{self.base_url}/step?actionIndex={action_index}")
        resp.raise_for_status()
        return resp.json()

class SkyTeamAgent:
    def __init__(self, api_url, strategy_name="random", logging_enabled=True):
        self.client = SkyTeamClient(api_url)
        self.strategy_name = strategy_name
        self.strategy = StrategyFactory.create(strategy_name)
        self.belief_tracker = None
        self.role = None
        self.logger = None
        self.logging_enabled = logging_enabled

    def run_game(self, run_number=1, shared_timestamp=None):
        print(f"--- Connecting to Simulator... ---")
        obs = self.client.reset()
        
        self.role = obs['playersState']['role']
        partner_role = "Copilot" if self.role == "Pilot" else "Pilot"
        self.belief_tracker = BeliefTracker(partner_role)
        
        # Initialize Logger
        # Tag includes strategy and role for easier data analysis later
        # If multiple runs, also include run number and shared timestamp
        if self.logging_enabled:
            self.logger = GameLogger(
                run_tag=f"{self.strategy_name}_{self.role}",
                run_number=run_number,
                shared_timestamp=shared_timestamp
            )
            self.logger.log_initial_state(obs)

        print(f"--- Game Started. I am {self.role}. Strategy: {self.strategy_name.upper()} ---")

        action_history = []
        step_count = 0
        done = False
        score = 0

        while not done:
            step_count += 1
            valid_actions = obs['validActions']
            
            if not valid_actions:
                print("No valid actions available. Ending.")
                break

            # 1. Update Beliefs
            self.belief_tracker.update(action_history, obs['publicState'])
            
            # 2. Select Action based on Strategy
            action_index = self.strategy.select_action(valid_actions, obs, self.belief_tracker) 
            
            # 3. Execute
            selected_action = valid_actions[action_index]
            print(f"[RUN {run_number}] Step {step_count} ({self.strategy_name}): Selected {self._format_action_name(selected_action)}")
            
            action_history.append(selected_action)
            result = self.client.step(action_index)
            
            # 4. Log Step
            if self.logging_enabled:
                self.logger.log_step(step_count, selected_action, result)

            # 5. Handle Result
            obs = result['observation']
            done = result['isDone']
            score += result['reward']
            if done:
                print(f"[RUN {run_number}] --- Game Over. Reward: {result['reward']} ---")
        
        if self.logging_enabled:
            self.logger.close()
        # return score
        
        # Analyze Result
        public_state = obs.get('publicState', {})
        outcome, cause = SimulationAnalyzer.analyze_end_state(public_state, score)
        altitude = public_state.get('altitude', 0)
        
        return GameResult(
            run_id=run_number,
            strategy=self.strategy_name,
            outcome=outcome,
            cause=cause,
            final_altitude=altitude,
            reward=score
        )
    
    def _format_action_name(self, action):
        # Helper to make logs readable
        # Tries to parse the C# Type name or looks for module name
        raw_type = action.get('$type', 'UnknownAction')
        # Simple string cleaning if needed
        return raw_type.split('.')[-1] 
