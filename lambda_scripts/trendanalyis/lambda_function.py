import os
import pandas as pd
import re
import boto3
from io import BytesIO

def get_stop_words():
    stop_words_1 = os.environ.get("STOP_WORDS", "").split(",")
    stop_words_2 = os.environ.get("STOP_WORDS_2", "").split(",")
    stop_words_3 = os.environ.get("STOP_WORDS_3", "").split(",")
    stop_words_4 = os.environ.get("STOP_WORDS_4", "").split(",")

    all_stop_words = stop_words_1 + stop_words_2 + stop_words_3 + stop_words_4
    return all_stop_words

def trend_analysis(df, stop_words):
    df['combined_text'] = df['title'] + ' ' + df['text_content']
    df['combined_text'] = df['combined_text'].str.lower()

    pattern = r'\b[^\d\W]+\b'
    
    df['filtered_tokens'] = df['combined_text'].apply(lambda x: re.findall(pattern, x))
    print(df['filtered_tokens'])
    
    words = pd.Series([word for sublist in df['filtered_tokens'] for word in sublist])
    word_counts = words.value_counts()
    
    word_count_list = [(word, count) for word, count in zip(word_counts.index, word_counts.values)]
    
    top_keywords = [(word, count) for word, count in word_count_list if word not in stop_words]
    
    return top_keywords

def get_latest_parquet(bucket, folder):
    s3 = boto3.client('s3')
    response = s3.list_objects_v2(Bucket=bucket, Prefix=folder)
    
    parquet_files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.parquet')]
    
    if parquet_files:
        latest_parquet = max(parquet_files, key=lambda x: response['Contents'][parquet_files.index(x)]['LastModified'])
        return latest_parquet
    else:
        return None

def lambda_handler(event, context):
    stop_words = get_stop_words()
    
    s3 = boto3.client('s3')
    input_bucket = 'reddit-extracted-raw-data'
    input_folder = 'reddit-data-parquet/'
    
    latest_parquet_file = get_latest_parquet(input_bucket, input_folder)
    
    if latest_parquet_file is None:
        return {
            'statusCode': 404,
            'body': 'No Parquet files found in the specified folder'
        }
    
    obj = s3.get_object(Bucket=input_bucket, Key=latest_parquet_file)
    df = pd.read_parquet(BytesIO(obj['Body'].read()))
    
    top_keywords = trend_analysis(df, stop_words)

    top_keywords_csv = '\n'.join([f"{word},{count}" for word, count in top_keywords])
    
    output_bucket = 'reddit-extracted-raw-data'
    output_folder = 'reddit-trend-output/'
    output_file = 'top_trending_keywords.csv'
    
    response = s3.list_objects_v2(Bucket=output_bucket, Prefix=output_folder)

    if 'Contents' not in response:
        s3.put_object(Bucket=output_bucket, Key=(output_folder + '/'))
    else:
        for obj in response['Contents']:
            s3.delete_object(Bucket=output_bucket, Key=obj['Key'])
    
    s3.put_object(Bucket=output_bucket, Key=output_folder + output_file, Body=top_keywords_csv)

    return {
        'statusCode': 200,
        'body': 'Top 3 trending keywords stored in S3.'
    }