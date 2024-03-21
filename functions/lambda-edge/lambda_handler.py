import boto3

# Create DynamoDB client
dynamodb = boto3.client('dynamodb', region_name='us-east-1')

def get_item_from_dynamodb(table_name, key):
    try:
        # Retrieve data from DynamoDB table
        response = dynamodb.get_item(
            TableName=table_name,
            Key=key
        )
        
        # Extract data from response
        return response.get('Item')
    except Exception as e:
        # Handle any exceptions and return None
        print(f"Error retrieving item from DynamoDB: {e}")
        return None


HOME_CONTENT = """
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Simple Lambda@Edge Static Content Response</title>
</head>
<body>
    <p>Hello from Lambda@Edge!</p>
    <p>This is the home page!</p>
</body>
</html>
"""

ANSWER_CONTENT = """
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Simple Lambda@Edge Static Content Response</title>
</head>
<body>
    <p>Hello from Lambda@Edge!</p>
    <p>Clue: {} Answer: {}</p>
</body>
</html>
"""

CONTENT_404 = """
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Simple Lambda@Edge Static Content Response</title>
</head>
<body>
    <p>Hello from Lambda@Edge!</p>
    <p>The requested page doesn't exist!</p>
</body>
</html>
"""

CONTENT_500 = """
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Simple Lambda@Edge Static Content Response</title>
</head>
<body>
    <p>Hello from Lambda@Edge!</p>
    <p>Oops! Something went wrong!</p>
</body>
</html>
"""
'''
This is the structure of the event from cloudfront

{
    "Records": [
        {
            "cf": {
                "config": {
                    "distributionDomainName": "dn0eff97ul7zj.cloudfront.net",
                    "distributionId": "EY8ZZSBOCSVLC",
                    "eventType": "viewer-request",
                    "requestId": "xQwB7T-PkzzZXxr6iUpGDGSPgS7_mUKe0ZoFYLcxqcbuoVdFtpnWkg=="
                },
                "request": {
                    "clientIp": "98.148.247.202",
                    "headers": {
                        "host": [
                            {
                                "key": "Host",
                                "value": "www.justcrossword.com"
                            }
                        ],
                        "user-agent": [
                            {
                                "key": "User-Agent",
                                "value": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                            }
                        ],
                        "cache-control": [
                            {
                                "key": "cache-control",
                                "value": "max-age=0"
                            }
                        ],
                        "accept": [
                            {
                                "key": "accept",
                                "value": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
                            }
                        ],
                        "accept-encoding": [
                            {
                                "key": "accept-encoding",
                                "value": "gzip, deflate, br, zstd"
                            }
                        ],
                        "accept-language": [
                            {
                                "key": "accept-language",
                                "value": "en-US,en;q=0.9"
                            }
                        ]
                    },
                    "method": "GET",
                    "querystring": "",
                    "uri": "/"
                }
            }
        }
    ]
}
'''


# TODO: pass status codes and other stuff
def generate_response(html_content):
    return {
        'status': '200',
        'statusDescription': 'OK',
        'headers': {
            'cache-control': [
                {
                    'key': 'Cache-Control',
                    'value': 'max-age=100'
                }
            ],
            "content-type": [
                {
                    'key': 'Content-Type',
                    'value': 'text/html'
                }
            ]
        },
        'body': html_content
    }


def handler(event, context):

    try:
        print(event)
        print(event['Records'][0]['cf']['request']['uri'])

        uri = event['Records'][0]['cf']['request']['uri']

        if uri == '/':
            return generate_response(HOME_CONTENT)
        
        segments = uri.split('/')

        requested_clue_path = segments[1] if len(segments) > 1 else ''

        print(f"looking up requested path {requested_clue_path}")

        # Define DynamoDB table name
        table_name = 'CrosswordInfraStack-CrosswordTableC285ED21-111C8OOVQD3G'  # Replace with your DynamoDB table name
        
        # Define key for the item to retrieve
        key = {'clue_path': {'S': requested_clue_path}}  # Replace key_name and key_value with your actual key
        
        # # Retrieve item from DynamoDB
        item = get_item_from_dynamodb(table_name, key)
        
        if item:
            # Process retrieved item
            # Example: extract values from item
            clue = item.get('clue', {}).get('S')
            answer = item.get('answer', {}).get('S')
            # Do something with the values
            
            return generate_response(ANSWER_CONTENT.format(clue, answer))
        else:
            return generate_response(CONTENT_404)
    except Exception as e:

        return generate_response(CONTENT_500)