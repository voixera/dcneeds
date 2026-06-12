const { matchStatus } = require("../config/worldcup");
const { readDb } = require("../database/jsonDb");
const { normalizeText } = require("../utils/format");

function sortByKickoffAsc(a, b) {
  return new Date(a.kickoff).getTime() - new Date(b.kickoff).getTime();
}

function sortByKickoffDesc(a, b) {
  return new Date(b.kickoff).getTime() - new Date(a.kickoff).getTime();
}

function sortStandings(a, b) {
  const goalDifferenceA = a.goalsFor - a.goalsAgainst;
  const goalDifferenceB = b.goalsFor - b.goalsAgainst;

  return (
    b.points - a.points ||
    goalDifferenceB - goalDifferenceA ||
    b.goalsFor - a.goalsFor ||
    a.teamId.localeCompare(b.teamId)
  );
}

function teamMatchesQuery(team, query) {
  const normalized = normalizeText(query);
  const searchValues = [
    team.id,
    team.name,
    team.fifaCode,
    ...(team.aliases || []),
  ];

  return searchValues.some((value) => normalizeText(value).includes(normalized));
}

function teamMatchesExactQuery(team, query) {
  const normalized = normalizeText(query);
  const searchValues = [
    team.id,
    team.name,
    team.fifaCode,
    ...(team.aliases || []),
  ];

  return searchValues.some((value) => normalizeText(value) === normalized);
}

function teamMatchesFilter(db, teamQuery) {
  if (!teamQuery) return () => true;

  const matchingTeamIds = db.teams
    .filter((team) => teamMatchesQuery(team, teamQuery))
    .map((team) => team.id);

  return (match) =>
    matchingTeamIds.includes(match.homeTeamId) ||
    matchingTeamIds.includes(match.awayTeamId);
}

function getUpcomingMatches({ team, limit = 10 } = {}) {
  const db = readDb();
  const filterByTeam = teamMatchesFilter(db, team);

  const matches = db.matches
    .filter((match) => match.status !== matchStatus.finished)
    .filter(filterByTeam)
    .sort(sortByKickoffAsc)
    .slice(0, limit);

  return { db, matches };
}

function getLatestResults({ team, limit = 10 } = {}) {
  const db = readDb();
  const filterByTeam = teamMatchesFilter(db, team);

  const matches = db.matches
    .filter((match) => match.status === matchStatus.finished)
    .filter(filterByTeam)
    .sort(sortByKickoffDesc)
    .slice(0, limit);

  return { db, matches };
}

function getStandings(group) {
  const db = readDb();
  const normalizedGroup = group ? normalizeText(group).toUpperCase() : null;
  const rows = db.standings
    .filter((row) => !normalizedGroup || row.group.toUpperCase() === normalizedGroup)
    .sort(sortStandings);

  return { db, rows };
}

function getGroupedStandings() {
  const db = readDb();
  const groups = [...new Set(db.standings.map((row) => row.group))].sort();

  return {
    db,
    groups: groups.map((group) => ({
      group,
      rows: db.standings
        .filter((row) => row.group === group)
        .sort(sortStandings),
    })),
  };
}

function findTeam(query) {
  const db = readDb();
  const team = db.teams.find((item) => teamMatchesExactQuery(item, query));

  if (team) return { db, team };

  return {
    db,
    team: db.teams.find((item) => teamMatchesQuery(item, query)),
  };
}

function searchTeams(query, limit = 25) {
  const db = readDb();
  const normalized = normalizeText(query);

  return db.teams
    .filter((team) => {
      if (!normalized) return true;

      return teamMatchesQuery(team, query);
    })
    .slice(0, limit);
}

function findMatchById(matchId) {
  const db = readDb();
  const match = db.matches.find(
    (item) => normalizeText(item.id) === normalizeText(matchId),
  );

  return { db, match };
}

function getPredictionOpenMatches(limit = 25) {
  const db = readDb();
  const now = Date.now();

  return {
    db,
    matches: db.matches
      .filter((match) => {
        return (
          match.status === matchStatus.scheduled &&
          new Date(match.kickoff).getTime() > now
        );
      })
      .sort(sortByKickoffAsc)
      .slice(0, limit),
  };
}

function getMatchesStartingSoon(lookaheadMinutes) {
  const db = readDb();
  const now = Date.now();
  const until = now + lookaheadMinutes * 60 * 1000;

  return {
    db,
    matches: db.matches
      .filter((match) => {
        const kickoff = new Date(match.kickoff).getTime();

        return (
          match.status === matchStatus.scheduled &&
          kickoff > now &&
          kickoff <= until
        );
      })
      .sort(sortByKickoffAsc),
  };
}

function getFinishedMatches() {
  const db = readDb();

  return {
    db,
    matches: db.matches
      .filter((match) => match.status === matchStatus.finished)
      .sort(sortByKickoffDesc),
  };
}

module.exports = {
  findMatchById,
  findTeam,
  getFinishedMatches,
  getGroupedStandings,
  getLatestResults,
  getMatchesStartingSoon,
  getPredictionOpenMatches,
  getStandings,
  getUpcomingMatches,
  searchTeams,
};
