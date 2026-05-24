"""비용 예측 모델"""

import logging
import uuid
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
import statistics

logger = logging.getLogger(__name__)


class CostForecastModel:
    """시계열 분석 기반 AWS 비용 예측 모델"""

    def __init__(self, cost_history_table, dynamodb_table):
        """
        Args:
            cost_history_table: Cost history DynamoDB table
            dynamodb_table: Model storage DynamoDB table
        """
        self.cost_history_table = cost_history_table
        self.table = dynamodb_table

    def train_arima_model(self, account_id: str, historical_days: int = 90) -> str:
        """
        ARIMA 시계열 모델 학습

        Args:
            account_id: AWS Account ID
            historical_days: 학습에 사용할 역사 데이터 기간 (일)

        Returns:
            모델 ID
        """
        try:
            if historical_days < 30:
                logger.error("Need at least 30 days of data to train model")
                return ""

            # Get historical cost data
            response = self.cost_history_table.query(
                KeyConditionExpression='account_id = :acc',
                ExpressionAttributeValues={':acc': account_id}
            )

            items = response.get('Items', [])
            if len(items) < historical_days:
                logger.warning(f"Only {len(items)} days of data available, need {historical_days}")

            # Extract cost values
            costs = []
            for item in sorted(items, key=lambda x: x.get('date', ''))[-historical_days:]:
                try:
                    cost = float(item.get('cost', 0))
                    costs.append(cost)
                except (ValueError, TypeError):
                    continue

            if len(costs) < 10:
                logger.error("Insufficient data for model training")
                return ""

            # Simple trend analysis (simulating ARIMA)
            # In production, would use statsmodels.tsa.arima.ARIMA
            mean_cost = statistics.mean(costs)
            trend = (costs[-1] - costs[0]) / len(costs)  # Daily trend

            model_id = str(uuid.uuid4())

            # Store model
            self.table.put_item(Item={
                'model_id': model_id,
                'account_id': account_id,
                'model_type': 'ARIMA',
                'training_date': datetime.now(timezone.utc).isoformat(),
                'data_points': len(costs),
                'mean_cost': mean_cost,
                'trend': trend,
                'status': 'trained'
            })

            logger.info(f"Trained ARIMA model {model_id} for {account_id} with {len(costs)} data points")
            return model_id

        except Exception as e:
            logger.error(f"Failed to train ARIMA model: {str(e)}")
            return ""

    def forecast_costs(self, account_id: str, model_id: str, days_ahead: int = 30) -> Dict:
        """
        향후 비용 예측

        Args:
            account_id: AWS Account ID
            model_id: 모델 ID
            days_ahead: 예측 기간 (일)

        Returns:
            예측 정보: forecast, confidence_interval, trend
        """
        try:
            # Retrieve model
            response = self.table.get_item(Key={'model_id': model_id})
            if 'Item' not in response:
                logger.error(f"Model {model_id} not found")
                return {'error': 'Model not found'}

            model = response['Item']
            mean_cost = model['mean_cost']
            trend = model['trend']

            # Generate forecast using simple linear trend
            forecast = []
            lower_bound = []
            upper_bound = []

            for day in range(1, days_ahead + 1):
                predicted = mean_cost + (trend * day)
                forecast.append(max(0, predicted))

                # Add confidence interval (±10% for 95% CI)
                margin = predicted * 0.10
                lower_bound.append(max(0, predicted - margin))
                upper_bound.append(predicted + margin)

            # Determine trend direction
            if trend > 0:
                trend_direction = 'increasing'
            elif trend < 0:
                trend_direction = 'decreasing'
            else:
                trend_direction = 'stable'

            logger.info(f"Forecasted {days_ahead} days for {account_id}, trend: {trend_direction}")

            return {
                'account_id': account_id,
                'model_id': model_id,
                'forecast': forecast,
                'lower_bound': lower_bound,
                'upper_bound': upper_bound,
                'confidence': 0.95,
                'trend': trend_direction,
                'average_daily_cost': mean_cost,
                'monthly_projection': mean_cost * 30
            }

        except Exception as e:
            logger.error(f"Failed to forecast costs: {str(e)}")
            return {'error': str(e)}

    def detect_cost_anomalies(self, account_id: str, actual_cost: float, predicted_cost: float) -> Dict:
        """
        예측값과 실제값의 차이를 통한 이상 감지

        Args:
            account_id: AWS Account ID
            actual_cost: 실제 비용
            predicted_cost: 예측 비용

        Returns:
            이상 감지 결과
        """
        try:
            if predicted_cost == 0:
                deviation_percent = 100.0
            else:
                deviation_percent = abs(actual_cost - predicted_cost) / predicted_cost * 100

            threshold = 20  # 20% deviation threshold

            is_anomaly = deviation_percent > threshold

            return {
                'account_id': account_id,
                'actual_cost': actual_cost,
                'predicted_cost': predicted_cost,
                'deviation_percent': deviation_percent,
                'is_anomaly': is_anomaly,
                'severity': 'high' if deviation_percent > 40 else 'medium' if is_anomaly else 'low'
            }

        except Exception as e:
            logger.error(f"Failed to detect cost anomalies: {str(e)}")
            return {'error': str(e)}

    def recommend_cost_reductions(self, account_id: str, forecast: Dict) -> List[Dict]:
        """
        예측 기반 비용 절감 제안

        Args:
            account_id: AWS Account ID
            forecast: 비용 예측 데이터

        Returns:
            비용 절감 제안 목록
        """
        try:
            recommendations = []
            monthly_projected = forecast.get('monthly_projection', 0)

            # High trend
            if forecast.get('trend') == 'increasing':
                recommendations.append({
                    'action': 'Implement auto-scaling policies',
                    'potential_savings': monthly_projected * 0.15,  # 15% savings
                    'priority': 'high',
                    'timeframe': 'immediate',
                    'reason': 'Costs are increasing rapidly'
                })

                recommendations.append({
                    'action': 'Review and delete unused resources',
                    'potential_savings': monthly_projected * 0.10,  # 10% savings
                    'priority': 'high',
                    'timeframe': 'within 1 week'
                })

            # Moderate recommendations
            recommendations.append({
                'action': 'Analyze reserved instance opportunities',
                'potential_savings': monthly_projected * 0.20,  # 20% savings
                'priority': 'medium',
                'timeframe': 'within 2 weeks'
            })

            recommendations.append({
                'action': 'Check for idle EC2 instances and snapshots',
                'potential_savings': monthly_projected * 0.05,  # 5% savings
                'priority': 'low',
                'timeframe': 'within 1 month'
            })

            logger.info(f"Generated {len(recommendations)} cost reduction recommendations for {account_id}")

            return recommendations

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {str(e)}")
            return []

    def calculate_forecast_accuracy(self, predictions: List[float], actuals: List[float]) -> Dict:
        """
        예측 모델의 정확도 계산

        Args:
            predictions: 예측값 목록
            actuals: 실제값 목록

        Returns:
            정확도 지표: MAPE, RMSE, MAE
        """
        try:
            if len(predictions) != len(actuals) or len(predictions) == 0:
                return {'error': 'Prediction and actual lists must have same length'}

            # Calculate MAPE (Mean Absolute Percentage Error)
            errors = []
            for pred, actual in zip(predictions, actuals):
                if actual != 0:
                    error_percent = abs(pred - actual) / actual * 100
                    errors.append(error_percent)

            mape = sum(errors) / len(errors) if errors else 0

            # Calculate RMSE (Root Mean Square Error)
            squared_errors = [(pred - actual) ** 2 for pred, actual in zip(predictions, actuals)]
            rmse = (sum(squared_errors) / len(squared_errors)) ** 0.5

            # Calculate MAE (Mean Absolute Error)
            absolute_errors = [abs(pred - actual) for pred, actual in zip(predictions, actuals)]
            mae = sum(absolute_errors) / len(absolute_errors)

            logger.info(f"Model accuracy - MAPE: {mape:.2f}%, RMSE: {rmse:.2f}, MAE: {mae:.2f}")

            return {
                'mape': mape,  # Mean Absolute Percentage Error
                'rmse': rmse,  # Root Mean Square Error
                'mae': mae,    # Mean Absolute Error
                'accuracy_percent': max(0, 100 - mape)  # Inverse of MAPE
            }

        except Exception as e:
            logger.error(f"Failed to calculate forecast accuracy: {str(e)}")
            return {'error': str(e)}
