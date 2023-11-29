import boto3

ssm_client = boto3.client('ssm', region_name='us-east-1')


def get_ssm_param(key):
    response = ssm_client.get_parameter(
        Name=f'/ai/elevenLabsTwilioDemo/{key}',
        WithDecryption=True
    )
    return response['Parameter']['Value']


def set_ssm_param(key, value):
    response = ssm_client.put_parameter(
        Name=f'/ai/elevenLabsTwilioDemo/{key}',
        Value=value,
        Type='String',
        Overwrite=True
    )
    return response


def send_twiml(twiml):
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/xml'},
        'body': str(twiml)
    }
