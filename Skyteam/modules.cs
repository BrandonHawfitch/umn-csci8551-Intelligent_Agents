using System.Text.Json.Serialization;

namespace SkyTeam
{

  public static class GameModules
  {
    /// <summary>
    /// Returns a list of the modules used in the base game.
    /// </summary>
    /// <returns></returns>
    public static List<Module> GetBaseModules()
    {

      List<Position> axis_positions = new List<Position>
        {
          new Position(
            permittedRoles: new List<PlayerRole> { PlayerRole.Pilot },
            allowedDieValues: new List<int> { 1, 2, 3, 4, 5, 6 }
          ),
          new Position(
            permittedRoles: new List<PlayerRole> { PlayerRole.Copilot },
            allowedDieValues: new List<int> { 1, 2, 3, 4, 5, 6 }
          )
        };
      var AxisTiltModule = new Module(
        name: "Axis Tilt",
        positions:axis_positions ,
        effect: (BaseGameState gameState, Position position) =>
        {
          if (axis_positions[0].IsOccupied() && axis_positions[1].IsOccupied())
          {
            int difference = axis_positions[1].PlacedDie!.Value - axis_positions[0].PlacedDie!.Value;
            gameState.AxisTilt += difference;
          }
        },
        mandatory: true
      );

      List<Position> engine_positions = new List<Position>
        {
          new Position(
            permittedRoles: new List<PlayerRole> { PlayerRole.Pilot },
            allowedDieValues: new List<int> { 1, 2, 3, 4, 5, 6 }
          ),
          new Position(
            permittedRoles: new List<PlayerRole> { PlayerRole.Copilot },
            allowedDieValues: new List<int> { 1, 2, 3, 4, 5, 6 }
          )
        };
      var EngineModule = new Module(
        name: "Engine",
        positions: engine_positions,
        effect: (BaseGameState gameState, Position position) =>
        {
          if (engine_positions[0].IsOccupied() && engine_positions[1].IsOccupied())
          {
            int sum = engine_positions[0].PlacedDie!.Value + engine_positions[1].PlacedDie!.Value;
            if (sum < gameState.BlueAeroMarker)
            {
              gameState.ApproachTrack.AdvanceApproach(0); // No movement
            }
            else if (sum < gameState.OrangeAeroMarker)
            {
              gameState.ApproachTrack.AdvanceApproach(1); // Normal movement
            }
            else
            {
              gameState.ApproachTrack.AdvanceApproach(2); // Quick movement
            }
            if (gameState.Altitude == 0) // Set landing speed only when landing
            {
              gameState.LandingSpeed = sum;
            }
          }
        },
        mandatory: true
      );

      var RadioModule = new Module(
        name: "Radio",
        positions: new List<Position>
        {
          new Position(
            permittedRoles: new List<PlayerRole> { PlayerRole.Pilot },
            allowedDieValues: new List<int> { 1, 2, 3, 4, 5, 6 }
          ),
          new Position(
            permittedRoles: new List<PlayerRole> { PlayerRole.Copilot },
            allowedDieValues: new List<int> { 1, 2, 3, 4, 5, 6 }
          ),
          new Position(
            permittedRoles: new List<PlayerRole> { PlayerRole.Copilot },
            allowedDieValues: new List<int> { 1, 2, 3, 4, 5, 6 }
          )
        },
        effect: (BaseGameState gameState, Position position) =>
        {
          var dieValue = position.PlacedDie!.Value;
          gameState.ApproachTrack.ClearPlaneAtDistance(dieValue);
          Console.WriteLine($"Radio Module used to clear plane at distance {dieValue}.");
        },
        mandatory: false
      );

      var LandingGearModule = new Module(
        name: "Landing Gear",
        positions: new List<Position>
        {
          new Position(
            permittedRoles: new List<PlayerRole> { PlayerRole.Pilot },
            allowedDieValues: new List<int> { 1, 2 }
          ),
          new Position(
            permittedRoles: new List<PlayerRole> { PlayerRole.Pilot },
            allowedDieValues: new List<int> { 3, 4 }
          ),
          new Position(
            permittedRoles: new List<PlayerRole> { PlayerRole.Pilot },
            allowedDieValues: new List<int> { 5, 6 }
          )
        },
        effect: (BaseGameState gameState, Position position) =>
        {
          gameState.BlueAeroMarker += 1.0f;
          position.IsComplete = true;
        },
        mandatory: false
      );

      var FlapsModule = new Module(
        name: "Flaps",
        positions: new List<Position>
        {
          new Position(
            permittedRoles: new List<PlayerRole> { PlayerRole.Copilot },
            allowedDieValues: new List<int> { 1, 2 }
          ),
          new Position(
            permittedRoles: new List<PlayerRole> { PlayerRole.Copilot },
            allowedDieValues: new List<int> { 2, 3 }
          ),
          new Position(
            permittedRoles: new List<PlayerRole> { PlayerRole.Copilot },
            allowedDieValues: new List<int> { 4, 5 }
          ),
          new Position(
            permittedRoles: new List<PlayerRole> { PlayerRole.Copilot },
            allowedDieValues: new List<int> { 5, 6 }
          )
        },
        effect: (BaseGameState gameState, Position position) =>
        {
          gameState.OrangeAeroMarker += 1.0f;
          position.IsComplete = true;
        },
        mandatory: false
      );

      var BrakesModule = new Module(
        name: "Brakes",
        positions: new List<Position>
        {
          new Position(
            permittedRoles: new List<PlayerRole> { PlayerRole.Pilot },
            allowedDieValues: new List<int> { 2 }
          ),
          new Position(
            permittedRoles: new List<PlayerRole> { PlayerRole.Pilot },
            allowedDieValues: new List<int> { 4 }
          ),
          new Position(
            permittedRoles: new List<PlayerRole> { PlayerRole.Pilot },
            allowedDieValues: new List<int> { 6 }
          )
        },
        effect: (BaseGameState gameState, Position position) =>
        {
          gameState.RedBrakeMarker += 2.0f;
          position.IsComplete = true;
        },
        mandatory: false
      );

      var ConcentrationModule = new Module(
    name: "Concentration",
    positions: new List<Position>
    {
      new Position(
        permittedRoles: new List<PlayerRole> { PlayerRole.Pilot, PlayerRole.Copilot },
        allowedDieValues: new List<int> { 1, 2, 3, 4, 5, 6 }
      ),
      new Position(
        permittedRoles: new List<PlayerRole> { PlayerRole.Pilot, PlayerRole.Copilot },
        allowedDieValues: new List<int> { 1, 2, 3, 4, 5, 6 }
      ),
      new Position(
        permittedRoles: new List<PlayerRole> { PlayerRole.Pilot, PlayerRole.Copilot },
        allowedDieValues: new List<int> { 1, 2, 3, 4, 5, 6 }
      )
    },
    effect: (BaseGameState gameState, Position position) =>
    {
      // No direct effect on game state; allows rerolling a die
      if (gameState.RerollTokens <= 3)
      {
        gameState.CoffeeTokens += 1;
      }
    },
    mandatory: false
  );
    
      return new List<Module>
      {
        AxisTiltModule,
        EngineModule,
        RadioModule,
        LandingGearModule,
        FlapsModule,
        BrakesModule,
        ConcentrationModule
      };
    }
  }

  /// <summary>
  /// Represents a module in the game, which contains multiple positions for placing dice.
  /// Modules define effects that occur when dice are placed in their positions.
  /// </summary>
  public class Module
  {
    public string Name { get; set; }
    public List<Position> Positions { get; set; }
    [JsonIgnore]
    public Action<BaseGameState, Position> Effect { get; set; }
    public bool Mandatory { get; set; } = false;

    public Module(string name, List<Position> positions, Action<BaseGameState, Position> effect, bool mandatory = false)
    {
      Name = name;
      Positions = positions;
      Effect = effect;
      Mandatory = mandatory;
      foreach (var position in Positions)
      {
        position.Module = this;
      }
    }

    public void DiePlaced(BaseGameState gameState, Position position)
    {
      Console.WriteLine($"Applying {Name} Module effects.");
      Effect(gameState, position);
    }

    public Module Clone()
    {
      var clonedPositions = this.Positions.Select(p => p.Clone()).ToList();
      return new Module(Name, clonedPositions, Effect, Mandatory);
    }

    /// <summary>
    /// Gets the unoccupied positions in this module for a given player role.
    /// </summary>
    /// <param name="role"></param>
    /// <param name="playerDice"></param>
    /// <returns></returns>
    public List<Position> GetUnoccupiedPositions(PlayerRole role)
    {
      var availablePositions = new List<Position>();
      foreach (var position in Positions)
      {
        if (!position.IsOccupied() && position.PermittedRoles.Contains(role))
        {
          availablePositions.Add(position);
        }
      }
      return availablePositions;
    }

    /// <summary>
    /// Gets the positions in this module that are available for placement
    /// Positions are available if they are not occupied, not marked as complete, and permitted for the current player role.
    /// Specific modules may have additional rules for availability.
    /// </summary>
    public List<Position> GetAvailablePositions(PlayerRole role, BaseGameState gameState)
    {
      // Create a list to hold available positions
      List<Position> availablePositions =
      [
        // General case: unoccupied, not complete, permitted roles
        .. Positions.Where(p => !p.IsOccupied() && !p.IsComplete && p.PermittedRoles.Contains(role)).ToList(),
      ];
      
      // Additional rules for specific modules can be added here if needed
      
      // Brakes module: only allow lowest incomplete position to be used
      if (Name == "Brakes")
      {
        availablePositions = availablePositions
          .OrderBy(p => p.AllowedDieValues.Min())
          .Take(1)
          .ToList();
      }

      // Radio Module: only allow positions if there is at least one plane that can be cleared
      if (Name == "Radio")
      {
        bool anyPlaneClearable = Enumerable.Range(1, 6)
          .Any(gameState.ApproachTrack.IsPlaneAtDistance);
        
        if (!anyPlaneClearable)
        {
          return new List<Position>(); // No planes to clear anywhere
        }
      }

      return availablePositions;
    }
  }
}