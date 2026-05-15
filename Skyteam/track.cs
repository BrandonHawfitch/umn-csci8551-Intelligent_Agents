namespace SkyTeam
{
  public static class GameTracks
  {
    public static TrackState MontrealTrudeauTrack()
    {
      int trackLength = 7;
      List<int> planesOnApproach = new List<int> { 0, 0, 1, 2, 1, 3, 2 };
      return new TrackState(trackLength, planesOnApproach);
    }
  }

  /// <summary>
  /// TrackState: Represents the state of the approach track, including planes on approach
  /// </summary>
  public class TrackState
  {
    public int TrackLength { get; set; }
    public int ApproachIndex { get; set; } = 0;
    public List<int> PlanesOnApproach { get; set; } // Numbers of planes on the approach track, indexed by location

    public TrackState(int trackLength, List<int> planesOnApproach)
    {
      TrackLength = trackLength;
      PlanesOnApproach = planesOnApproach;
    }

    public int distanceToRunway()
    {
      return TrackLength - ApproachIndex - 1;
    }

    public bool IsAtRunway()
    {
      return distanceToRunway() == 0;
    }

    public bool IsBeyondRunway()
    {
      return distanceToRunway() < 0;
    }

    public bool PlaneCollision()
    {
      // Clamp the check to the track length to prevent out-of-bounds errors if we overshoot
      int limit = ApproachIndex < TrackLength ? ApproachIndex : TrackLength;
      for (int i = 0; i < limit; i++)
      {
        if (PlanesOnApproach[i] > 0)
        {
          return true;
        }
      }
      return false;
    }

    public void AdvanceApproach(int steps)
    {
      ApproachIndex += steps;
    }

    public void ClearPlaneAtDistance(int distance)
    {
      int index = ApproachIndex + distance - 1;
      if (index >= TrackLength)
      {
        index = TrackLength - 1;
      }

      if (PlanesOnApproach[index] <= 0)
      {
        throw new InvalidOperationException("No planes to clear at the specified distance.");
      }

      PlanesOnApproach[index] -= 1;
    }

    public bool IsPlaneAtDistance(int distance)
    {
      int index = ApproachIndex + distance - 1;
      if (index >= TrackLength)
      {
        index = TrackLength - 1;
      }
      return PlanesOnApproach[index] > 0;
    }

    public TrackState Clone()
    {
      return new TrackState(TrackLength, new List<int>(PlanesOnApproach))
      {
        ApproachIndex = this.ApproachIndex
      };
    }
  }
}