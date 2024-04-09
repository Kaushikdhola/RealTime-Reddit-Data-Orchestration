import os
import json
import sys
import boto3
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse as parse_datetime
from kafka import KafkaConsumer
import re

def store_in_s3(messages):
    s3 = boto3.client('s3')
    bucket_name = 'reddit-extracted-raw-data'
    folder_name = 'reddit-data/'
    
    current_datetime = datetime.now(timezone.utc)
    file_name = current_datetime.strftime('%Y-%m-%d_%H-%M-%S') + '.csv'
    
    csv_content = ""
    
    keys = [
        "title",
        "score",
        "num_comments",
        "created_utc",
        "upvote_ratio",
        "award_count",
        "number_of_upvotes",
        "number_of_downvotes",
        "text_content",
        "is_video"
    ]
    
    header_row = ",".join(keys) + "\n"
    csv_content += header_row
    
    for message in messages:
        row_values = []
        for key in keys:
            value = message.get(key, '')
            if isinstance(value, str):
                
                value = remove_commas(value)
                value=remove_newlines_and_spaces(value)
                value = remove_special_characters(value)
                value = remove_newlines(value)
                
                print(value)
                
                if ',' in value or '\n' in value:
                    value = f'"{value}"'
            elif isinstance(value, bool):
                
                value = str(value).lower()
            elif isinstance(value, (int, float)):
                
                value = str(value)
            row_values.append(value)
        
        row = ",".join(row_values) + "\n"
        csv_content += row
    
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=folder_name)
    exists = 'Contents' in response
    
    if not exists:
        s3.put_object(Bucket=bucket_name, Key=folder_name)
    else:
        for obj in response['Contents']:
            s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
    
    s3.put_object(Bucket=bucket_name, Key=f'{folder_name}{file_name}', Body=csv_content)

def remove_commas(value):
    return value.replace(',', '')

def remove_special_characters(value):
    value = re.sub(r'[^a-zA-Z0-9\s]', '', value)
    return value

def remove_newlines_and_spaces(value):
    value = ' '.join(value.split())
    return value
    
def remove_newlines(value):
    value=value.replace('\\n', ' ')
    value=value.replace('\n', ' ')
    value=value.replace('\\', ' ')
    return value
    
def remove_commas(value):
    # Remove commas from the value
    return value.replace(',', '')

def convert_to_numeric(value):
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return None

def convert_to_boolean(value):
    if value.lower() == 'true':
        return True
    elif value.lower() == 'false':
        return False
    else:
        return None
    
def lambda_handler(event, context):
    
    bootstrap_servers = os.getenv('BOOTSTRAP_SERVER')
    sasl_mechanism = os.getenv('SASL_MECHANISM')
    username = os.getenv('USERNAME')
    password = os.getenv('PASSWORD')
    group_id = os.getenv('GROUP_ID')
    topic = os.getenv('TOPIC')

    consumer_timeout_ms = 5000

    consumer = KafkaConsumer(
        topic,
        group_id=group_id,
        bootstrap_servers=bootstrap_servers,
        sasl_mechanism=sasl_mechanism,
        security_protocol='SASL_SSL',
        sasl_plain_username=username,
        sasl_plain_password=password,
        consumer_timeout_ms=consumer_timeout_ms
    )
    
    messages = []
    for message in consumer:
        message_data = json.loads(message.value.decode('utf-8'))
        messages.append(message_data)
        sys.stdout.write(json.dumps(message_data) + '\n')
        sys.stdout.flush()
        
    consumer.close()
    
    store_in_s3(messages)
    
    glue_client = boto3.client('glue')
    
    workflow_name = 'GlueWorkFlowETL'
    
    try:
        response = glue_client.start_workflow_run(
            Name=workflow_name
        )
        
        workflow_run_id = response['RunId']
        
        return {
            'statusCode': 200,
            'body': f'Started Glue workflow run with ID: {workflow_run_id}'
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error starting Glue workflow: {str(e)}'
        }
    