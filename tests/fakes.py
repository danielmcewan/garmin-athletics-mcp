from __future__ import annotations


class FakeGarminAdapter:
    def __init__(self) -> None:
        self.daily_calls = 0
        self.performance_calls = 0
        self.activity_calls = 0
        self.detail_calls = 0
        self.fail = False

    def fetch_daily(self, day: str) -> dict:
        self.daily_calls += 1
        if self.fail:
            raise RuntimeError("upstream offline")
        return {
            "stats": {
                "totalSteps": 12345,
                "totalDistanceMeters": 9876,
                "totalKilocalories": 2400,
                "activeKilocalories": 650,
                "restingHeartRate": 49,
            },
            "sleep": {
                "dailySleepDTO": {
                    "sleepTimeSeconds": 28800,
                    "deepSleepSeconds": 5400,
                    "lightSleepSeconds": 16200,
                    "remSleepSeconds": 5400,
                    "sleepScores": {"overall": {"value": 82}},
                }
            },
            "heart_rate": {"minHeartRate": 45, "maxHeartRate": 181},
            "stress": {"averageStressLevel": 24},
            "body_battery": [{"charged": 78, "drained": 22}],
            "hrv": {"hrvSummary": None},
            "training_readiness": [],
        }

    def fetch_performance(self, day: str) -> dict:
        self.performance_calls += 1
        if self.fail:
            raise RuntimeError("upstream offline")
        return {
            "max_metrics": {"generic": {"vo2MaxValue": 52}},
            "training_status": {"trainingStatusPhrase": "PRODUCTIVE", "trainingLoad": 410},
            "fitness_age": {"fitnessAge": 31},
            "race_predictions": {"time5K": 1260, "time10K": 2700},
        }

    def fetch_activities(self, start: str, end: str) -> list[dict]:
        self.activity_calls += 1
        if self.fail:
            raise RuntimeError("upstream offline")
        return [
            {
                "activityId": 1002,
                "activityName": "Recent Run",
                "activityType": {"typeKey": "running"},
                "startTimeLocal": f"{end} 07:00:00",
                "duration": 1800,
                "distance": 5000,
                "averageHR": 155,
                "averagePace": 360,
                "elevationGain": 42,
            },
            {
                "activityId": 1001,
                "activityName": "Earlier Run",
                "activityType": {"typeKey": "running"},
                "startTimeLocal": f"{start} 07:00:00",
                "duration": 1860,
                "distance": 5000,
                "averageHR": 158,
                "averagePace": 372,
                "elevationGain": 40,
            },
        ]

    def fetch_activity_details(self, activity_id: str) -> dict:
        self.detail_calls += 1
        if self.fail:
            raise RuntimeError("upstream offline")
        return {
            "details": {
                "activityId": int(activity_id),
                "activityName": "Recent Run",
                "activityType": {"typeKey": "running"},
                "geoPolylineDTO": {
                    "polyline": [
                        {"lat": -27.47, "lon": 153.02, "elevation": 12.1},
                        {"lat": -27.471, "lon": 153.021, "elevation": 13.0},
                    ]
                },
            },
            "splits": {"lapDTOs": [{"distance": 1000, "duration": 360}]},
            "typed_splits": {},
            "heart_rate_zones": {"zone1": 30},
            "power_zones": {"availability": "unavailable"},
            "weather": {"temperature": 22},
            "gear": [],
        }

