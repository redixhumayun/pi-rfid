# Use this code snippet in your app.
# If you need more information about configurations or implementing the sample code, visit the AWS docs:   
# https://aws.amazon.com/developers/getting-started/python/

import boto3
import base64
from botocore.exceptions import ClientError
import json
from environment_variable import EnvironmentVariable

def get_secret(environment):

    #   Load the secrets based on environment
    if environment == EnvironmentVariable.DEVELOPMENT.value:
        secret_name = "pi-rfid/env-variables-test"
    elif environment == EnvironmentVariable.PRODUCTION.value:
        secret_name = "pi-rfid/env-variables"        
    region_name = "ap-south-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'UnrecognizedClientException':
            # The client is not recognized with AWS, probably because this
            # client is not registered
            raise e
        if e.response['Error']['Code'] == 'AccessDeniedException':
            # The user running on this Pi does not have access to the Systems Manager
            # service on AWS. Please add the required permissions to this user
            raise e
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        if e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        if e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        if e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            parsed_secret_values = json.loads(secret)
            return parsed_secret_values
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
            
    # Your code goes here.

def write_secrets_to_env_file(secrets: dict):
    try:
        with open('.env', 'w') as env_file:
            for key, value in secrets.items():
                string_to_write = f"{key}={value}\n"   
                env_file.write(string_to_write)
        print('Done writing the env file successfully')
    except Exception as err:
        print(f"Error while writing the .env file: {err}")
        raise err