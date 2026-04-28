export interface CostData {
  today_cost: number;
  yesterday_cost: number;
  monthly_cost: number;
  increase_percent: number;
  threshold: number;
  is_anomaly: boolean;
  date: string;
  daily_costs: Array<{ date: string; cost: number }>;
}

export interface EC2Anomaly {
  type: 'unauthorized_region' | 'open_port' | 'new_instance';
  instance_id: string;
  region: string;
  details: string;
  severity: 'critical' | 'warning' | 'info';
}

export interface EC2ExposedInstance {
  instance_id: string;
  region: string;
  port: number;
  sg_id: string;
}

export interface EC2Data {
  total_instances: number;
  running_instances: number;
  stopped_instances: number;
  anomalies: EC2Anomaly[];
  exposed_instances: EC2ExposedInstance[];
  instances_by_region: Record<string, number>;
}

export interface S3PublicBucket {
  bucket_name: string;
  public_reasons: string[];
  created: string;
}

export interface S3NewBucket {
  bucket_name: string;
  created: string;
}

export interface S3Anomaly {
  type: 'public_bucket' | 'new_bucket';
  bucket_name: string;
  details: string;
  severity: 'critical' | 'warning' | 'info';
}

export interface S3Data {
  total_buckets: number;
  public_buckets: S3PublicBucket[];
  new_buckets: S3NewBucket[];
  anomalies: S3Anomaly[];
}

export interface GuardianEvent {
  event_id: string;
  event_type: 'cost' | 'ec2' | 's3' | 'summary' | 'auto_response';
  severity: 'info' | 'warning' | 'critical';
  timestamp: string;
  details: Record<string, any>;
  auto_response?: {
    action: string;
    resource_id: string;
    status: 'success' | 'failed';
  };
}

export interface DashboardSummary {
  cost: CostData;
  ec2: EC2Data;
  s3: S3Data;
  recent_events: GuardianEvent[];
  last_check: string;
  next_check: string;
  system_health: 'healthy' | 'warning' | 'critical';
}

/** Raw DynamoDB check_result item stored by the Python handler */
export interface CheckResultItem {
  timestamp: string;
  event_type: 'check_result';
  severity: 'info';
  details: string; // JSON string of CheckResultDetails
}

export interface CheckResultDetails {
  cost: CostData;
  ec2: EC2Data;
  s3: S3Data;
  last_check: string;
  system_health: 'healthy' | 'warning' | 'critical';
}

/** Raw DynamoDB event item */
export interface DynamoEventItem {
  timestamp: string;
  event_type: string;
  severity: string;
  details: string; // JSON string
  action_type?: string;
  resource_id?: string;
  status?: string;
}
