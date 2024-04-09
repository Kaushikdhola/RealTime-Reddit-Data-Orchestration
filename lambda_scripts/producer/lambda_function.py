import json
from kafka import KafkaProducer
import os
import praw
import prawcore
import boto3

def lambda_handler(event, context):
    
    invoke_consumer_lambda()

    bootstrap_servers = os.getenv('BOOTSTRAP_SERVERS')
    sasl_mechanism = 'SCRAM-SHA-512'
    username = os.getenv('CLOUDKARAFKA_USERNAME')
    password = os.getenv('CLOUDKARAFKA_PASSWORD')
    topic = os.getenv('KAFKA_TOPIC')

    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        security_protocol='SASL_SSL',
        sasl_mechanism=sasl_mechanism,
        sasl_plain_username=username,
        sasl_plain_password=password,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
    reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    
    reddit = praw.Reddit(client_id=reddit_client_id, client_secret=reddit_client_secret, user_agent="Reddit Kafka Producer")
    subreddit_names=os.getenv('SUBREDDITS').split(',')
    
    for subreddit_name in subreddit_names:
        try:
            subreddit = reddit.subreddit(subreddit_name)

            #increase limit to to 1000 to get more data from reddit which are created in last 24 hours
            #for testing purpose, limit is set to 1
            #it will fetch only 1 post from each subreddit
            #posts are fetched and sent to kafka in descending order of created_utc
            for submission in subreddit.new(limit=1):
                reddit_data = {
                    "title": submission.title,
                    "score": submission.score,
                    "num_comments": submission.num_comments,
                    "created_utc": submission.created_utc,
                    "upvote_ratio": submission.upvote_ratio,
                    "award_count": submission.total_awards_received,
                    "number_of_upvotes": submission.ups,
                    "number_of_downvotes": submission.downs,
                    "text_content": submission.selftext,
                    "is_video": submission.is_video,
                }
                producer.send(topic, value=reddit_data)
                print(f"Message sent to Kafka: {reddit_data}")

        except prawcore.exceptions.Forbidden as e:
            print(f"Access to r/{subreddit_name} is Forbidden: {e}")
        except Exception as e:
            print(f"Error accessing r/{subreddit_name}: {e}")

    producer.flush()
    producer.close()

    return {
        'statusCode': 200,
        'body': json.dumps('Data sent to Kafka successfully!')
    }


def invoke_consumer_lambda():
    lambda_client = boto3.client('lambda')

    consumer_lambda_arn = 'arn:aws:lambda:us-east-1:590183658701:function:RedditKafkaConsumer1'

    response = lambda_client.invoke(
        FunctionName=consumer_lambda_arn,
        InvocationType='Event'  
    )
