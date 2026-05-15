import csv
import datetime
import argparse
from collections import Counter

from analyzer import SimulationAnalyzer
from autopilot import SkyTeamAgent


# --- REPORTING UTILS ---
def save_summary_report(results, timestamp):
    total = len(results)
    if total == 0: return

    wins = [r for r in results if r.outcome == "WIN"]
    losses = [r for r in results if r.outcome == "LOSS"]
    
    # Build the summary text
    summary_lines = []
    summary_lines.append("="*60)
    summary_lines.append(f"SIMULATION SUMMARY REPORT ({total} Runs)")
    summary_lines.append("="*60)
    
    # 1. High Level
    win_rate = (len(wins) / total) * 100
    summary_lines.append(f"Strategy:      {results[0].strategy}")
    summary_lines.append(f"Total Games:   {total}")
    summary_lines.append(f"Wins:          {len(wins)} ({win_rate:.1f}%)")
    summary_lines.append(f"Losses:        {len(losses)}")
    summary_lines.append("-" * 60)

    # 2. Loss Analysis
    if losses:
        summary_lines.append("FAILURE ANALYSIS (Distribution of Causes):")
        causes = Counter(r.cause for r in losses)
        for cause, count in causes.most_common():
            pct = (count / len(losses)) * 100
            summary_lines.append(f"  - {cause:<30} : {count:>3} ({pct:>5.1f}% of losses)")
        summary_lines.append("-" * 60)

    # 3. Altitude Distribution
    summary_lines.append("TERMINAL ALTITUDE DISTRIBUTION:")
    alts = Counter(r.final_altitude for r in results)
    for alt in sorted(alts.keys(), reverse=True):
        count = alts[alt]
        bar = "#" * int((count/total)*20)
        summary_lines.append(f"  Alt {alt}: {count:>3} {bar}")
    summary_lines.append("="*60)
    
    # Print to console
    print("\n" + "\n".join(summary_lines) + "\n")
    
    # Save to log file
    log_path = f"logs/simulation_{timestamp}_summary.txt"
    
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))
    
    print(f"Summary report saved to: {log_path}")

def save_csv_report(results, timestamp):
    csv_filename = f"logs/simulation_{timestamp}_results.csv"
    keys = results[0].to_dict().keys()
    
    try:
        with open(csv_filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for r in results:
                writer.writerow(r.to_dict())
        print(f"Detailed CSV report saved to: {csv_filename}")
        
    except Exception as e:
        print(f"Failed to save CSV: {e}")

# --- CONFIGURATION ---
DEFAULT_API_URL = "http://localhost:5155"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sky Team Autopilot Agent")
    parser.add_argument('--url', type=str, default=DEFAULT_API_URL, help="URL of the C# Simulator")
    parser.add_argument('--strategy', type=str, default="random", choices=["random", "entropy", "heuristic"], help="Action selection strategy")
    parser.add_argument("--no-log", action="store_true", help="Disable game logging")
    parser.add_argument('--runs', type=int, default=1, help="Number of games to run (default: 1)")
    
    args = parser.parse_args()

    agent = SkyTeamAgent(args.url, args.strategy, not args.no_log)
    
    # Create shared timestamp for all runs
    shared_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    all_results = []
    
    try:
        for i in range(1, args.runs + 1):
            result = agent.run_game(run_number=i, shared_timestamp=shared_ts)
            all_results.append(result)
            
            # Simple progress ticker
            print(f"Result: {result.outcome} ({result.cause})")
            
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user.")
    
    if all_results and args.runs > 1:
        save_csv_report(all_results, shared_ts)
        save_summary_report(all_results, shared_ts)
        # SimulationAnalyzer.save_summary(all_results, f"summary_{shared_ts}")