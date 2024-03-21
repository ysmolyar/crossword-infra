import * as path from 'path';
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import {
  aws_s3 as s3,
  aws_s3_deployment as s3deployment,
  aws_iam as iam,
  aws_cloudfront as cloudfront,
  aws_certificatemanager as acm,
  aws_route53 as route53,
  aws_route53_targets as route53targets,
  aws_cloudfront_origins as origins,
  aws_lambda as lambda,
  aws_dynamodb as dynamodb
} from 'aws-cdk-lib';

const lambdaEdgeDeploymentPackage = "functions/lambda-edge/deployment_package.zip"

export class EdgeFunctionStack extends cdk.Stack {

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create the lambda function for Lambda@Edge
    const edgeLambdaFunction = new lambda.Function(this, 'EdgeLambdaFunction', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'lambda_handler.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', lambdaEdgeDeploymentPackage)),
      currentVersionOptions: {
        removalPolicy: cdk.RemovalPolicy.DESTROY
      }
    });

    // A numbered version to give to cloudfront
    const edgeLambdaFunctionVersion = new lambda.Version(this, "EdgeLambdaFunctionVersion", {
      lambda: edgeLambdaFunction,
    });

    // Output the ARN of the DynamoDB table
    new cdk.CfnOutput(this, 'EdgeLambdaVersionArn', {
      value: edgeLambdaFunction.currentVersion.edgeArn
    });
  }
}
