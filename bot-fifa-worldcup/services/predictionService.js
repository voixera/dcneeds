const { predictionPoints, matchStatus } = require("../config/worldcup");
const { readDb, updateDb } = require("../database/jsonDb");
const { getOutcome } = require("../utils/format");

function calculatePredictionPoints(prediction, match) {
  if (
    match.status !== matchStatus.finished ||
    match.homeScore === null ||
    match.awayScore === null
  ) {
    return 0;
  }

  if (
    prediction.homeScore === match.homeScore &&
    prediction.awayScore === match.awayScore
  ) {
    return predictionPoints.exactScore;
  }

  let points = 0;
  const predictedOutcome = getOutcome(prediction.homeScore, prediction.awayScore);
  const actualOutcome = getOutcome(match.homeScore, match.awayScore);
  const predictedDifference = prediction.homeScore - prediction.awayScore;
  const actualDifference = match.homeScore - match.awayScore;

  if (predictedOutcome === actualOutcome) {
    points += predictionPoints.correctOutcome;
  }

  if (predictedDifference === actualDifference) {
    points += predictionPoints.correctGoalDifferenceBonus;
  }

  return points;
}

function assertPredictionScore(score, label) {
  if (!Number.isInteger(score) || score < 0 || score > 20) {
    throw new Error(`${label} harus berupa angka 0 sampai 20.`);
  }
}

function savePrediction({ userId, username, matchId, homeScore, awayScore }) {
  assertPredictionScore(homeScore, "Skor tuan rumah");
  assertPredictionScore(awayScore, "Skor tamu");

  return updateDb((db) => {
    const match = db.matches.find((item) => item.id.toLowerCase() === matchId.toLowerCase());

    if (!match) {
      throw new Error(`Match ID ${matchId} tidak ditemukan.`);
    }

    if (match.status !== matchStatus.scheduled) {
      throw new Error("Prediksi hanya bisa dibuat untuk pertandingan yang belum selesai.");
    }

    if (new Date(match.kickoff).getTime() <= Date.now()) {
      throw new Error("Prediksi sudah ditutup karena kickoff pertandingan sudah lewat.");
    }

    const existing = db.predictions.find(
      (prediction) =>
        prediction.userId === userId &&
        prediction.matchId.toLowerCase() === match.id.toLowerCase(),
    );

    if (existing) {
      existing.username = username;
      existing.homeScore = homeScore;
      existing.awayScore = awayScore;
      existing.updatedAt = new Date().toISOString();
      existing.points = calculatePredictionPoints(existing, match);

      return { prediction: existing, match, created: false };
    }

    const prediction = {
      id: `${userId}:${match.id}`,
      userId,
      username,
      matchId: match.id,
      homeScore,
      awayScore,
      points: 0,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    db.predictions.push(prediction);

    return { prediction, match, created: true };
  });
}

function recalculateAllPredictions(db) {
  for (const prediction of db.predictions) {
    const match = db.matches.find((item) => item.id === prediction.matchId);
    if (!match) continue;

    prediction.points = calculatePredictionPoints(prediction, match);
  }
}

function getLeaderboard(limit = 10) {
  return updateDb((db) => {
    recalculateAllPredictions(db);

    const scores = new Map();

    for (const prediction of db.predictions) {
      const current = scores.get(prediction.userId) || {
        userId: prediction.userId,
        username: prediction.username,
        points: 0,
        predictions: 0,
      };

      current.username = prediction.username || current.username;
      current.points += prediction.points;
      current.predictions += 1;
      scores.set(prediction.userId, current);
    }

    return [...scores.values()]
      .sort((a, b) => b.points - a.points || b.predictions - a.predictions)
      .slice(0, limit);
  });
}

function getUserPredictions(userId) {
  const db = readDb();

  return db.predictions.filter((prediction) => prediction.userId === userId);
}

module.exports = {
  calculatePredictionPoints,
  getLeaderboard,
  getUserPredictions,
  recalculateAllPredictions,
  savePrediction,
};
