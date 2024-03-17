def handler(event, context):
    message = "Hello, world!"
    return {
        'statusCode': 200,
        'body': message
    }