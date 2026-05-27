"""Seasonality Detection for time-series analysis."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SeasonalityDetector:
    """Detects and analyzes seasonal patterns in time-series data."""

    def __init__(self):
        """Initialize seasonality detector."""
        self.detected_patterns = {}

    def detect_seasonality(self, values: List[float], min_period: int = 6) -> Dict[str, Any]:
        """
        Detect seasonal patterns using autocorrelation and spectral analysis.

        Args:
            values: Time series values
            min_period: Minimum period to consider as seasonal

        Returns:
            Dict with seasonality detection results
        """
        if len(values) < min_period * 2:
            return {"is_seasonal": False, "reason": "Insufficient data"}

        try:
            # Calculate autocorrelation at different lags
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)

            acf_scores = {}
            # Focus on periods 6-24 for seasonal analysis (typical business cycles)
            for lag in range(min_period, min(len(values) // 2, 25)):
                c0 = sum((values[i] - mean) * (values[i + lag] - mean) for i in range(len(values) - lag))
                acf = c0 / (variance * (len(values) - lag)) if variance > 0 else 0
                acf_scores[lag] = abs(acf)

            # Find dominant period (highest autocorrelation in seasonal range)
            # Prefer 12, 6, 24 as they represent common seasonal periods
            preferred_periods = [12, 6, 24]
            strongest_period = None
            strongest_acf = 0.0

            for period in preferred_periods:
                if period in acf_scores and acf_scores[period] > strongest_acf:
                    strongest_period = period
                    strongest_acf = acf_scores[period]

            # If no preferred period found, use overall strongest
            if strongest_period is None and acf_scores:
                strongest_period = max(acf_scores, key=acf_scores.get)
                strongest_acf = acf_scores[strongest_period]

            if strongest_period is not None:
                # Seasonality threshold: ACF > 0.25 indicates seasonality
                is_seasonal = strongest_acf > 0.25

                return {
                    "is_seasonal": is_seasonal,
                    "seasonal_period": strongest_period,
                    "strength": round(strongest_acf, 2),
                    "acf_scores": {k: round(v, 3) for k, v in acf_scores.items()},
                }

            return {"is_seasonal": False, "strength": 0}

        except Exception as e:
            logger.error(f"Error detecting seasonality: {e}")
            return {"is_seasonal": False}

    def decompose(self, values: List[float], period: int = 12) -> Dict[str, List[float]]:
        """
        Decompose time series into trend, seasonal, and residual components (STL method).

        Args:
            values: Time series values
            period: Seasonal period (default 12 for monthly)

        Returns:
            Dict with trend, seasonal, residual components
        """
        if len(values) < period * 2:
            logger.warning(f"Insufficient data for decomposition ({len(values)} < {period * 2})")
            return {"trend": values, "seasonal": [0] * len(values), "residual": [0] * len(values)}

        try:
            # Simple moving average for trend
            trend = []
            for i in range(len(values)):
                window_start = max(0, i - period // 2)
                window_end = min(len(values), i + period // 2 + 1)
                trend_val = sum(values[window_start:window_end]) / (window_end - window_start)
                trend.append(trend_val)

            # Detrended series
            detrended = [values[i] - trend[i] for i in range(len(values))]

            # Seasonal component: average of each season
            seasonal = [0] * len(values)
            for season_idx in range(period):
                season_values = [detrended[i] for i in range(season_idx, len(values), period)]
                if season_values:
                    seasonal_avg = sum(season_values) / len(season_values)
                    for i in range(season_idx, len(values), period):
                        seasonal[i] = seasonal_avg

            # Residual
            residual = [values[i] - trend[i] - seasonal[i] for i in range(len(values))]

            return {
                "trend": [round(t, 2) for t in trend],
                "seasonal": [round(s, 2) for s in seasonal],
                "residual": [round(r, 2) for r in residual],
            }

        except Exception as e:
            logger.error(f"Error decomposing series: {e}")
            return {"trend": values, "seasonal": [0] * len(values), "residual": [0] * len(values)}

    def identify_peaks(self, values: List[float], period: int = 12) -> Dict[str, Any]:
        """
        Identify peak and trough seasons.

        Args:
            values: Time series values
            period: Seasonal period

        Returns:
            Dict with peak/trough months and ratio
        """
        if len(values) < period:
            return {"peak_months": [], "trough_months": []}

        try:
            # Calculate average for each season
            season_avgs = {}
            for season_idx in range(period):
                season_values = [values[i] for i in range(season_idx, len(values), period)]
                if season_values:
                    season_avgs[season_idx] = sum(season_values) / len(season_values)

            if not season_avgs:
                return {"peak_months": [], "trough_months": []}

            # Find peaks and troughs
            max_val = max(season_avgs.values())
            min_val = min(season_avgs.values())
            peak_threshold = min_val + (max_val - min_val) * 0.7  # Top 30%
            trough_threshold = min_val + (max_val - min_val) * 0.3  # Bottom 30%

            peak_months = [m for m, v in season_avgs.items() if v >= peak_threshold]
            trough_months = [m for m, v in season_avgs.items() if v <= trough_threshold]

            ratio = (max_val / min_val) if min_val > 0 else 1.0

            return {
                "peak_months": sorted(peak_months),
                "trough_months": sorted(trough_months),
                "peak_to_trough_ratio": round(ratio, 2),
                "season_averages": {k: round(v, 2) for k, v in season_avgs.items()},
            }

        except Exception as e:
            logger.error(f"Error identifying peaks: {e}")
            return {"peak_months": [], "trough_months": []}

    def calculate_seasonality_strength(self, values: List[float], period: int = 12) -> float:
        """
        Calculate strength of seasonality (0-1 scale).

        Formula: 1 - (Var(residual) / Var(seasonal + residual))

        Args:
            values: Time series values
            period: Seasonal period

        Returns:
            Seasonality strength (0-1)
        """
        if len(values) < period:
            return 0.0

        try:
            decomposed = self.decompose(values, period)
            seasonal = decomposed["seasonal"]
            residual = decomposed["residual"]

            # Convert strings to floats if needed
            seasonal = [float(s) for s in seasonal]
            residual = [float(r) for r in residual]

            var_residual = sum(r**2 for r in residual) / len(residual)
            var_seasonal_residual = sum((seasonal[i] + residual[i]) ** 2 for i in range(len(residual))) / len(
                residual
            )

            if var_seasonal_residual == 0:
                return 0.0

            strength = 1 - (var_residual / var_seasonal_residual)
            return round(max(0.0, min(1.0, strength)), 2)

        except Exception as e:
            logger.error(f"Error calculating seasonality strength: {e}")
            return 0.0

    def get_seasonal_indices(self, values: List[float], period: int = 12) -> Dict[int, float]:
        """
        Get seasonal indices (multiplicative factors) for each season.

        Args:
            values: Time series values
            period: Seasonal period

        Returns:
            Dict mapping season to multiplicative index
        """
        if len(values) < period:
            return {}

        try:
            mean = sum(values) / len(values)

            # Calculate average for each season
            season_avgs = {}
            for season_idx in range(period):
                season_values = [values[i] for i in range(season_idx, len(values), period)]
                if season_values:
                    season_avgs[season_idx] = sum(season_values) / len(season_values)

            # Convert to indices (relative to mean)
            indices = {}
            for season_idx, avg in season_avgs.items():
                index = (avg / mean) if mean > 0 else 1.0
                indices[season_idx] = round(index, 3)

            return indices

        except Exception as e:
            logger.error(f"Error calculating seasonal indices: {e}")
            return {}

    def get_seasonality_summary(self, values: List[float]) -> Dict[str, Any]:
        """Get comprehensive seasonality summary."""
        detection = self.detect_seasonality(values)

        if not detection.get("is_seasonal"):
            return {"is_seasonal": False}

        period = detection.get("seasonal_period", 12)

        return {
            "is_seasonal": True,
            "period": period,
            "strength": detection.get("strength", 0),
            "peaks": self.identify_peaks(values, period),
            "strength_ratio": self.calculate_seasonality_strength(values, period),
            "seasonal_indices": self.get_seasonal_indices(values, period),
        }
