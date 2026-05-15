namespace SkyTeam
{
    /// <summary>
    /// Represents one player's view of the game at a given time.
    /// This is the "Observation" that gets passed to the agent.
    /// </summary>
    public class Observation
    {
        /// <summary>
        /// A deep copy of the public game state (altitude, axis, markers, all placed dice).
        /// </summary>
        public BaseGameState PublicState { get; private set; }

        /// <summary>
        /// The player's private information (i.e., their own un-used dice).
        /// </summary>
        public PlayerState PlayersState { get; private set; }

        /// <summary>
        /// A list of all valid actions this player can take right now.
        /// This is crucial for the agent, especially with complex action spaces.
        /// </summary>
        public List<IAction> ValidActions { get; private set; }

        public Observation(BaseGameState publicState, PlayerState playerState, List<IAction> validActions)
        {
            PublicState = publicState;
            PlayersState = playerState;
            ValidActions = validActions;
        }
    }
}