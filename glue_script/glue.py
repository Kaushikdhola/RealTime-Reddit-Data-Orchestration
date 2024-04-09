import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

try:
    import boto3
except ImportError:
    from subprocess import call
    call(['pip', 'install', 'boto3'])
    import boto3

args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Script generated for node Amazon S3
AmazonS3_node1712334626834 = glueContext.create_dynamic_frame.from_options(format_options={"quoteChar": "\"", 
                                        "withHeader": True, "separator": ",", 
                                        "optimizePerformance": False}, 
                                        connection_type="s3", format="csv", 
                                        connection_options={"paths": ["s3://reddit-extracted-raw-data/reddit-data/"], 
                                        "recurse": True}, 
                                        transformation_ctx="AmazonS3_node1712334626834")

# Script generated for node Change Schema
ChangeSchema_node1712334666935 = ApplyMapping.apply(frame=AmazonS3_node1712334626834, 
                                mappings=[("title", "string", "title", "string"), 
                                          ("score", "string", "score", "bigint"), 
                                          ("num_comments", "string", "num_comments", "bigint"), 
                                          ("created_utc", "string", "created_utc", "double"), 
                                          ("upvote_ratio", "string", "upvote_ratio", "double"), 
                                          ("award_count", "string", "award_count", "bigint"), 
                                          ("number_of_upvotes", "string", "number_of_upvotes", "bigint"), 
                                          ("number_of_downvotes", "string", "number_of_downvotes", "bigint"), 
                                          ("text_content", "string", "text_content", "string"), 
                                          ("is_video", "string", "is_video", "boolean")], 
                                transformation_ctx="ChangeSchema_node1712334666935")

# Create the 'reddit-data-parquet/' folder if it does not exist
s3 = boto3.client('s3')
bucket_name = 'reddit-extracted-raw-data'
folder_name = 'reddit-data-parquet/'
try:
    response = s3.list_objects(Bucket=bucket_name, Prefix=folder_name)
    if 'Contents' in response and not response['Contents']:
        s3.put_object(Bucket=bucket_name, Key=(folder_name))
except KeyError:
    s3.put_object(Bucket=bucket_name, Key=(folder_name))
    
# Script generated for node Amazon S3
AmazonS3_node1712334675109 = glueContext.write_dynamic_frame.from_options(frame=ChangeSchema_node1712334666935, 
                                        connection_type="s3", 
                                        format="glueparquet", 
                                        connection_options={"path": "s3://reddit-extracted-raw-data/reddit-data-parquet/", 
                                        "partitionKeys": []}, 
                                        format_options={"compression": "uncompressed"}, 
                                        transformation_ctx="AmazonS3_node1712334675109")

lambda_client = boto3.client('lambda')

lambda_function_name = 'RedditTrendAnalysis1'
response = lambda_client.invoke(
    FunctionName=lambda_function_name,
    InvocationType='Event',  # Asynchronous invocation
    Payload='{}'
)

job.commit()