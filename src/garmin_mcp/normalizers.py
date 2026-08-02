from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def _walk(value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key), child
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def pick(data: Any, *keys: str, default: Any = None) -> Any:
    wanted = {key.casefold() for key in keys}
    for key, value in _walk(data):
        if key.casefold() in wanted and value is not None:
            return value
    return default


def number(value: Any) -> float | int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        result = float(value)
        return int(result) if result.is_integer() else result
    except (TypeError, ValueError):
        return None


def normalize_daily(date: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    """Reduce Garmin responses to an allowlisted daily athletics schema."""

    stats = raw.get("stats", {})
    sleep = raw.get("sleep", {})
    heart_rate = raw.get("heart_rate", {})
    stress = raw.get("stress", {})
    body_battery = raw.get("body_battery", {})
    hrv = raw.get("hrv", {})
    readiness = raw.get("training_readiness", {})
    hrv_available = isinstance(hrv, Mapping) and hrv.get("availability") != "unavailable"
    readiness_available = (
        isinstance(readiness, (Mapping, list))
        and not (isinstance(readiness, Mapping) and readiness.get("availability") == "unavailable")
        and bool(readiness)
    )
    return {
        "date": date,
        "steps": number(pick(stats, "totalSteps", "steps")),
        "distance_m": number(pick(stats, "totalDistanceMeters", "distanceInMeters")),
        "calories_total": number(pick(stats, "totalKilocalories", "totalCalories")),
        "calories_active": number(pick(stats, "activeKilocalories", "activeCalories")),
        "intensity_minutes": number(
            pick(stats, "intensityMinutes", "moderateIntensityMinutes")
        ),
        "resting_heart_rate": number(pick(stats, "restingHeartRate")),
        "heart_rate_min": number(pick(heart_rate, "minHeartRate", "minHr")),
        "heart_rate_max": number(pick(heart_rate, "maxHeartRate", "maxHr")),
        "stress_average": number(pick(stress, "averageStressLevel", "avgStressLevel")),
        "body_battery_high": number(
            pick(body_battery, "charged", "bodyBatteryHighestValue")
        ),
        "body_battery_low": number(
            pick(body_battery, "drained", "bodyBatteryLowestValue")
        ),
        "sleep_seconds": number(pick(sleep, "sleepTimeSeconds", "totalSleepSeconds")),
        "deep_sleep_seconds": number(pick(sleep, "deepSleepSeconds")),
        "light_sleep_seconds": number(pick(sleep, "lightSleepSeconds")),
        "rem_sleep_seconds": number(pick(sleep, "remSleepSeconds")),
        "awake_seconds": number(pick(sleep, "awakeSleepSeconds", "awakeSeconds")),
        "sleep_score": number(pick(sleep, "overallScore", "sleepScore", "value")),
        "respiration_average": number(
            pick(stats, "avgWakingRespirationValue", "avgRespiration")
        ),
        "hrv_status": pick(hrv, "hrvStatus", "status") if hrv_available else None,
        "hrv_last_night_average": number(
            pick(hrv, "lastNightAvg", "lastNightAverage")
        )
        if hrv_available
        else None,
        "training_readiness": number(
            pick(readiness, "score", "trainingReadinessScore")
        )
        if readiness_available
        else None,
        "metric_availability": {
            "hrv_status": "available" if hrv_available else "unsupported_or_no_data",
            "training_readiness": (
                "available" if readiness_available else "unsupported_or_no_data"
            ),
        },
        "source_device": "Garmin Forerunner 55",
    }


def normalize_activity(raw: Mapping[str, Any]) -> dict[str, Any]:
    activity_id = pick(raw, "activityId", "activity_id", "id")
    return {
        "activity_id": str(activity_id) if activity_id is not None else None,
        "name": pick(raw, "activityName", "activityNameOriginal", "name"),
        "sport": pick(raw, "typeKey", "sportTypeKey", "sport"),
        "start_time_local": pick(raw, "startTimeLocal", "startTimeGMT", "startTime"),
        "duration_seconds": number(pick(raw, "duration", "durationSeconds", "elapsedDuration")),
        "moving_seconds": number(pick(raw, "movingDuration", "movingTime")),
        "distance_m": number(pick(raw, "distance", "distanceMeters")),
        "calories": number(pick(raw, "calories")),
        "average_heart_rate": number(pick(raw, "averageHR", "averageHeartRate")),
        "max_heart_rate": number(pick(raw, "maxHR", "maxHeartRate")),
        "average_pace_seconds_per_km": number(pick(raw, "averagePace", "avgPace")),
        "average_speed_mps": number(pick(raw, "averageSpeed")),
        "max_speed_mps": number(pick(raw, "maxSpeed")),
        "average_cadence": number(
            pick(raw, "averageRunningCadenceInStepsPerMinute", "averageCadence")
        ),
        "elevation_gain_m": number(pick(raw, "elevationGain", "totalElevationGain")),
        "aerobic_training_effect": number(pick(raw, "aerobicTrainingEffect")),
        "anaerobic_training_effect": number(pick(raw, "anaerobicTrainingEffect")),
        "vo2_max": number(pick(raw, "vO2MaxValue", "vo2MaxValue", "vo2Max")),
    }


def normalize_performance(date: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    max_metrics = raw.get("max_metrics", {})
    training_status = raw.get("training_status", {})
    fitness_age = raw.get("fitness_age", {})
    race_predictions = raw.get("race_predictions", {})
    return {
        "date": date,
        "running_vo2_max": number(
            pick(max_metrics, "vO2MaxPreciseValue", "vo2MaxValue", "vo2Max")
        ),
        "fitness_age": number(pick(fitness_age, "fitnessAge")),
        "training_status": pick(
            training_status, "trainingStatus", "trainingStatusPhrase", "status"
        ),
        "training_load": number(
            pick(training_status, "weeklyTrainingLoad", "trainingLoad")
        ),
        "recovery_time_hours": number(
            pick(training_status, "recoveryTime", "recoveryTimeHours")
        ),
        "race_5k_seconds": number(pick(race_predictions, "time5K", "raceTime5k")),
        "race_10k_seconds": number(pick(race_predictions, "time10K", "raceTime10k")),
        "race_half_marathon_seconds": number(
            pick(race_predictions, "timeHalfMarathon", "raceTimeHalf")
        ),
        "race_marathon_seconds": number(
            pick(race_predictions, "timeMarathon", "raceTimeMarathon")
        ),
    }


def normalize_splits(raw: Any) -> list[dict[str, Any]]:
    candidates = pick(raw, "lapDTOs", "splits", default=[])
    if not isinstance(candidates, list):
        return []
    result = []
    for index, item in enumerate(candidates, start=1):
        if not isinstance(item, Mapping):
            continue
        result.append(
            {
                "lap": number(pick(item, "lapIndex", "lapNumber")) or index,
                "start_time": pick(item, "startTimeLocal", "startTimeGMT", "startTime"),
                "distance_m": number(pick(item, "distance", "distanceMeters")),
                "duration_seconds": number(pick(item, "duration", "elapsedDuration")),
                "moving_seconds": number(pick(item, "movingDuration", "movingTime")),
                "average_heart_rate": number(pick(item, "averageHR", "averageHeartRate")),
                "max_heart_rate": number(pick(item, "maxHR", "maxHeartRate")),
                "average_pace_seconds_per_km": number(pick(item, "averagePace", "avgPace")),
                "average_cadence": number(
                    pick(item, "averageRunningCadenceInStepsPerMinute", "averageCadence")
                ),
                "elevation_gain_m": number(pick(item, "elevationGain")),
            }
        )
    return result


def normalize_zones(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, (Mapping, list)):
        return []
    candidates = raw if isinstance(raw, list) else pick(raw, "zones", default=[])
    if not isinstance(candidates, list):
        return []
    result = []
    for index, item in enumerate(candidates, start=1):
        if not isinstance(item, Mapping):
            continue
        result.append(
            {
                "zone": number(pick(item, "zoneNumber", "zone")) or index,
                "seconds": number(pick(item, "secsInZone", "seconds", "duration")),
                "min_value": number(pick(item, "zoneLowBoundary", "minimum")),
                "max_value": number(pick(item, "zoneHighBoundary", "maximum")),
            }
        )
    return result


def normalize_weather(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping) or raw.get("availability") == "unavailable":
        return None
    return {
        "condition": pick(raw, "weatherTypeDTO", "weatherType", "condition"),
        "temperature_c": number(pick(raw, "temp", "temperature")),
        "apparent_temperature_c": number(pick(raw, "apparentTemp", "feelsLike")),
        "humidity_percent": number(pick(raw, "relativeHumidity", "humidity")),
        "wind_speed": number(pick(raw, "windSpeed")),
    }


def normalize_gear(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    return [
        {
            "gear_id": str(pick(item, "gearPk", "uuid", "id")),
            "name": pick(item, "displayName", "gearName", "name"),
            "model": pick(item, "modelName", "model"),
        }
        for item in raw
        if isinstance(item, Mapping)
    ]

