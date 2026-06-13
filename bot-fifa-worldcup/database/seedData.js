const teamsByGroup = {
  A: [
    {
      id: "mexico",
      name: "Mexico",
      fifaCode: "MEX",
      federation: "CONCACAF",
      aliases: ["Meksiko"],
      description: "Tuan rumah bersama World Cup 2026 dan unggulan Grup A.",
    },
    {
      id: "south-africa",
      name: "South Africa",
      fifaCode: "RSA",
      federation: "CAF",
      aliases: ["Afrika Selatan"],
      description: "Wakil CAF di Grup A.",
    },
    {
      id: "korea-republic",
      name: "Korea Republic",
      fifaCode: "KOR",
      federation: "AFC",
      aliases: ["South Korea", "Korea Selatan"],
      description: "Wakil AFC di Grup A.",
    },
    {
      id: "czechia",
      name: "Czechia",
      fifaCode: "CZE",
      federation: "UEFA",
      aliases: ["Czech Republic", "Republik Ceko"],
      description: "Wakil UEFA di Grup A.",
    },
  ],
  B: [
    {
      id: "canada",
      name: "Canada",
      fifaCode: "CAN",
      federation: "CONCACAF",
      aliases: ["Kanada"],
      description: "Tuan rumah bersama World Cup 2026 dan peserta Grup B.",
    },
    {
      id: "bosnia-and-herzegovina",
      name: "Bosnia and Herzegovina",
      fifaCode: "BIH",
      federation: "UEFA",
      aliases: ["Bosnia", "Bosnia Herzegovina"],
      description: "Wakil UEFA di Grup B.",
    },
    {
      id: "qatar",
      name: "Qatar",
      fifaCode: "QAT",
      federation: "AFC",
      aliases: [],
      description: "Wakil AFC di Grup B.",
    },
    {
      id: "switzerland",
      name: "Switzerland",
      fifaCode: "SUI",
      federation: "UEFA",
      aliases: ["Swiss"],
      description: "Wakil UEFA di Grup B.",
    },
  ],
  C: [
    {
      id: "brazil",
      name: "Brazil",
      fifaCode: "BRA",
      federation: "CONMEBOL",
      aliases: ["Brasil"],
      description: "Wakil CONMEBOL dan salah satu favorit turnamen.",
    },
    {
      id: "morocco",
      name: "Morocco",
      fifaCode: "MAR",
      federation: "CAF",
      aliases: ["Maroko"],
      description: "Wakil CAF di Grup C.",
    },
    {
      id: "haiti",
      name: "Haiti",
      fifaCode: "HAI",
      federation: "CONCACAF",
      aliases: [],
      description: "Wakil CONCACAF di Grup C.",
    },
    {
      id: "scotland",
      name: "Scotland",
      fifaCode: "SCO",
      federation: "UEFA",
      aliases: ["Skotlandia"],
      description: "Wakil UEFA di Grup C.",
    },
  ],
  D: [
    {
      id: "united-states",
      name: "United States",
      fifaCode: "USA",
      federation: "CONCACAF",
      aliases: ["USA", "USMNT", "Amerika Serikat"],
      description: "Tuan rumah bersama World Cup 2026 dan peserta Grup D.",
    },
    {
      id: "paraguay",
      name: "Paraguay",
      fifaCode: "PAR",
      federation: "CONMEBOL",
      aliases: [],
      description: "Wakil CONMEBOL di Grup D.",
    },
    {
      id: "australia",
      name: "Australia",
      fifaCode: "AUS",
      federation: "AFC",
      aliases: [],
      description: "Wakil AFC di Grup D.",
    },
    {
      id: "turkiye",
      name: "Turkiye",
      fifaCode: "TUR",
      federation: "UEFA",
      aliases: ["Turkey", "Turki", "Turkiye"],
      description: "Wakil UEFA di Grup D.",
    },
  ],
  E: [
    {
      id: "germany",
      name: "Germany",
      fifaCode: "GER",
      federation: "UEFA",
      aliases: ["Jerman"],
      description: "Wakil UEFA dan juara dunia empat kali.",
    },
    {
      id: "curacao",
      name: "Curacao",
      fifaCode: "CUW",
      federation: "CONCACAF",
      aliases: ["Curacao"],
      description: "Wakil CONCACAF di Grup E.",
    },
    {
      id: "ivory-coast",
      name: "Ivory Coast",
      fifaCode: "CIV",
      federation: "CAF",
      aliases: ["Cote d'Ivoire", "Pantai Gading"],
      description: "Wakil CAF di Grup E.",
    },
    {
      id: "ecuador",
      name: "Ecuador",
      fifaCode: "ECU",
      federation: "CONMEBOL",
      aliases: [],
      description: "Wakil CONMEBOL di Grup E.",
    },
  ],
  F: [
    {
      id: "netherlands",
      name: "Netherlands",
      fifaCode: "NED",
      federation: "UEFA",
      aliases: ["Belanda", "Holland"],
      description: "Wakil UEFA di Grup F.",
    },
    {
      id: "japan",
      name: "Japan",
      fifaCode: "JPN",
      federation: "AFC",
      aliases: ["Jepang"],
      description: "Wakil AFC di Grup F.",
    },
    {
      id: "sweden",
      name: "Sweden",
      fifaCode: "SWE",
      federation: "UEFA",
      aliases: ["Swedia"],
      description: "Wakil UEFA di Grup F.",
    },
    {
      id: "tunisia",
      name: "Tunisia",
      fifaCode: "TUN",
      federation: "CAF",
      aliases: [],
      description: "Wakil CAF di Grup F.",
    },
  ],
  G: [
    {
      id: "belgium",
      name: "Belgium",
      fifaCode: "BEL",
      federation: "UEFA",
      aliases: ["Belgia"],
      description: "Wakil UEFA di Grup G.",
    },
    {
      id: "egypt",
      name: "Egypt",
      fifaCode: "EGY",
      federation: "CAF",
      aliases: ["Mesir"],
      description: "Wakil CAF di Grup G.",
    },
    {
      id: "ir-iran",
      name: "IR Iran",
      fifaCode: "IRN",
      federation: "AFC",
      aliases: ["Iran"],
      description: "Wakil AFC di Grup G.",
    },
    {
      id: "new-zealand",
      name: "New Zealand",
      fifaCode: "NZL",
      federation: "OFC",
      aliases: ["Selandia Baru"],
      description: "Wakil OFC di Grup G.",
    },
  ],
  H: [
    {
      id: "spain",
      name: "Spain",
      fifaCode: "ESP",
      federation: "UEFA",
      aliases: ["Spanyol"],
      description: "Wakil UEFA dan salah satu unggulan Grup H.",
    },
    {
      id: "cabo-verde",
      name: "Cabo Verde",
      fifaCode: "CPV",
      federation: "CAF",
      aliases: ["Cape Verde"],
      description: "Wakil CAF di Grup H.",
    },
    {
      id: "saudi-arabia",
      name: "Saudi Arabia",
      fifaCode: "KSA",
      federation: "AFC",
      aliases: ["Arab Saudi"],
      description: "Wakil AFC di Grup H.",
    },
    {
      id: "uruguay",
      name: "Uruguay",
      fifaCode: "URU",
      federation: "CONMEBOL",
      aliases: [],
      description: "Wakil CONMEBOL di Grup H.",
    },
  ],
  I: [
    {
      id: "france",
      name: "France",
      fifaCode: "FRA",
      federation: "UEFA",
      aliases: ["Prancis"],
      description: "Wakil UEFA dan juara dunia dua kali.",
    },
    {
      id: "senegal",
      name: "Senegal",
      fifaCode: "SEN",
      federation: "CAF",
      aliases: [],
      description: "Wakil CAF di Grup I.",
    },
    {
      id: "iraq",
      name: "Iraq",
      fifaCode: "IRQ",
      federation: "AFC",
      aliases: ["Irak"],
      description: "Wakil AFC di Grup I.",
    },
    {
      id: "norway",
      name: "Norway",
      fifaCode: "NOR",
      federation: "UEFA",
      aliases: ["Norwegia"],
      description: "Wakil UEFA di Grup I.",
    },
  ],
  J: [
    {
      id: "argentina",
      name: "Argentina",
      fifaCode: "ARG",
      federation: "CONMEBOL",
      aliases: [],
      description: "Juara bertahan World Cup dan unggulan Grup J.",
    },
    {
      id: "algeria",
      name: "Algeria",
      fifaCode: "ALG",
      federation: "CAF",
      aliases: ["Aljazair"],
      description: "Wakil CAF di Grup J.",
    },
    {
      id: "austria",
      name: "Austria",
      fifaCode: "AUT",
      federation: "UEFA",
      aliases: [],
      description: "Wakil UEFA di Grup J.",
    },
    {
      id: "jordan",
      name: "Jordan",
      fifaCode: "JOR",
      federation: "AFC",
      aliases: ["Yordania"],
      description: "Wakil AFC di Grup J.",
    },
  ],
  K: [
    {
      id: "portugal",
      name: "Portugal",
      fifaCode: "POR",
      federation: "UEFA",
      aliases: [],
      description: "Wakil UEFA dan unggulan Grup K.",
    },
    {
      id: "dr-congo",
      name: "DR Congo",
      fifaCode: "COD",
      federation: "CAF",
      aliases: ["Congo DR", "DRC", "Congo", "RD Kongo"],
      description: "Wakil CAF di Grup K.",
    },
    {
      id: "uzbekistan",
      name: "Uzbekistan",
      fifaCode: "UZB",
      federation: "AFC",
      aliases: [],
      description: "Wakil AFC di Grup K.",
    },
    {
      id: "colombia",
      name: "Colombia",
      fifaCode: "COL",
      federation: "CONMEBOL",
      aliases: ["Kolombia"],
      description: "Wakil CONMEBOL di Grup K.",
    },
  ],
  L: [
    {
      id: "england",
      name: "England",
      fifaCode: "ENG",
      federation: "UEFA",
      aliases: ["Inggris"],
      description: "Wakil UEFA dan unggulan Grup L.",
    },
    {
      id: "croatia",
      name: "Croatia",
      fifaCode: "CRO",
      federation: "UEFA",
      aliases: ["Kroasia"],
      description: "Wakil UEFA di Grup L.",
    },
    {
      id: "ghana",
      name: "Ghana",
      fifaCode: "GHA",
      federation: "CAF",
      aliases: [],
      description: "Wakil CAF di Grup L.",
    },
    {
      id: "panama",
      name: "Panama",
      fifaCode: "PAN",
      federation: "CONCACAF",
      aliases: [],
      description: "Wakil CONCACAF di Grup L.",
    },
  ],
};

const teams = Object.entries(teamsByGroup).flatMap(([group, groupTeams]) =>
  groupTeams.map((team) => ({
    group,
    coach: `Pelatih ${team.name}`,
    captain: `Kapten ${team.name}`,
    ...team,
  })),
);

const groupByTeamId = Object.fromEntries(
  teams.map((team) => [team.id, team.group]),
);

const fixtures = [
  ["mexico", "south-africa", "2026-06-11T19:00:00.000Z", "Mexico City Stadium", 2, 0],
  ["korea-republic", "czechia", "2026-06-12T02:00:00.000Z", "Estadio Guadalajara", 2, 1],
  ["canada", "bosnia-and-herzegovina", "2026-06-12T19:00:00.000Z", "Toronto Stadium", 1, 1],
  ["united-states", "paraguay", "2026-06-13T01:00:00.000Z", "Los Angeles Stadium"],
  ["qatar", "switzerland", "2026-06-13T19:00:00.000Z", "San Francisco Bay Area Stadium"],
  ["brazil", "morocco", "2026-06-13T22:00:00.000Z", "New York New Jersey Stadium"],
  ["haiti", "scotland", "2026-06-14T01:00:00.000Z", "Boston Stadium"],
  ["australia", "turkiye", "2026-06-14T04:00:00.000Z", "BC Place"],
  ["germany", "curacao", "2026-06-14T17:00:00.000Z", "Houston Stadium"],
  ["netherlands", "japan", "2026-06-14T20:00:00.000Z", "Dallas Stadium"],
  ["ivory-coast", "ecuador", "2026-06-14T23:00:00.000Z", "Philadelphia Stadium"],
  ["sweden", "tunisia", "2026-06-15T02:00:00.000Z", "Estadio Monterrey"],
  ["spain", "cabo-verde", "2026-06-15T16:00:00.000Z", "Atlanta Stadium"],
  ["belgium", "egypt", "2026-06-15T19:00:00.000Z", "BC Place"],
  ["saudi-arabia", "uruguay", "2026-06-15T22:00:00.000Z", "Miami Stadium"],
  ["ir-iran", "new-zealand", "2026-06-16T01:00:00.000Z", "Los Angeles Stadium"],
  ["france", "senegal", "2026-06-16T19:00:00.000Z", "New York New Jersey Stadium"],
  ["iraq", "norway", "2026-06-16T22:00:00.000Z", "Boston Stadium"],
  ["argentina", "algeria", "2026-06-17T01:00:00.000Z", "Kansas City Stadium"],
  ["austria", "jordan", "2026-06-17T04:00:00.000Z", "San Francisco Bay Area Stadium"],
  ["portugal", "dr-congo", "2026-06-17T17:00:00.000Z", "Houston Stadium"],
  ["england", "croatia", "2026-06-17T20:00:00.000Z", "Dallas Stadium"],
  ["ghana", "panama", "2026-06-17T23:00:00.000Z", "Toronto Stadium"],
  ["uzbekistan", "colombia", "2026-06-18T02:00:00.000Z", "Mexico City Stadium"],
  ["czechia", "south-africa", "2026-06-18T16:00:00.000Z", "Atlanta Stadium"],
  ["switzerland", "bosnia-and-herzegovina", "2026-06-18T19:00:00.000Z", "Los Angeles Stadium"],
  ["canada", "qatar", "2026-06-18T22:00:00.000Z", "BC Place"],
  ["mexico", "korea-republic", "2026-06-19T01:00:00.000Z", "Estadio Guadalajara"],
  ["united-states", "australia", "2026-06-19T19:00:00.000Z", "Seattle Stadium"],
  ["scotland", "morocco", "2026-06-19T22:00:00.000Z", "Boston Stadium"],
  ["brazil", "haiti", "2026-06-20T00:30:00.000Z", "Philadelphia Stadium"],
  ["turkiye", "paraguay", "2026-06-20T03:00:00.000Z", "San Francisco Bay Area Stadium"],
  ["netherlands", "sweden", "2026-06-20T17:00:00.000Z", "Houston Stadium"],
  ["germany", "ivory-coast", "2026-06-20T20:00:00.000Z", "Toronto Stadium"],
  ["ecuador", "curacao", "2026-06-21T03:00:00.000Z", "Kansas City Stadium"],
  ["tunisia", "japan", "2026-06-21T04:00:00.000Z", "Estadio Monterrey"],
  ["spain", "saudi-arabia", "2026-06-21T16:00:00.000Z", "Atlanta Stadium"],
  ["belgium", "ir-iran", "2026-06-21T19:00:00.000Z", "Los Angeles Stadium"],
  ["uruguay", "cabo-verde", "2026-06-21T22:00:00.000Z", "Miami Stadium"],
  ["new-zealand", "egypt", "2026-06-22T01:00:00.000Z", "BC Place"],
  ["argentina", "austria", "2026-06-22T17:00:00.000Z", "Dallas Stadium"],
  ["france", "iraq", "2026-06-22T21:00:00.000Z", "Philadelphia Stadium"],
  ["norway", "senegal", "2026-06-23T00:00:00.000Z", "New York New Jersey Stadium"],
  ["jordan", "algeria", "2026-06-23T03:00:00.000Z", "San Francisco Bay Area Stadium"],
  ["portugal", "uzbekistan", "2026-06-23T17:00:00.000Z", "Houston Stadium"],
  ["england", "ghana", "2026-06-23T20:00:00.000Z", "Boston Stadium"],
  ["panama", "croatia", "2026-06-23T23:00:00.000Z", "Toronto Stadium"],
  ["colombia", "dr-congo", "2026-06-24T02:00:00.000Z", "Estadio Guadalajara"],
  ["switzerland", "canada", "2026-06-24T19:00:00.000Z", "BC Place"],
  ["bosnia-and-herzegovina", "qatar", "2026-06-24T19:00:00.000Z", "Seattle Stadium"],
  ["scotland", "brazil", "2026-06-24T22:00:00.000Z", "Miami Stadium"],
  ["morocco", "haiti", "2026-06-24T22:00:00.000Z", "Atlanta Stadium"],
  ["czechia", "mexico", "2026-06-25T01:00:00.000Z", "Mexico City Stadium"],
  ["south-africa", "korea-republic", "2026-06-25T01:00:00.000Z", "Estadio Monterrey"],
  ["ecuador", "germany", "2026-06-25T20:00:00.000Z", "New York New Jersey Stadium"],
  ["curacao", "ivory-coast", "2026-06-25T20:00:00.000Z", "Philadelphia Stadium"],
  ["japan", "sweden", "2026-06-25T23:00:00.000Z", "Dallas Stadium"],
  ["tunisia", "netherlands", "2026-06-25T23:00:00.000Z", "Kansas City Stadium"],
  ["turkiye", "united-states", "2026-06-26T02:00:00.000Z", "Los Angeles Stadium"],
  ["paraguay", "australia", "2026-06-26T02:00:00.000Z", "San Francisco Bay Area Stadium"],
  ["norway", "france", "2026-06-26T19:00:00.000Z", "Boston Stadium"],
  ["senegal", "iraq", "2026-06-26T19:00:00.000Z", "Toronto Stadium"],
  ["cabo-verde", "saudi-arabia", "2026-06-27T00:00:00.000Z", "Houston Stadium"],
  ["uruguay", "spain", "2026-06-27T00:00:00.000Z", "Estadio Guadalajara"],
  ["egypt", "ir-iran", "2026-06-27T03:00:00.000Z", "Seattle Stadium"],
  ["new-zealand", "belgium", "2026-06-27T03:00:00.000Z", "BC Place"],
  ["panama", "england", "2026-06-27T21:00:00.000Z", "New York New Jersey Stadium"],
  ["croatia", "ghana", "2026-06-27T21:00:00.000Z", "Philadelphia Stadium"],
  ["colombia", "portugal", "2026-06-27T23:30:00.000Z", "Miami Stadium"],
  ["dr-congo", "uzbekistan", "2026-06-27T23:30:00.000Z", "Atlanta Stadium"],
  ["algeria", "austria", "2026-06-28T02:00:00.000Z", "Kansas City Stadium"],
  ["jordan", "argentina", "2026-06-28T02:00:00.000Z", "Dallas Stadium"],
];

function getOutcome(homeScore, awayScore) {
  if (homeScore > awayScore) return "home";
  if (homeScore < awayScore) return "away";
  return "draw";
}

function buildMatches() {
  return fixtures.map((fixture, index) => {
    const [homeTeamId, awayTeamId, kickoff, venue, homeScore, awayScore] = fixture;
    const isFinished = Number.isInteger(homeScore) && Number.isInteger(awayScore);

    return {
      id: `M${String(index + 1).padStart(3, "0")}`,
      stage: "Group Stage",
      group: groupByTeamId[homeTeamId],
      homeTeamId,
      awayTeamId,
      kickoff,
      venue,
      status: isFinished ? "finished" : "scheduled",
      homeScore: isFinished ? homeScore : null,
      awayScore: isFinished ? awayScore : null,
    };
  });
}

function buildStandings(matches) {
  const standingsByTeam = new Map(
    teams.map((team) => [
      team.id,
      {
        group: team.group,
        teamId: team.id,
        played: 0,
        won: 0,
        drawn: 0,
        lost: 0,
        goalsFor: 0,
        goalsAgainst: 0,
        points: 0,
      },
    ]),
  );

  for (const match of matches) {
    if (match.status !== "finished") continue;

    const home = standingsByTeam.get(match.homeTeamId);
    const away = standingsByTeam.get(match.awayTeamId);
    const outcome = getOutcome(match.homeScore, match.awayScore);

    home.played += 1;
    away.played += 1;
    home.goalsFor += match.homeScore;
    home.goalsAgainst += match.awayScore;
    away.goalsFor += match.awayScore;
    away.goalsAgainst += match.homeScore;

    if (outcome === "home") {
      home.won += 1;
      home.points += 3;
      away.lost += 1;
    } else if (outcome === "away") {
      away.won += 1;
      away.points += 3;
      home.lost += 1;
    } else {
      home.drawn += 1;
      away.drawn += 1;
      home.points += 1;
      away.points += 1;
    }
  }

  return [...standingsByTeam.values()];
}

const matches = buildMatches();

module.exports = {
  metadata: {
    source: "local-seed",
    version: "2026-world-cup-full-groups-2026-06-13",
    note: "Data peserta dan jadwal fase grup World Cup 2026. Hasil dapat diperbarui di database/db.json atau FIFA_DB_PATH.",
  },
  teams,
  matches,
  standings: buildStandings(matches),
  predictions: [],
  notificationLog: {
    matchReminders: [],
    resultNotifications: [],
  },
  notificationChannels: {},
};
