namespace SkyTeam
{
  public class Scenario
  {
    public string Name { get; set; }
    public int? Seed { get; set; } = 1234;
    public List<ScenarioStep> Steps { get; set; } = new List<ScenarioStep>();

    public static void RunScenario(GameSimulator simulator, Scenario scenario)
    {
      foreach (var step in scenario.Steps)
      {
        Console.WriteLine($"Executing Step: {step.Description}");
        var position = simulator.CompleteGameState.BaseState.GetModuleByName(step.ModuleName).Positions[step.PositionIndex];
        var action = new PlaceDieAction(step.Role, step.Die, position);
        var stepResult = simulator.PlayAction(step.Role, step.ModuleName, step.Die.Value, step.PositionIndex);
        step.PostStepAssert?.Invoke(simulator, stepResult);
      }
    }
  }

  public class ScenarioStep
  {
    public String Description { get; set; } = "";
    public PlayerRole Role { get; set; }
    public string ModuleName { get; set; }
    public Die Die { get; set; }
    public int PositionIndex { get; set; } = 0;

    public Action<GameSimulator, MDPStepResult> PostStepAssert { get; set; }

    public ScenarioStep(PlayerRole role, string moduleName, Die die, int positionIndex)
    {
      Role = role;
      ModuleName = moduleName;
      Die = die;
      PositionIndex = positionIndex;
    }
  }
}