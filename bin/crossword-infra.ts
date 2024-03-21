#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { CrosswordInfraStack } from '../lib/crossword-infra-stack';
import { EdgeFunctionStack } from '../lib/edge-function-stack';

const app = new cdk.App();

new EdgeFunctionStack(app, 'EdgeFunctionStack', {
  env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: 'us-east-1' },
});

// For simplicity as Cloudfront is only supported in use1, hardcoding region
new CrosswordInfraStack(app, 'CrosswordInfraStack', {
  env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: 'us-east-1' }
});