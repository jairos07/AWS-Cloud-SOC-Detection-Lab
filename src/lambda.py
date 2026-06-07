import json
import boto3
import uuid
import os
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
sns_client = boto3.client('sns')

TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'soc-incidents')
SNS_ARN = os.environ.get('SNS_TOPIC_ARN', '')
table = dynamodb.Table(TABLE_NAME)

SEVERITY_MAP = {
    'SOC-FailedConsoleLogins-ALARM': 'MEDIUM',
    'SOC-IAMUserCreation-ALARM': 'HIGH',
    'SOC-PrivilegeEscalation-ALARM': 'HIGH',
    'SOC-CloudTrailTampering-ALARM': 'CRITICAL',
    'SOC-AccessKeyCreation-ALARM': 'MEDIUM',
    'SOC-RootAccountLogin-ALARM': 'CRITICAL',
}

def parse_cloudwatch_alarm(event):
    try:
        sns_message = json.loads(event['Records'][0]['Sns']['Message'])
        return {
            'alarm_name': sns_message.get('AlarmName', 'Unknown'),
            'alarm_description': sns_message.get('AlarmDescription', 'No description'),
            'state': sns_message.get('NewStateValue', 'UNKNOWN'),
            'reason': sns_message.get('NewStateReason', 'No reason provided'),
            'region': sns_message.get('Region', 'eu-west-1'),
            'account_id': sns_message.get('AWSAccountId', 'Unknown'),
            'metric_name': sns_message.get('Trigger', {}).get('MetricName', 'Unknown'),
            'raw_message': json.dumps(sns_message)
        }
    except (KeyError, json.JSONDecodeError):
        return {
            'alarm_name': event.get('alarm_name', 'TEST-ALARM'),
            'alarm_description': event.get('alarm_description', 'Direct test'),
            'state': 'ALARM',
            'reason': 'Direct Lambda test invocation',
            'region': 'eu-west-1',
            'account_id': 'TEST',
            'metric_name': event.get('metric_name', 'TestMetric'),
            'raw_message': json.dumps(event)
        }

def lambda_handler(event, context):
    print(f"SOC Responder triggered. Event: {json.dumps(event)}")
    
    parsed = parse_cloudwatch_alarm(event)
    print(f"Alarm: {parsed['alarm_name']} | State: {parsed['state']}")
    
    if parsed['state'] != 'ALARM':
        print(f"State is {parsed['state']}, not ALARM. Skipping.")
        return {'statusCode': 200, 'body': 'State not ALARM, skipped.'}
    
    incident_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    severity = SEVERITY_MAP.get(parsed['alarm_name'], 'LOW')
    
    incident = {
        'incident_id': incident_id,
        'timestamp': timestamp,
        'alarm_name': parsed['alarm_name'],
        'severity': severity,
        'metric_name': parsed['metric_name'],
        'alarm_description': parsed['alarm_description'],
        'state_reason': parsed['reason'],
        'region': parsed['region'],
        'account_id': parsed['account_id'],
        'status': 'OPEN',
        'raw_event': parsed['raw_message'],
        'created_at': timestamp
    }
    
    try:
        table.put_item(Item=incident)
        print(f"Incident saved: {incident_id} | Severity: {severity}")
    except Exception as e:
        print(f"DynamoDB error: {e}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({'incident_id': incident_id, 'severity': severity})
    }