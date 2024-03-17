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
  aws_lambda as lambda
} from 'aws-cdk-lib';

const domainName = "justcrossword.com"
const s3AssetPath = "./assets"
const rootObject = "index.html"
const urlRewriteFunc = "functions/url-rewrite.js"
const lambdaHandler = "function/lambda-handler.py"

export class CrosswordInfraStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create s3 bucket to host site contents
    const assetsBucket = new s3.Bucket(this, 'WebsiteBucket', {
      publicReadAccess: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      accessControl: s3.BucketAccessControl.PRIVATE,
      objectOwnership: s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
      encryption: s3.BucketEncryption.S3_MANAGED,
    });

    // Deploy root object
    new s3deployment.BucketDeployment(this, "Deployment", {
      sources: [s3deployment.Source.asset(s3AssetPath)],
      destinationBucket: assetsBucket,
    });

    // Create OAI user to retrieve assets on behalf of user
    const cloudfrontOAI = new cloudfront.OriginAccessIdentity(
      this, 'CloudFrontOriginAccessIdentity');

    // Grant OAI user read access to s3
    assetsBucket.addToResourcePolicy(new iam.PolicyStatement({
      actions: ['s3:GetObject'],
      resources: [assetsBucket.arnForObjects('*')],
      principals: [new iam.CanonicalUserPrincipal(
        cloudfrontOAI.cloudFrontOriginAccessIdentityS3CanonicalUserId)],
    }));

    // Look up hosted zone for domain
    const zone = route53.HostedZone.fromLookup(this, 'HostedZone',
      { domainName: domainName });

    // Create TLS site certificate
    const certificate = new acm.DnsValidatedCertificate(this,
      'SiteCertificate',
      {
        domainName,
        hostedZone: zone,
        region: 'us-east-1',
        subjectAlternativeNames: [`www.${domainName}`]
      });

    // create a function to rewrite urls
    const rewriteFunction = new cloudfront.Function(this, 'Function', {
      code: cloudfront.FunctionCode.fromFile({ filePath: urlRewriteFunc }),
    });

    // Create some security headers for responses
    const responseHeaderPolicy = new cloudfront.ResponseHeadersPolicy(this, 'SecurityHeadersResponseHeaderPolicy', {
      comment: 'Security headers response header policy',
      securityHeadersBehavior: {
        contentSecurityPolicy: {
          override: true,
          contentSecurityPolicy: "default-src 'self'"
        },
        strictTransportSecurity: {
          override: true,
          accessControlMaxAge: cdk.Duration.days(2 * 365),
          includeSubdomains: true,
          preload: true
        },
        contentTypeOptions: {
          override: true
        },
        referrerPolicy: {
          override: true,
          referrerPolicy: cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN
        },
        xssProtection: {
          override: true,
          protection: true,
          modeBlock: true
        },
        frameOptions: {
          override: true,
          frameOption: cloudfront.HeadersFrameOption.DENY
        }
      }
    });

    // Create the cloudfront distribution (tie it all together)
    // Single default behavior which applies a path pattern that matches all requests
    // NOTE: set invalidation on /index.html bc cloudfront caches everything for 24h by default.
    // can use versioning or invalidation to solve this, no way to invalidate in CDK so I did it in console.
    // will remove invalidations once site dev stabilizes
    const cloudfrontDistribution = new cloudfront.Distribution(this, 'CloudFrontDistribution', {
      certificate: certificate,
      domainNames: [domainName, `www.${domainName}`],
      defaultRootObject: rootObject,
      defaultBehavior: {
        origin: new origins.S3Origin(assetsBucket, {
          originAccessIdentity: cloudfrontOAI
        }),
        functionAssociations: [{
          function: rewriteFunction,
          eventType: cloudfront.FunctionEventType.VIEWER_REQUEST
        }],
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        responseHeadersPolicy: responseHeaderPolicy
      }
    });

    // Create an A Record in the domain's hosted zone and point it to the cloudfront distribution
    new route53.ARecord(this, 'ARecord', {
      recordName: domainName,
      target: route53.RecordTarget.fromAlias(new route53targets.CloudFrontTarget(cloudfrontDistribution)),
      zone
    });

    // Create an A Record in the domain's hosted zone and point it to the cloudfront distribution
    new route53.ARecord(this, 'ARecordWWW', {
      recordName: `www.${domainName}`,
      target: route53.RecordTarget.fromAlias(new route53targets.CloudFrontTarget(cloudfrontDistribution)),
      zone
    });

    // TODO: create lambda
        //  lambda function definition
        const lambdaFunction = new lambda.Function(this, 'lambda-function', {
          runtime: lambda.Runtime.PYTHON_3_12,
          timeout: cdk.Duration.seconds(),
          handler: 'lambda_handler.handler',
          code: lambda.Code.fromAsset(path.join(__dirname, '/../functions/nyt-lambda')),
          // environment: {
          //   REGION: cdk.Stack.of(this).region,
          //   AVAILABILITY_ZONES: JSON.stringify(
          //     cdk.Stack.of(this).availabilityZones,
          //   ),
          // },
        });"Vn1&^4QpdpZooi#V"
  }
}
