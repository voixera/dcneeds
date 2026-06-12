function formatDateTime(isoDate, timezone) {
  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: timezone,
  }).format(new Date(isoDate));
}

function formatScore(match) {
  if (match.homeScore === null || match.awayScore === null) {
    return "vs";
  }

  return `${match.homeScore} - ${match.awayScore}`;
}

function getTeam(db, teamId) {
  return db.teams.find((team) => team.id === teamId);
}

function getTeamName(db, teamId) {
  return getTeam(db, teamId)?.name || teamId;
}

function formatMatchTitle(db, match) {
  return `${getTeamName(db, match.homeTeamId)} ${formatScore(match)} ${getTeamName(
    db,
    match.awayTeamId,
  )}`;
}

function formatMatchLine(db, match, timezone) {
  const title = formatMatchTitle(db, match);
  const kickoff = formatDateTime(match.kickoff, timezone);
  const group = match.group ? `Grup ${match.group}` : match.stage;

  return `**${match.id}** | ${title}\n${group} - ${kickoff}\n${match.venue}`;
}

function normalizeText(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
}

function truncate(value, maxLength = 100) {
  const text = String(value);
  if (text.length <= maxLength) return text;

  return `${text.slice(0, maxLength - 3)}...`;
}

function getOutcome(homeScore, awayScore) {
  if (homeScore > awayScore) return "home";
  if (homeScore < awayScore) return "away";
  return "draw";
}

function formatStandingsTable(db, rows) {
  const header = "Tim              M  M  S  K  GM-GK  P";
  const lines = rows.map((row) => {
    const teamName = truncate(getTeamName(db, row.teamId), 15).padEnd(15, " ");
    const goals = `${row.goalsFor}-${row.goalsAgainst}`.padEnd(6, " ");

    return `${teamName} ${String(row.played).padStart(2, " ")} ${String(
      row.won,
    ).padStart(2, " ")} ${String(row.drawn).padStart(2, " ")} ${String(
      row.lost,
    ).padStart(2, " ")} ${goals} ${String(row.points).padStart(2, " ")}`;
  });

  return [header, ...lines].join("\n");
}

module.exports = {
  formatDateTime,
  formatMatchLine,
  formatMatchTitle,
  formatScore,
  formatStandingsTable,
  getOutcome,
  getTeam,
  getTeamName,
  normalizeText,
  truncate,
};
